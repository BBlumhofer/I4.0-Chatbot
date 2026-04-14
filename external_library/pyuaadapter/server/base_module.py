from __future__ import annotations

import asyncio
import importlib
from abc import abstractmethod
from typing import List

import structlog
from asyncua import Node, Server, ua
from typing_extensions import deprecated, override

from pyuaadapter.server.resources.battery_resource import BatteryResource

from ..common.enums import SkillStates
from . import BaseConfig
from .access_control import AccessControl, AccessControlAttributeService, AccessControlMethodService
from .base_callable import BaseCallable
from .base_machinery_item import BaseMachineryItem
from .base_skill_continuous import BaseSkillContinuous
from .common import add_object
from .data_classes import Orientation, Position
from .plugins import AVAILABLE_PLUGINS, BasePlugin
from .resources.carrier_resource import CarrierResource
from .resources.nubstone_resource import NubstoneResource
from .resources.truck_resource import TruckResource
from .skills.base_startup_skill import BaseStartupSkill
from .spatial_object import SpatialObjectList, WorldFrame
from .ua_fsm import UaFiniteStateMachine
from .ua_types import UaTypes
from .user import User


class BaseModule(BaseMachineryItem):
    """ Base class representing a new SmartFactory-KL demo plant module"""

    access_control: AccessControl
    _spatial_object_list: SpatialObjectList

    def __init__(self, server: Server, ns_idx: int, _id: str, name: str, config: BaseConfig):
        super().__init__(server=server, parent=None, ns_idx=ns_idx, _id=_id, name=name, config=config)
        self.logger = structlog.get_logger("sf.server.Module", name=self.full_name)
        self.running = True
        self.plugins: List[BasePlugin] = []
        self._add_enabled_plugins()

    def _add_enabled_plugins(self):
        for plugin_name, plugin_module_name in AVAILABLE_PLUGINS.items():
            try:
                module = importlib.import_module(plugin_module_name, "pyuaadapter.server.plugins")
                plugin_instance: BasePlugin = module.Plugin(self.config)
                if plugin_instance.is_enabled:
                    self.logger.info(f"Plugin '{plugin_name}' enabled.")
                else:
                    self.logger.info(f"Plugin '{plugin_name}' not enabled.")
            except ModuleNotFoundError as err:
                self.logger.info(f"Plugin '{plugin_name}' cannot be enabled, missing library", err=err)

    @override
    async def init(self, folder_node: Node) -> None:
        """ Initialize the module asynchronously.

        :param folder_node: parent OPC-UA node, ideally a folder type
        """
        self._ua_node = await add_object(
            self.ns_idx, folder_node, ua.QualifiedName(self.name, UaTypes.ns_machine_set),
            UaTypes.module_type, instantiate_optional=False)
        #TODO?: asyncua hardcodes references types (folder --> organize, all others hasComponent): see (copy_node_util.py)

        await UaFiniteStateMachine.init_class(self.ns_idx)  # initialize before use in access control, own state, skills
        await self._init_access_control()
        BaseCallable.init_class(self.server, self.ns_idx, self.access_control)

        await self._init_notification()  # may need logs during initialization
        await self._init_monitoring()  # assets may need position from monitoring

        await self._init_resources()
        await asyncio.gather(  # order is not important
            self._init_machine_identification(),
            self._init_components(),
            self._init_attributes(),
            self._init_parameter_set(),
            self._init_requirements(),
            self._init_plugins(),
        )

        await self._init_skills()  # gates are potentially required for some skills
        await self._init_methods()
        # depending on start up and initials start up might be executed automatically
        while self.skills[BaseStartupSkill.NAME].current_state == SkillStates.Starting:  # noqa: ASYNC110
            await asyncio.sleep(0.1)

        await self._init_status() # cause of initial skills init status after skills are initialized
        await self._init_users()  # needs the MachineryBuildingBlocks node

        self._validate()

        for plugin in self.plugins:
            await plugin.after_module_init()

        await self._delete_empty_folders()

        self._initialized = True

    @abstractmethod
    async def _init_machine_identification(self) -> None:
        """
        Forces user to call child method _init_identification()
        """

        pass

    async def _init_monitoring(self) -> None:
        """
        Should be called by parent to set position and orientation
        """

        await super()._init_monitoring()

        await add_object(ns_idx=self.ns_idx, location=self.ua_monitoring,
                         bname=ua.QualifiedName("MachineRoomList", UaTypes.ns_rsl),
                         object_tyoe=UaTypes.spatial_object_list) # optional

        self._spatial_object_list = SpatialObjectList(WorldFrame(position=Position(0,0,0),
                                                                  orientation=Orientation(0,0,0)))
        await self._spatial_object_list.init(self)
        ua_rsl_location = await self.server.get_objects_node().get_child(f"{UaTypes.ns_rsl}:RelativeSpatialLocations")
        await ua_rsl_location.add_reference(self._spatial_object_list.ua_node, ua.ObjectIds.Organizes)

    async def _init_notification(self) -> None:
        # overriding creates notification folder
        await super()._init_notification()

    async def _init_access_control(self) -> None:

        self.access_control = AccessControl(await self.ua_node.get_child(f"{UaTypes.ns_di}:Lock"),
                                            UaTypes.ns_di, self.server, self.config)

        await self.access_control.init()

        self.server.iserver.set_user_manager(self.access_control)
        self.server.iserver.method_service = AccessControlMethodService(self.server.iserver.aspace)
        self.server.iserver.attribute_service = AccessControlAttributeService(
            self.server.iserver.aspace, self.access_control
        )

    async def _init_users(self) -> None:
        """ Initialize OPC UA representation of users. """
        ua_users = await add_object(self.ns_idx, self.ua_machinery_building_blocks,
                                    ua.QualifiedName("Users", self.ns_idx), UaTypes.users_type)
        await self.access_control.init_ua_users(ua_users)

    @abstractmethod
    async def _init_resources(self) -> None:
        await super()._init_resources()

        # TODO @SiJu should be module specific, no?
        await NubstoneResource.init(self.ns_idx)
        await TruckResource.init(self.ns_idx)
        await BatteryResource.init(self.ns_idx)
        await CarrierResource.init(self.ns_idx)

    async def _init_plugins(self):
        for plugin in self.plugins:
            await plugin.init(self)

    #####################################
    # FSM Conditions

    # Raise UaStatusCodeError for correct OPC-UA status code answers instead of a misc one

    @override
    async def _condition_access_allowed(self, user: User) -> bool:
        if not self.access_control.access_allowed(user, 2):  # operator access level or higher required
            await self._log_error(f"Denied, user '{user}' has no access to this module!")
            raise ua.UaStatusCodeError(ua.StatusCodes.BadUserAccessDenied)
        return True

    def _validate(self) -> None:
        """ Validates whether the module was correctly set-up by the user. """

        # check for mandatory skills, ShutdownSkill skill is optional in newer node sets
        mandatory_skills = [BaseStartupSkill.NAME]
        for skill_name, skill in self.skills.items():
            if skill_name == BaseStartupSkill.NAME and isinstance(skill, BaseSkillContinuous):
                mandatory_skills.remove(skill_name)

        if len(mandatory_skills):
            raise RuntimeError(f"Please provide the missing mandatory skills: {mandatory_skills}!")

    @property
    @deprecated("Please use ua_node instead!")
    def ua_module(self) -> Node:
        """ Main node of the module. """
        return self._ua_node

    @property
    def spatial_object_list(self) -> SpatialObjectList:
        return self._spatial_object_list

    @property
    @override
    def root_parent(self) -> "BaseModule":
        return self
