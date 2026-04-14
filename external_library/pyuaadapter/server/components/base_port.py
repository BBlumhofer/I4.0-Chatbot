from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Dict, Type

import aiohttp
import structlog
from asyncua import Node, Server

from pyuaadapter.common.enums import SkillStates
from pyuaadapter.server import BaseConfig
from pyuaadapter.server.base_component import BaseComponent
from pyuaadapter.server.base_machinery_item import BaseMachineryItem
from pyuaadapter.server.spatial_object import SpatialObject

if TYPE_CHECKING:  # prevent circular imports during run-time
    from pyuaadapter.server.skills.base_couple_skill import BaseCoupleSkill


class BasePort(BaseComponent, ABC):
    """ Abstract base class representing a topology port. """

    ua_active_port: Node
    ua_position: Node
    ua_skills: Node
    ua_tag_neighbor: Node
    ua_tag_own: Node
    couple_skill: BaseCoupleSkill | None
    _couple_skill_cls : Type[BaseCoupleSkill] | None

    def __init__(self, server: Server, parent: "BaseMachineryItem", ns_idx: int, _id: str, name: str,
                 rfid_tag_own: int, config: BaseConfig,
                 couple_skill: Type[BaseCoupleSkill] | None = None,
                 couple_skill_kwargs: Dict[str, Any] | None = None,
                 spatial_object: SpatialObject | None = None):
        """
        Creates a new gate instance.

        :param _id: id of the gate (sequential number starting at 1)
        :param rfid_tag_own: RFID tag content attached to module
        """

        super().__init__(server, parent=parent, ns_idx=ns_idx, _id=_id, name=name, config=config, spatial_object=spatial_object)
        self.module = self.root_parent
        self.rfid_tag_own = "Unknown"
        self._rfid_tag_own_raw = rfid_tag_own
        self.couple_skill = None
        self._couple_skill_cls = couple_skill
        self._couple_skill_kwargs: Dict[str, Any] = couple_skill_kwargs if couple_skill_kwargs is not None else {}
        self.logger = structlog.getLogger("sf.server.Port", name=self.full_name)

    async def init(self, parent_node: Node, component_type: Node | None = None) -> None:
        """
        Asynchronous initialization.

        :param parent_node: parent OPC-UA node, ideally a folder type
        :param component_type: node to used to instantiate object
                               -> None since type is always port_type but to support reflection of child
        """
        from pyuaadapter.server import UaTypes
        await super().init(folder_node=parent_node, component_type=UaTypes.port_type)
        self.rfid_tag_own = await self.get_rfid_tag_name(self._rfid_tag_own_raw)

    async def _init_component_identification(self, manufacturer: str | None = None,
                                             serial_number: str | None = None,
                                             product_instance_uri: str | None = None) -> None:
        await self._init_identification(manufacturer=manufacturer, serial_number=serial_number,
                                        product_instance_uri=product_instance_uri)

    async def _init_notification(self) -> None:
        # add optional notification for port
        await super()._init_notification()

    async def _init_attributes(self) -> None:
        await super()._init_attributes()

        from pyuaadapter.server import UaTypes

        self.ua_active_port, self.ua_tag_own = await asyncio.gather(
            self.ua_attributes.get_child([f"{UaTypes.ns_machine_set}:IsActive"]),
            self.ua_attributes.get_child([f"{UaTypes.ns_machine_set}:OwnRfidTag"]),
        )

        await asyncio.gather(
            self.ua_active_port.write_value(self._couple_skill_cls is not None),  # if we have a couple skill, we are active
            self.ua_tag_own.write_value(self.rfid_tag_own),
        )

    async def _init_monitoring(self) -> None:
        await super()._init_monitoring()

        from pyuaadapter.server import UaTypes

        self.ua_tag_neighbor, self.magnets_closed = await asyncio.gather(
            self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:PartnerRfidTag"]),
            self.ua_monitoring.get_child([f"{UaTypes.ns_machine_set}:MagnetsClosed"])
        )

        await self.ua_tag_neighbor.write_value("")

    async def _init_skills(self) -> None:
        await super()._init_skills()

        if self._couple_skill_cls is not None:
            self.couple_skill = await self.add_skill(**self._couple_skill_kwargs, skill=self._couple_skill_cls)

    async def _request_rfid_from_api(self, rfid: int, timeout: float = 5.0) -> str:
        async with aiohttp.ClientSession() as session:  # noqa: SIM117
            url = self.module.config.PORT_API.format(rfid)
            self.logger.info("Requesting RFID mapping", rfid=rfid, url=url)
            async with session.get(url, timeout=timeout, raise_for_status=True) as response:
                text = await response.text()
                try:
                    return json.loads(text)  # we expect JSON, but that might change in the future...
                except json.decoder.JSONDecodeError:
                    self.logger.warning("Could not parse response, falling back to text.", rfid=rfid, text=text)
                    return text


    async def get_rfid_tag_name(self, rfid: int, timeout: float = 5.0) -> str:
        """ Returns the human-readable tag name from the given tag ID number. """
        if self.module.config.PORT_API_ENABLE:
            try:
                return await self._request_rfid_from_api(rfid, timeout=timeout)
            except Exception as err:
                self.logger.warning("Error getting RFID data from API, fallback to provided configuration.", err=err)

        try:
            return self.module.config.RFID_NEIGHBOUR_MAPPING[rfid]
        except KeyError:
            self.logger.warning("Could not find RFID in local mapping!", rfid=rfid)
            return str(rfid)

    async def set_rfid_tag_neighbor(self, content: str | int) -> None:
        """
        Sets the RFID tag content attached to neighbor.

        :param content: RFID tag content of neighbor.
        If it is a number, it will automatically be mapped to the human-readable tag name.
        Otherwise, it assumes it is already human-readable.
        """
        if isinstance(content, int):
            content = await self.get_rfid_tag_name(content)
        await self._log_info(f"Set neighbor tag to '{content}'!")
        await self.ua_tag_neighbor.write_value(str(content))

    async def set_magnets_closed(self, closed: bool) -> None:
        """
        Sets the magnets closed boolean variable.

        :param closed: boolean variable if magnet is closed.
        It is a boolean that should be True if magnets are closed and False if magents are open.
        """
        await self._log_info(f"Set magnets closed to '{closed}'!")
        await self.magnets_closed.write_value(closed)

    async def set_monitoring_values(self, rfid_tag_neighbor: str | int, closed: bool) -> None:
        await self.set_rfid_tag_neighbor(rfid_tag_neighbor)
        await self.set_magnets_closed(closed)

    async def enable_historizing(self, server: Server, count: int = 1000) -> None:
        """
        Enables OPC-UA historizing for the gate.

        :param server: OPC-UA server reference
        :param count: how many changes should be stored in history
        """
        await server.historize_node_data_change([self.ua_tag_neighbor], count=count)

    def is_mated(self) -> bool:
        """ Return whether this gate is mated. """
        if self.couple_skill is None:
            raise NotImplementedError  # TODO how should this be implemented for passive ports?
        else:
            return self.couple_skill.current_state == SkillStates.Running
