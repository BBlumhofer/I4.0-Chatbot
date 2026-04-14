from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

import structlog
from asyncua import Node, Server
from asyncua.ua import Int32, NodeId, VariantType
from asyncua.ua.uaerrors import BadNoMatch

from pyuaadapter.common.util import get_all_variables_with_browse_name, read_value, write_value
from pyuaadapter.server.access_control import AccessControl
from pyuaadapter.server.base_requirements import BaseRequirements
from pyuaadapter.server.common import add_variable, get_node_id

if TYPE_CHECKING:
    from pyuaadapter.server.base_machinery_item import BaseMachineryItem


class BaseCallable(BaseRequirements, ABC):
    """Abstract base class for all callables, i.e. skills and methods."""

    ua_final_result_data: Node
    """OPC UA node of final result folder."""
    ua_parameter_set: Node
    """OPC UA node of parameter set folder."""
    ua_monitoring: Node
    """OPC UA node of monitoring folder."""

    logger: structlog.BoundLogger

    # class attributes
    server: ClassVar[Server]
    """The OPC UA server instance."""
    access_control: ClassVar[AccessControl]
    """The access control instance."""
    ns_idx: ClassVar[int]

    def __init__(self, name: str, machinery_item: "BaseMachineryItem", _type: Node, *, minimum_access_level: int = 1):
        """ Create a new callable instance.

        :param name: name of the callable
        :param machinery_item: machinery_item instance
        :param _type: OPC UA node determining the OPC UA object type used for instantiation.
        :param minimum_access_level: Minimum required access level to start the callable (see User for more info)
        """
        super().__init__()
        self.name = name
        self._machinery_item = machinery_item
        self._minimum_access_level = minimum_access_level
        self._type = _type

        self.config = machinery_item.config
        self.ua_parameter_set_nodes: dict[str, Node] = {}
        self.ua_monitoring_nodes: dict[str, Node] = {}
        self.ua_final_result_data_nodes: dict[str, Node] = {}
        self._nodes_to_historize: list[Node] = []

    @property
    def full_name(self) -> str:
        """Return the full name including the full names of all parents, separated by '/'."""
        return f"{self._machinery_item.full_name}/{self.name}"

    @classmethod
    def init_class(cls, server: Server, ns_idx: int, access_control: AccessControl) -> None:
        """
        Initializes the class members. Call once before instantiating any skill.

        :param server: OPC-UA server instance
        :param ns_idx: OPC-UA namespace index
        :param access_control: AccessControl instance
        """
        cls.server = server
        cls.ns_idx = ns_idx
        cls.access_control = access_control

    @abstractmethod
    async def _get_sub_node(self) -> Node:
        raise NotImplementedError

    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        """Initialize the callable instance asynchronously.

        :param existing_node: pre-existing OPC UA node prior to init().
                Will be used instead of creating a new node in the given location.
        :param location: parent OPC-UA node, ideally a folder type
        """
        from pyuaadapter.server import UaTypes  # prevent circular import

        if existing_node is None:
            if location is None:
                raise RuntimeError("No location given!")

            node_id = get_node_id(location, self.name)
            self._ua_node = await location.add_object(node_id, self.name, self._type.nodeid, True)
        else:
            self._ua_node = existing_node

        await (await self._ua_node.get_child(f"{UaTypes.ns_skill_set}:Name")).write_value(self.name)

        ua_sub_node = await self._get_sub_node()

        ua_min_access_level_node = await ua_sub_node.get_child(f"{UaTypes.ns_skill_set}:MinAccessLevel")
        await ua_min_access_level_node.write_value(Int32(self._minimum_access_level))

        self.ua_parameter_set = await ua_sub_node.get_child(f"{UaTypes.ns_skill_set}:ParameterSet")
        self.ua_parameter_set_nodes.update(await get_all_variables_with_browse_name(self.ua_parameter_set))

        self.ua_final_result_data = await ua_sub_node.get_child(f"{UaTypes.ns_skill_set}:FinalResultData")
        self.ua_final_result_data_nodes.update(await get_all_variables_with_browse_name(self.ua_final_result_data))

        self.ua_monitoring = await ua_sub_node.get_child(f"{UaTypes.ns_skill_set}:Monitoring")
        self.ua_monitoring_nodes.update(await get_all_variables_with_browse_name(self.ua_monitoring))

        with contextlib.suppress(BadNoMatch): # TODO @SiJu: Should methods also have requirements?
            self.ua_requirements_folder = await self._ua_node.get_child(f"{UaTypes.ns_skill_set}:Requirements")


    async def enable_historizing(self, server: Server, count: int = 1000) -> None:
        """ Enables OPC-UA historizing for all previously added nodes (parameter, monitoring, etc.) with enabled
        historizing.

        :param server: OPC-UA server reference
        :param count: how many changes should be stored in history
        """
        await server.historize_node_data_change(self._nodes_to_historize, count=count)

    @property
    def ua_node(self) -> Node:
        """ Returns the internal OPC UA node of the callable. Make sure you know what you are doing! """
        return self._ua_node

    async def add_parameter_variable(self, name: str,
                                     val: Any,
                                     *,
                                     varianttype: VariantType | None = None,
                                     datatype: NodeId | int | None = None,
                                     historize: bool = False,
                                     unit: str | int | None = None,
                                     _range: tuple[float, float] | None = None) -> Node:
        """ Creates a new OPC UA node in the parameter set folder with the given parameters and sets it writable. """
        node = await add_variable(self.ns_idx, self.ua_parameter_set, name, val, varianttype, datatype, unit, _range)
        await node.set_writable()

        if historize:
            self._nodes_to_historize.append(node)

        self.ua_parameter_set_nodes[name] = node

        return node

    async def add_result_variable(self, name: str,
                                  val: Any,
                                  *,
                                  varianttype: VariantType | None = None,
                                  datatype: NodeId | int | None = None,
                                  historize: bool = False,
                                  unit: str | int | None = None,
                                  _range: tuple[float, float] | None = None) -> Node:
        """ Creates a new OPC UA node in the final result data folder with the given parameters. """
        node = await add_variable(self.ns_idx, self.ua_final_result_data, name, val, varianttype, datatype, unit,
                                  _range)
        if historize:
            self._nodes_to_historize.append(node)

        self.ua_final_result_data_nodes[name] = node

        return node

    async def add_monitoring_variable(self, name: str,
                                      val: Any,
                                      *,
                                      varianttype: VariantType | None = None,
                                      datatype: NodeId | int | None = None,
                                      historize: bool = False,
                                      unit: str | int | None = None,
                                      _range: tuple[float, float] | None = None) -> Node:
        """ Creates a new OPC UA node in the monitoring folder with the given parameters. """
        node = await add_variable(self.ns_idx, self.ua_monitoring, name, val, varianttype, datatype, unit, _range)

        if historize:
            self._nodes_to_historize.append(node)

        self.ua_monitoring_nodes[name] = node

        return node

    async def _log_info(self, text: str, severity: int = 0):
        await self._machinery_item._log_info(severity=severity, text=text)

    async def _log_warning(self, text: str, severity: int = 555):
        await self._machinery_item._log_warning(severity=severity, text=text)

    async def _log_error(self, text: str, severity: int = 999, code: str = ""):
        await self._machinery_item._log_error(severity=severity, text=text, code=code)

    async def write_parameter(self, name: str, value: Any) -> None:
        """Write the given value to the parameter with the given name."""
        try:
            parameter_node = self.ua_parameter_set_nodes[name]
            await write_value(parameter_node, value)
        except KeyError:
            self.logger.error("Could not find parameter!", variable=name)
            raise
        except:
            self.logger.error("Could not write parameter!", variable=name)
            raise

    async def write_parameters(self, parameters: dict[str, Any]) -> None:
        """
        Sets the parameters of the skill according to given dictionary.

        Keys of the dictionary are matched to the browse name of the OPC UA node.
        Values of the dictionary are written to the matched OPC UA node.
        """
        for name, value in parameters.items():
            await self.write_parameter(name, value)

    async def read_parameter(self, name: str) -> Any:
        """Read the value of the parameter node with the given name."""
        try:
            result_node = self.ua_parameter_set_nodes[name]
            return await read_value(result_node)
        except KeyError:
            self.logger.error("Could not find parameter!", variable=name)
            raise

    async def read_parameters(self) -> dict[str, Any]:
        """
        Reads all parameters from the skill and returns them as a dictionary.

        Keys are the display name of OPC UA nodes, values the corresponding values.
        """
        ret = {}
        for name, node in self.ua_parameter_set_nodes.items():
            ret[name] = await read_value(node)
        return ret

    async def read_result(self, name: str) -> Any:
        """Read the value of the final result data node with the given name."""
        try:
            result_node = self.ua_final_result_data_nodes[name]
            return await read_value(result_node)
        except KeyError:
            self.logger.error("Could not find final result!", variable=name)
            raise

    async def read_results(self) -> dict[str, Any]:
        """
        Reads all results from the skill and returns them as a dictionary.

        Keys are the display name of OPC UA nodes, values the corresponding values.
        """
        ret = {}
        for name, node in self.ua_final_result_data_nodes.items():
            ret[name] = await read_value(node)
        return ret

    async def read_monitoring(self) -> dict[str, Any]:
        """
        Reads all monitoring values from the skill and returns them as a dictionary.

        Keys are the display name of OPC UA nodes, values the corresponding values.
        """
        ret = {}
        for name, node in self.ua_monitoring_nodes.items():
            ret[name] = await read_value(node)
        return ret

    @property
    def machinery_item(self) -> 'BaseMachineryItem':
        return self._machinery_item

    async def _delete_empty_folders(self):
        if len(await self.ua_requirements_folder.get_children()) == 0:
            await self.ua_requirements_folder.delete()
        await self._machinery_item._delete_empty_folders(await self._get_sub_node())