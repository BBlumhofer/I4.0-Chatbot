from __future__ import annotations

import asyncio
import base64
import os
import socket
from dataclasses import dataclass
from enum import IntEnum
from functools import partial
from inspect import currentframe

import structlog
from asyncua import Node, Server, ua, uamethod
from asyncua.server.address_space import AddressSpace, AttributeService, MethodService
from asyncua.server.internal_server import InternalServer
from asyncua.server.internal_session import InternalSession, SessionState
from asyncua.server.user_managers import UserManager
from asyncua.ua import NodeId

try:  # asyncua <=1.1.6
    from asyncua.server.users import User as UaUser
    from asyncua.server.users import UserRole
except ModuleNotFoundError:  # asyncua >= 1.1.7
    from asyncua.crypto.permission_rules import User as UaUser
    from asyncua.crypto.permission_rules import UserRole
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from typing_extensions import override

from .base_config import BaseConfig
from .common import add_object, write_optional
from .ua_fsm import UaFiniteStateMachine
from .user import INTERNAL_USER, User


def get_hostname_from_ip(ip: str) -> str:
    """ Tries to determine the hostname of the given IP via reverse DNS lookup. """
    try:
        data = socket.gethostbyaddr(ip)
        return repr(data[0])
    except Exception:
        return ip


def get_scrypt_instance() -> Scrypt:
    #  Note: The same salt (usually bad) is used for all passwords since it acts more like a master password
    #  to not have the user passwords in clear text inside the code base...
    if 'UA_ADAPTER_SALT' in os.environ:
        salt = base64.b64decode(bytes(os.environ['UA_ADAPTER_SALT'], 'utf-8'))
        return Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1)
    else:
        raise RuntimeError("Salt not found in environment variable! Please insert salt into UA_ADAPTER_SALT !")


class AccessControl(UserManager):
    """
    Manages access control using (currently hard-coded) user information which specify priority and access level.
    Priority is only used for determining whether a user can override occupation of another user with a lower priority.
    Access level determines which methods and variables etc. may be accessed.

    In order to write to certain variables or call most methods, a user must first occupy using the 'occupy'-
    OPC-UA method the module. If the module is already occupied by another user, the method 'prio' can be used if the
    priority of the new user is higher than the priority of the occupying user.
    After the user is done interacting with the module, occupation should be freed using the 'free'-method.
    Alternatively, the occupation is automatically freed when the OPC-UA session is closed.
    """

    class States(IntEnum):
        """
        States of the internal state machine of AccessControl
        """
        Freed = 1
        """Any authorized user can get control of the module in this state."""
        Occupied = 2
        """Module is occupied by another user and should be freed first or the user with priority can get control."""
        Local = 4
        """Module is occupied by the local user and must be freed by the local user first."""

    ua_current_occupier_variable: Node
    ua_locked: Node
    ua_locking_client: Node
    ua_remaining_lock_time: Node
    machine: UaFiniteStateMachine  # TODO should be no UaFiniteStateMachine

    def __init__(self, ua_node: Node, ns_idx: int, server: Server, config: BaseConfig):
        self._ua_node = ua_node
        self._ns_idx = ns_idx
        self.server = server
        self.logger = structlog.getLogger("sf.server.AccessControl")
        self.sessions: list[InternalSession] = []
        self.minimum_access = config.MINIMUM_ACCESS
        self.current_occupier: User | None = None
        self.config = config
        self.users = config.USERS
        self._lock = asyncio.Lock()
        self.node_ids_bypass_lock: dict[NodeId, int] = {} # TODO maybe remove when locks for components are implemented
        """ Dictionary of node IDs and their access-level. These nodes can be written to without acquiring the lock. """

    async def init(self) -> None:
        """Asynchronous initialization of the instance."""
        self.machine = UaFiniteStateMachine("AccessControlStateMachine", states=AccessControl.States, initial="Freed")  # type: ignore
        self.machine.add_transition(trigger="free", source=["Occupied", "Local"], dest="Freed",
                                    conditions=[self._condition_access_allowed], after=[self._clear_current_occupier])
        self.machine.add_transition(trigger="occupy", source="Freed", dest="Occupied",
                                    conditions=[self._condition_has_any_access], after=[self._set_current_occupier])
        self.machine.add_transition(trigger="prio", source=["Freed", "Occupied"], dest="Occupied",
                                    conditions=[self._condition_has_greater_priority, self._condition_has_any_access],
                                    after=[self._set_current_occupier])
        self.machine.add_transition(trigger="local", source=["Freed", "Occupied"], dest="Local")
        await self.machine.init(self._ua_node)

        self.ua_current_occupier_variable = await self._ua_node.get_child(f"{self._ns_idx}:LockingUser")

        (self.ua_current_occupier_variable, self.ua_locked, self.ua_locking_client, self.ua_remaining_lock_time,
         ua_node_init_lock, ua_node_exit_lock, ua_node_break_lock, ua_node_renew_lock) = \
            await asyncio.gather(
                self._ua_node.get_child(f"{self._ns_idx}:LockingUser"),
                self._ua_node.get_child(f"{self._ns_idx}:Locked"),
                self._ua_node.get_child(f"{self._ns_idx}:LockingClient"),
                self._ua_node.get_child(f"{self._ns_idx}:RemainingLockTime"),
                self._ua_node.get_child(f"{self._ns_idx}:InitLock"),
                self._ua_node.get_child(f"{self._ns_idx}:ExitLock"),
                self._ua_node.get_child(f"{self._ns_idx}:BreakLock"),
                self._ua_node.get_child(f"{self._ns_idx}:RenewLock")

            )

        await asyncio.gather(
            self.server.historize_node_data_change(self.ua_current_occupier_variable, count=1000),
            self.machine.enable_historizing(self.server),
            self._set_current_occupier(None)
        )

        self.server.iserver.isession.add_method_callback(ua_node_init_lock.nodeid, self._ua_occupy)
        self.server.iserver.isession.add_method_callback(ua_node_exit_lock.nodeid, self._ua_free)
        self.server.iserver.isession.add_method_callback(ua_node_break_lock.nodeid, self._ua_prio)
        self.server.iserver.isession.add_method_callback(ua_node_renew_lock.nodeid, self._ua_renew)

        self._check_for_closed_sessions_loop()

    async def init_ua_users(self, node: Node) -> None:
        """ Initializes OPC UA representation of all users. """
        from .server import UaTypes
        for user in self.users:
            ua_user = await add_object(self._ns_idx, node, ua.QualifiedName(user.name, self._ns_idx),
                                       UaTypes.user_type, instantiate_optional=True)
            await user.ua_init(ua_user)

    async def _update_users_present(self):
        present_users: list[str] = []
        for session in self.get_active_sessions():
            if session.user.name not in present_users:
                present_users.append(session.user.name)

        for user in self.users:
            await write_optional(user.ua_is_present, user.name in present_users)

    def add_node_to_bypass(self, node: Node, min_access_level: int | None = None) -> None:
        """ Adds the given node to bypass locking requirement for write access (minimum access level still required) """
        if node is None:
            raise ValueError("Node cannot be None!")
        if min_access_level is None:
            min_access_level = self.minimum_access
        self.node_ids_bypass_lock[node.nodeid] = min_access_level
        self.logger.info("Added node to bypass locking requirement!", node=node.nodeid.to_string(),
                         min_access_level=min_access_level)

    def remove_node_from_bypass(self, node: Node) -> None:
        """ Removes the given node from bypassing the locking requirement. """
        if node is None:
            raise ValueError("Node cannot be None!")
        del self.node_ids_bypass_lock[node.nodeid]
        self.logger.info("Removed node from bypass locking requirement!", node=node.nodeid.to_string())

    def _check_for_closed_sessions_loop(self, delay: float = 10.0):
        loop = asyncio.get_event_loop()
        loop.call_soon(self._schedule_check_for_closed_sessions)
        loop.call_later(delay, self._check_for_closed_sessions_loop, delay)

    def _schedule_check_for_closed_sessions(self):
        asyncio.create_task(self._check_for_closed_sessions())

    async def _check_for_closed_sessions(self) -> None:
        """
        Checks for closed sessions once. In case of a closed session that is still occupying
        the module, it is automatically freed.
        """
        async with self._lock:
            remove_list = []
            for session in self.sessions:
                if session.state == SessionState.Closed:
                    remove_list.append(session)

            for session in remove_list:
                if self.access_allowed(session.user):
                    self.logger.info("Freeing occupation for closed session.", user=session.user)
                    await self.machine.try_trigger(session.user, "free")
                self.sessions.remove(session)

            if len(remove_list) > 0:
                await self._update_users_present()

    def user_already_logged_in(self, username: str) -> bool:
        """
        Checks whether the given username is already logged in.

        :param username: Name of the user
        :return: True if already logged in, False otherwise
        """
        for session in self.sessions:
            if session.state == SessionState.Activated and session.user.name == username:
                self.logger.info("User is already logged in!", username=username, host=session.name[0])
                return True

        return False

    def check_password(self, user: User, password: bytes | None) -> bool:
        """
        Checks if the given password for the given user instance is correct.
        :return: Returns true if the password is correct, otherwise false.
        """
        if password is None:
            return False
        try:
            if isinstance(user.password, bytes):
                get_scrypt_instance().verify(password, user.password)
            else:
                return user.password == password.decode()  # clear text (e.g. for test cases)
        except InvalidKey:
            return False
        except RuntimeError as re:  # UA_ADAPTER_SALT not set in environment
            self.logger.error(re)

        return True

    @override
    def get_user(self, iserver: InternalServer,
                 username: str | None = None,
                 password: str | bytes | None = None,
                 certificate: bytes | None = None) -> None | User:
        """
        Internal user-manager. Checks whether the given user credentials are correct and also allowed to log in multiple
        times if already logged in. Sets the user of the given session and tracks it internally.

        :return: True if user is allowed to log in, False otherwise.
        """
        active_sessions = self.get_active_sessions()
        for session in active_sessions:
            self.logger.info(
                "Currently active session", username=session.user.name, host=get_hostname_from_ip(session.name[0])
            )

        # grab the session via inspection, this method is called by the corresponding internal session
        isession: InternalSession = currentframe().f_back.f_locals['self']  # type: ignore
        if not isinstance(isession, InternalSession):
            raise RuntimeError("Could not grab internal session, it's a very likely asyncua update broke the dirty "
                               "hack. Please notify the maintainer of the PyUaAdapter library!")

        logger = self.logger.bind(username=username, host=get_hostname_from_ip(isession.name[0]))

        for user in self.users:
            if user.name == username:
                if isinstance(password, str):  # password is string when using sign/encryption OPC-UA endpoints
                    password = bytes(password, 'utf-8')
                if self.check_password(user, password):
                    # new connection
                    if user.allow_multiple or not self.user_already_logged_in(user.name):
                        isession.user = user
                        self.sessions.append(isession)
                        logger.info("Access granted!")
                        asyncio.create_task(self._update_users_present())
                        return user
                    # check for a reconnection attempt of already logged-in user (thx to FeDi)
                    elif self.config.ALLOW_RECONNECTION_FROM_SAME_HOST:
                        for session in active_sessions:
                            # ensure if IP-addresses are equal AND the username is equal to the one of that specific IP-Address
                            if (session.name[0] == isession.name[0]) and (session.user.name == username):
                                loop = asyncio.get_event_loop()
                                task = loop.create_task(session.close_session())  # now close existing session
                                isession.user = user
                                self.sessions.append(isession)
                                logger.info("Access granted (again)!")
                                asyncio.create_task(self._update_users_present())
                                return user

        logger.warning("Access denied!")
        return None

    def get_active_sessions(self) -> list[InternalSession]:
        """ Returns a list of all active OPC-UA sessions """
        return [session for session in self.sessions if session.state == SessionState.Activated]

    def access_allowed(self, user: User | UaUser, access_required: int = 0, check_occupation: bool = True) -> bool:
        """
        Checks whether the user is allowed to access. This check is based on whether the user occupies the module and
        whether the access rights are equal or greater than what is required.

        :param user: Named tuple of the user
        :param access_required: Access level to check against
        :param check_occupation: Check occupation (default True) or bypass it (False).
        :return: True if access is allowed, False otherwise
        """
        if user is None:
            return False
        try:
            if user.role == UserRole.Admin:  # should only be used for internal skill calls etc.
                return True
            if not isinstance(user, User):
                return False
            if check_occupation and user != self.current_occupier:
                return False
            return user.access >= access_required
        except AttributeError as err:
            self.logger.exception(err)
            return False

    def _condition_access_allowed(self, user: User) -> bool:
        if not self.access_allowed(user):
            raise ua.UaStatusCodeError(ua.StatusCodes.BadUserAccessDenied)
        return True

    def _condition_has_any_access(self, user: User) -> bool:
        if user.role == UserRole.User and not user.access >= self.minimum_access:
            raise ua.UaStatusCodeError(ua.StatusCodes.BadUserAccessDenied)
        return True

    def _condition_has_greater_priority(self, user: User) -> bool:
        if self.current_occupier is not None and user.priority <= self.current_occupier.priority:
            raise ua.UaStatusCodeError(ua.StatusCodes.BadRequestNotAllowed)
        return True

    async def set_access_key_inserted(self, key_status: bool) -> None:
        """
        Sets the access key status which automatically tries to occupy the module for user 'operator'
        (with prio when necessary) when the key is inserted.
        If the key is pulled out, the occupation is automatically freed.

        :param key_status: True for inserted, False otherwise.
        """
        for session in self.sessions:
            if session.user.name == "operator":
                if key_status:  # key inserted
                    if self.machine.state == AccessControl.States.Freed:  # type: ignore
                        await self._occupy(session.user)
                    else:
                        await self._prio(session.user)
                else:
                    await self._free(session.user)

    async def _clear_current_occupier(self, *args, **kwargs):
        await self._set_current_occupier(None)

    async def _set_current_occupier(self, occupier: User | None) -> None:
        if occupier is None:
            self.logger.info("Clearing current occupier")
            await self.ua_current_occupier_variable.set_value("")
            await self.ua_locking_client.set_value("")
            await self.ua_locked.write_value(False)
            await self.ua_remaining_lock_time.write_value(0)
        elif hasattr(occupier, "name") and occupier.name is not None:
            self.logger.info("Setting current occupier", username=occupier.name)
            await self.ua_current_occupier_variable.set_value(occupier.name)
            await self.ua_locked.write_value(True)
            await self.ua_remaining_lock_time.write_value(99999)

            for isession in self.sessions:
                if isession.user.name == occupier.name:
                    await self.ua_locking_client.set_value(get_hostname_from_ip(isession.name[0]))
        else:
            self.logger.info("Occupied internally")
            await self.ua_current_occupier_variable.set_value("SERVER")
            await self.ua_locked.write_value(True)
        self.current_occupier = occupier

    async def _free(self, user: User):
        return await self.machine.try_trigger(user, 'free')

    @uamethod
    async def _ua_free(self, parent, session: InternalSession, *args):
        self.logger.debug("Free method called", username=session.user.name)
        return await self._free(session.user)

    async def _occupy(self, user: User):
        await self._check_for_closed_sessions()  # so we don't need to wait for the longer running loop
        return await self.machine.try_trigger(user, "occupy")

    @uamethod
    async def _ua_occupy(self, parent, session: InternalSession, *args):
        self.logger.debug("Occupy method called", username=session.user.name)
        return await self._occupy(session.user)

    async def _prio(self, user: User):
        return await self.machine.try_trigger(user, 'prio')

    @uamethod
    async def _ua_prio(self, parent, session: InternalSession, *args):
        self.logger.debug("Prio method called", username=session.user.name)
        return await self._prio(session.user)

    @uamethod
    async def _ua_renew(self, parent, session: InternalSession, *args):
        self.logger.debug("Renew method called", username=session.user.name)
        # TODO @SiJu Should we implement this some time?


class AccessControlAttributeService(AttributeService):
    """
    AccessControl based AttributeService for OPC-UA, requiring a user to occupy the module first before writing access
    in general is granted. Note that most variables are read-only, see OPC-UA write masks.
    """

    def __init__(self, aspace: AddressSpace, access_control: AccessControl):
        super().__init__(aspace)
        self._access_control = access_control

    async def check_range(self, write_value: ua.WriteValue) -> bool:
        """ Returns True if the given write_value is inside the range (if modelled). Otherwise, returns False."""

        # only check if value attributes are written to
        if write_value.AttributeId != ua.AttributeIds.Value.value:
            return True

        node = self._access_control.server.get_node(write_value.NodeId)

        try:  # make sure value to write is within modelled range (if it is modelled)
            range_node = await node.get_child("0:EURange")
            _range: ua.Range | None = await range_node.read_value()

            if _range is None:
                return True  # No Range -> pass

            value = write_value.Value.Value.Value  # type: ignore
            if value < _range.Low or value > _range.High:
                self._access_control.logger.info(
                    "Denying writing value", value=value, target=write_value.NodeId.Identifier, range=_range)
                return False
        except ua.uaerrors.BadNoMatch:  # when there is no modeled range, we cannot check it ;)
            pass

        return True

    @override
    async def write(self, params: ua.WriteParameters, user: User | UaUser = INTERNAL_USER) -> list[ua.StatusCode]:
        result = []
        for write_value in params.NodesToWrite:
            try:
                access_required = self._access_control.node_ids_bypass_lock[write_value.NodeId]
                # Node IDs in this dict are allowed to bypass the locking requirement, so skip the
                # occupation check. Every other node ID will raise an KeyError.
                check_occupation = False
            except KeyError:
                access_required = 1  # TODO should this be configurable?
                check_occupation = True

            if self._access_control.access_allowed(
                    user, access_required=access_required, check_occupation=check_occupation):
                if not await self.check_range(write_value):
                    result.append(ua.StatusCode(ua.StatusCodes.BadOutOfRange))  # type: ignore
                else:
                    result.extend(await super().write(ua.WriteParameters([write_value]), user))
            else:
                result.append(ua.StatusCode(ua.StatusCodes.BadUserAccessDenied))  # type: ignore

        return result


@dataclass
class SessionUaVariant:
    """ This exists because the uamethod decorator unpacks arguments and expects a Value attribute. """
    Value: InternalSession


class AccessControlMethodService(MethodService):
    @override
    async def _run_method(self, func, parent, *args):
        # grab the session via inspection
        session: InternalSession = currentframe().f_back.f_back.f_back.f_locals['self']  # type: ignore
        if not isinstance(session, InternalSession):
            raise RuntimeError("Could not grab internal session, it's a very likely asyncua update broke the dirty "
                               "hack. Please notify the maintainer of the PyUaAdapter library!")

        if asyncio.iscoroutinefunction(func):
            return await func(parent, SessionUaVariant(session), *args)
        p = partial(func, parent, session, *args)
        res = await asyncio.get_event_loop().run_in_executor(self._pool, p)
        return res


class AccessControlSubscriptionHandler:
    """ Handles OPC-UA subscription data changes of key status accordingly for the given access control instance. """

    def __init__(self, access_control: AccessControl):
        self._access_control = access_control

    async def datachange_notification(self, node: Node, val, data) -> None:
        """ OPC-UA subscription callback """
        await self._access_control.set_access_key_inserted(val)
