from __future__ import annotations

from abc import ABC

import structlog
from asyncua import Node, ua
from typing_extensions import ClassVar

from pyuaadapter.server.common import add_object, add_property


class BaseResource(ABC):
    """ Base class for all resources. """
    asset_id: str
    """ Asset ID of this resource (part of Identification). """
    component_name: str
    """ Human-readable (component) name of this resource (part of Identification). """
    resource_class: str
    """ Type ('ResourceClass') of this resource, i.e. 'Cab', 'Trailer' etc (part of Identification). """
    _ua_node: Node
    """ OPC UA Node represented by this resource instance. """
    _ua_amount: Node | None
    """ (Optional) OPC UA Node of the 'Amount' of this resource (part of Monitoring). """

    _ua_resource_type: ClassVar[Node]
    """ OPC UA Node specifying which object type will be used for instantiation of OPC UA object representing 
    this resource. Must be set during inheriting class initialization."""

    def __init__(self, amount: int | None = None):
        self._logger = structlog.getLogger("sf.server.Resource", name=self.component_name)
        self.amount = amount
        """ Optional amount of this resource (part of Monitoring). """

    async def _fill_resource_obj(self, ns_idx: int, **kwargs) -> None:
        from pyuaadapter.server import UaTypes

        ua_identification = await self._ua_node.get_child(f"{UaTypes.ns_machine_set}:Identification")

        await (await ua_identification.get_child(f"{UaTypes.ns_di}:AssetId")).set_value(self.asset_id)
        await (await ua_identification.get_child(f"{UaTypes.ns_di}:ComponentName")).set_value(
            ua.LocalizedText(self.component_name, "en-US"))
        await (await ua_identification.get_child(f"{UaTypes.ns_machine_set}:ResourceClass")).set_value(
            self.resource_class)

        if self.amount is not None:
            try:
                _monitoring_node = await self._ua_node.get_child(f"{ns_idx}:Monitoring")
                self._ua_amount = await add_property(ns_idx, _monitoring_node, "Amount", self.amount)
            except ua.uaerrors.BadNoMatch:
                self._logger.warning("Could not add amount property!")

    async def add_resource_object(self, parent: Node, ns_idx: int, **kwargs) -> Node:
        self._ua_node = await add_object(ns_idx, parent, ua.QualifiedName(self.component_name, ns_idx),
                                self._ua_resource_type, instantiate_optional=False)
        await self._fill_resource_obj(ns_idx, **kwargs)
        return self._ua_node

    async def write_amount(self, amount: int) -> None:
        self.amount = amount
        if self._ua_amount is not None:
            await self._ua_amount.write_value(amount)
        else:
            self._logger.warning("Could not write amount to resource, there is no corresponding OPC UA node!",
                                 amount=amount)

    async def read_amount(self) -> int:
        if self._ua_amount is not None:
            return await self._ua_amount.read_value()
        else:
            raise RuntimeError("Could not read amount, there is no corresponding OPC UA node!")

    @property
    def ua_node(self) -> Node:
        """ Returns the OPC UA node representing this resource. """
        return self._ua_node





