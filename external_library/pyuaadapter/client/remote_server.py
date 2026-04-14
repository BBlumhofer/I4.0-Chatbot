""" This module provides the entry point for accessing remote OPC UA servers using the skill node-set v3+
and a callback interface for remote server events. """
from __future__ import annotations

import asyncio
import datetime
from asyncio import Task
from enum import IntEnum, auto
from typing import TYPE_CHECKING, Any

import structlog
from asyncua import Client, Node, ua
from asyncua.common.subscription import DataChangeNotif
from asyncua.crypto.cert_gen import generate_private_key, generate_self_signed_app_certificate
from asyncua.crypto.security_policies import SECURITY_POLICY_TYPE_MAP
from asyncua.ua import NodeId, SecurityPolicyType, UaError
from asyncua.ua.uaerrors import BadNoMatch, BadSessionClosed, BadSessionIdInvalid, BadUserAccessDenied
from cryptography import x509
from cryptography.hazmat._oid import ExtendedKeyUsageOID
from cryptography.hazmat.primitives import serialization

import pyuaadapter
from pyuaadapter.common.namespace_uri import (
    NS_DI_URI,
    NS_MACHINE_SET_URI,
    NS_MACHINERY_URI,
    NS_SFM_V3_URI,
    NS_SKILL_SET_URI,
)
from pyuaadapter.common.subscription_manager import SubscriptionManager

from ..common.exceptions import UnsupportedSkillNodeSetError

if TYPE_CHECKING:
    from .remote_module_v4 import RemoteModule  # technically not correct since it could also be a v3 module...


class RemoteServerStatus(IntEnum):
        DISCONNECTED = auto()
        """ The client is not connected to a server."""
        CONNECTING = auto()
        """ The client is trying to connect to a server. """
        BROWSING = auto()
        """ The client is connected, but is busy browsing the server namespace. """
        CONNECTED = auto()
        """ The client is connected and ready to be used. """

class RemoteServerSubscriber:
    """Callback interface for subscribers of remote server events. Also supports these methods async! """

    def on_connection_lost(self) -> None:
        """Callback method which is called when the connection to the remote server is lost."""
        pass

    def on_connection_established(self) -> None:
        """Callback method which is called when the connection to the remote server is established."""
        pass

    def on_server_time_update(self, current_server_time: datetime.datetime) -> None:
        """Callback method which is called when the current server time of the remote server is updated."""
        pass

    def on_status_change(self, status: RemoteServerStatus) -> None:
        """Callback method which is called when the status of the client changes. """
        pass



class RemoteServer:
    """ Central class for accessing a (remote) OPC UA server using the skill node-set v3+.

    After connecting to a server for the first time, it's address space needs to be browsed. If
    your application only requires certain parts of the address space, i.e. only components, you can
    skip unnecessary browsing by setting the browse_* options of the constructor accordingly. This
    will speed up the connection speed.

    Additionally, if the address space of the OPC UA server is stable, it does not need to be browsed
    again after a disconnect (since we assume that nothing changed). If this is the case for your
    application, set the `browse_on_reconnect` to False.
    """

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        *,
        timeout: float = 10.0,
        browse_skills: bool = True,
        browse_identification: bool = True,
        browse_resources: bool = True,
        browse_methods: bool = True,
        browse_on_reconnect: bool = True,
        setup_logging: bool = True,
        log_levels: dict[str, int | str] | None = None,
        security_policy: SecurityPolicyType = SecurityPolicyType.NoSecurity,
    ):
        """Creates new RemoteServer instance.

        :param url: The URL of the OPC UA server to connect to, i.e. opc.tcp://localhost:4843/
        :param username: Username used for authentication of the given OPC UA server.
        :param password: Password used for authentication of the given OPC UA server.
        :param timeout: Timeout in seconds for connection tries.
        :param browse_methods: If false, all methods will be skipped during browsing.
        :param browse_identification: If false, identification of machines/components will be skipped during browsing.
        :param browse_resources: If false, resources of machines will be skipped during browsing.
        :param browse_skills: If false, all skills will be skipped during browsing.
        :param browse_on_reconnect: If false, server address space will not be browsed on reconnection (after a
            disconnect happened).
        :param setup_logging: If True, logging is automatically set up. False allows you to set up logging the way you
            like it.
        :param security_policy: OPC UA security policy used for the connection. Default: No security policy.
        """
        self.url = url
        self.username = username
        self.password = password
        self._security_policy = security_policy
        self.timeout = timeout
        self.browse_identification = browse_identification
        self.browse_skills = browse_skills
        self.browse_resources = browse_resources
        self.browse_methods = browse_methods
        self.browse_on_reconnect = browse_on_reconnect

        self._status = RemoteServerStatus.DISCONNECTED
        """State of this client."""
        self._first_connection = True
        """Flag indicating whether this is our first connection (e.g. we definitely need to browse the server)."""

        self.subscription_manager = SubscriptionManager()

        self.namespace_map = {  # Default values, will be overwritten on connection
            NS_DI_URI: 2,
            NS_MACHINERY_URI: 3,
            NS_SKILL_SET_URI: 4,
            NS_MACHINE_SET_URI: 5
        }

        self.node_map: dict[NodeId, Any] = {}
        """ Maps OPC UA node IDs to Remote* instances. """

        self._machines: dict[str, "RemoteModule"] = {}
        self._subscribers: list[RemoteServerSubscriber] = []

        self._auto_reconnect_task: Task | None = None

        if setup_logging:
            pyuaadapter.common.setup_logging(log_levels=log_levels)
        self.logger = structlog.getLogger("sf.client.RemoteServer", url=url, username=username)

    def add_subscriber(self, subscriber: RemoteServerSubscriber) -> None:
        """ Adds given subscriber to the list of subscribers to be notified. """
        self._subscribers.append(subscriber)

    def remove_subscriber(self, subscriber: RemoteServerSubscriber) -> None:
        """ Remove given subscriber from the list of subscribers to be notified. """
        self._subscribers.remove(subscriber)

    async def set_status(self, status: RemoteServerStatus) -> None:
        self.logger.info("New status", status=status.name)
        self._status = status
        for sub in self._subscribers:
            if asyncio.iscoroutinefunction(sub.on_status_change):
                await sub.on_status_change(status)  # type: ignore
            else:
                sub.on_status_change(status)

    async def connect(self, timeout: float = 10.0,
                      reconnect_try_delay: float = 10.0,
                      max_retries: int | None = 3) -> RemoteServer:
        """
        Connect to the remote module with the given username and password.

        :param timeout: Timeout (in seconds) for each request to the OPC UA server
        :param reconnect_try_delay: Delay (in seconds) between reconnection attempts.
        :param max_retries: Limits the number of tries for the initial connection attempts.
            Use `None` for unlimited tries.
        """
        self.timeout = timeout
        await self._try_to_connect(reconnect_try_delay=reconnect_try_delay, max_retries=max_retries)

        # setup auto reconnection after successful connection to the server
        self._auto_reconnect_task = asyncio.create_task(
            self._auto_reconnect(reconnect_try_delay), name="Client Auto Reconnect"
        )
        return self  # allows chaining

    async def disconnect(self) -> None:
        """ Disconnect from the remote module. Will also cancel the auto reconnection."""
        self.logger.info("Disconnecting...")
        if self._auto_reconnect_task is not None:
            self._auto_reconnect_task.cancel()
        await self._ua_client.disconnect()
        await self.set_status(RemoteServerStatus.DISCONNECTED)

    async def _set_security(self):
        if self._security_policy == SecurityPolicyType.NoSecurity:
            return  # Default, we don't need to anything

        # TODO also load from file?
        key = generate_private_key()
        key_bytes = key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        cert = generate_self_signed_app_certificate(
            private_key=key,
            common_name="PyUaAdapter Client",
            names={},
            subject_alt_names=[x509.UniformResourceIdentifier("urn:pyuaadapter:client")],  # TODO
            extended=[ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH],
            days=3650,
        )
        cert_bytes = cert.public_bytes(serialization.Encoding.DER)

        policy, mode, _ = SECURITY_POLICY_TYPE_MAP[self._security_policy]
        self.logger.info(f"Setting security to {policy=}, {mode=}")
        await self._ua_client.set_security(policy=policy, certificate=cert_bytes, private_key=key_bytes, mode=mode)


    async def _connect(self):
        self._ua_client = Client(url=self.url, timeout=self.timeout)
        self._ua_client.set_user(self.username)
        self._ua_client.set_password(self.password)
        await self._set_security()

        await self.set_status(RemoteServerStatus.CONNECTING)
        await self._ua_client.connect()

        try:
            custom_objs = await self._ua_client.load_data_type_definitions()
            for name, obj in custom_objs.items():
                self.logger.debug("Found custom object", name=name, repr=repr(obj))
        except:
            self.logger.warning("Could not not load custom data type definitions!")

        # iterate through server namespace array to figure out correct namespace indexes
        namespace_array = await self._ua_client.get_namespace_array()
        if NS_MACHINE_SET_URI not in namespace_array:
            self.logger.warning("Could not find SFM namespace in server!")

        for index, namespace in enumerate(namespace_array):
            self.namespace_map[namespace] = index

        if self._first_connection or self.browse_on_reconnect:
            await self.set_status(RemoteServerStatus.BROWSING)
            self.node_map.clear()
            await self.subscription_manager.clear_subscriptions()
            await self.subscription_manager.init(self._ua_client)
            await self._iterate_machines()  # Iterate through all modules (v1-v3) / machines (v4)
            await self.setup_subscriptions()
        else:
            await self.subscription_manager.renew_subscriptions(self._ua_client)

        self.logger.info(f"Monitoring {self.subscription_manager.no_of_monitored_items} items in subscription.")

        self._first_connection = False
        await self.set_status(RemoteServerStatus.CONNECTED)
        for sub in self._subscribers:
            if asyncio.iscoroutinefunction(sub.on_connection_established):
                await sub.on_connection_established()
            else:
                sub.on_connection_established()

    @property
    def ua_client(self) -> Client:
        return self._ua_client

    async def setup_subscriptions(self) -> None:
        current_time_node = self._ua_client.get_node(ua.NodeId(Identifier=ua.Int32(2258), NamespaceIndex=ua.Int16(0)))
        await self.subscription_manager.subscribe_data_change(self, current_time_node)


    async def datachange_notification(self, _node: Node, val: Any, _data: DataChangeNotif) -> None:
        for sub in self._subscribers:
            if asyncio.iscoroutinefunction(sub.on_server_time_update):
                await sub.on_server_time_update(val)
            else:
                sub.on_server_time_update(val)

    async def _iterate_machines(self):
        """ Iterates through all machines / modules. """

        # First, try with v4, if that fails, try with v3.
        try:
            ua_module_set = await self._ua_client.get_objects_node().get_child(
                f"{self.namespace_map[NS_MACHINERY_URI]}:Machines")
            from pyuaadapter.client.remote_module_v4 import RemoteModule
            self.logger.info("Found a v4 compatible server, iterating through all available machines.")
        except BadNoMatch:  # not a v4 server
            try:
                ua_module_set = await self._ua_client.get_objects_node().get_child(
                    f"{self.namespace_map[NS_SFM_V3_URI]}:ModuleSet")
                from pyuaadapter.client.remote_module_v3 import RemoteModule  # type: ignore
                self.logger.info("Found a v3 compatible server, iterating through all available modules.")
            except BadNoMatch as err:
                raise UnsupportedSkillNodeSetError(
                    "Given server is neither a v4 or v3 compatible OPC UA skill server!") from err

        # Now, actually iterate through the machines/modules. The correct variant will be imported above
        for child in await ua_module_set.get_children():
            name = (await child.read_browse_name()).Name
            self.logger.info("Processing machine...", bname=name)

            try:
                module = RemoteModule(name=name, base_node=child, remote_server=self)
                await module.setup_subscriptions(self.subscription_manager)
                self._machines[name] = module
            except UaError as ex:
                self.logger.warning("Could not browse machine!", name=name)
                self.logger.exception(ex)

    async def _try_to_connect(self, reconnect_try_delay: float = 10.0, max_retries: int | None = None):
        try_count = 1
        while True:
            try:
                await self._connect()
                return
            except ConnectionRefusedError:
                self.logger.warning("Could not connect, ConnectionRefusedError!")
            except asyncio.exceptions.TimeoutError:
                self.logger.warning("Could not connect, TimeoutError!")
            except BadUserAccessDenied:  # most users are only allowed 1 simultaneous login
                # TODO how to differentiate wrong password?
                self.logger.warning("Could not login, BadUserAccessDenied!")

            try_count += 1
            if max_retries is not None and try_count > max_retries:  # give up after optional max_retries argument
                raise ConnectionError("Reached maximum number of retries, giving up!")

            msg = f"Trying to connect again in {reconnect_try_delay} seconds"
            if max_retries is not None:
                msg += f" (Attempt {try_count}/{max_retries})"
            self.logger.warning(msg)

            await asyncio.sleep(reconnect_try_delay)

    async def _auto_reconnect(self, reconnect_try_delay: float = 5.0):
        while True:
            try:
                await self._ua_client.check_connection()
                await asyncio.sleep(0.5)
            except (AttributeError, ConnectionError, BadSessionIdInvalid, BadSessionClosed,
                    asyncio.exceptions.TimeoutError):
                self.logger.warning("Lost connection, trying to reconnect...")
                await self.set_status(RemoteServerStatus.DISCONNECTED)
                for sub in self._subscribers:
                    if asyncio.iscoroutinefunction(sub.on_connection_lost):
                        await sub.on_connection_lost()
                    else:
                        sub.on_connection_lost()

                await self._try_to_connect(reconnect_try_delay=reconnect_try_delay, max_retries=None)  # never give up
            except Exception as ex:
                self.logger.exception(ex)  # TODO proper exception handling
                await asyncio.sleep(0.5)

    @property
    def status(self) -> RemoteServerStatus:
        """ Status of the client. """
        return self._status

    @property
    def connected(self) -> bool:
        """ Whether we are currently connected to the remote module. """
        return self._status == RemoteServerStatus.CONNECTED

    @property
    def machines(self) -> dict[str, "RemoteModule"]:  # skill node set v4 naming
        """Provide all available machines/modules in dictionary form using the name of the machine as the key."""
        return self._machines

    @property
    def modules(self) -> dict[str, "RemoteModule"]:  # skill node set v3 naming
        """Provide all available machines/modules in dictionary form using the name of the machine as the key."""
        return self._machines
