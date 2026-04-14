from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

import structlog
from asyncua import Node, ua
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua import (
    DataValue,
    EnumDefinition,
    LocalizedText,
    NodeId,
    NodeIdType,
    ObjectIdNames,
    UaStatusCodeError,
    Variant,
)
from asyncua.ua.uaerrors import BadOutOfRange, BadUserAccessDenied

from pyuaadapter.common.util import write_value

if TYPE_CHECKING:
    from pyuaadapter.client.remote_server import RemoteServer

_LOGGER = structlog.getLogger("sf.client.RemoteVariable")

def ua_value_to_simple(value: Any) -> None | bool | bytes | int | float | str:
    """ Converts given value (from OPC UA typically) to a simple JavaScript-friendly data type to make
    handling easier than complex types. """
    if value is None:
        return None
    elif isinstance(value, (bool, bytes, int, float, str, )):
        return value
    elif isinstance(value, LocalizedText):
        return value.Text
    elif isinstance(value, NodeId):
        return value.to_string() if not value.is_null() else None
    else:
        _LOGGER.warning("Unsupported value type, fallback to string", type=type(value))
        return str(value)

def ua_value_to_dto(value: Any) -> Any | dict[str, Any]:
    if dataclasses.is_dataclass(value):  # handle generic dataclass types used by asyncua
        return dataclasses.asdict(value)  # type: ignore
    else:
        return ua_value_to_simple(value)


@dataclasses.dataclass
class TimestampedValue:
    value: Any
    timestamp: datetime | None


class RemoteVariable:
    """ Simple data container for remote variables. """

    def __init__(self, name: str,
                 ua_node_id: NodeId | Node,
                 remote_server: "RemoteServer",
                 *,
                 valid_values: dict[int | str, str | None],
                 ua_data_type: str,
                 ua_value_rank: int,
                 is_writable: bool = False):
        self._name = name
        self._ua_node_id = ua_node_id.nodeid if isinstance(ua_node_id, Node) else ua_node_id
        """ Contains the OPC UA node ID which is represented by this instance. """
        self._remote_server = remote_server
        self._valid_values = valid_values  # used for enums, because they are just ints internally
        self._is_writable = is_writable
        self._value: Variant = Variant()
        self._timestamp: datetime | None = None
        self._ua_data_type: str = ua_data_type
        self._ua_value_rank: int = ua_value_rank
        self.unit: ua.EUInformation | None = None
        """ Unit of this variable. """
        self.range: ua.Range | None = None
        """ Range of this variable. """
        self.children: dict[str, RemoteVariable] = {}

        self._logger = _LOGGER.bind(name=name)

    @property
    def name(self) -> str:
        """ The name of the variable. """
        return self._name

    @property
    def ua_node(self) -> Node:
        """ Return a usable node from the current client. Note: Do **NOT** store it, it will become invalid
        after any reconnection!"""
        return self._remote_server.ua_client.get_node(self._ua_node_id)

    @property
    def is_writable(self) -> bool:
        """ Flag determining whether this variable is writable or read-only. Note however, that this is separate
        from the current access rights of the user. """
        return self._is_writable

    def _process_value(self, value: Variant | None) -> Any:
        if value is None or isinstance(value.Value, NodeId) and value.Value.is_null():
            return None
        elif len(self.valid_values) > 0 and isinstance(value.Value, (str, int)):
            try:
                return self.valid_values[value.Value]
            except KeyError:
                self._logger.warning("Tried to match non-existent definition", value=value.Value)
                return f"INVALID ENUM VALUE: {value.Value}"
        else:
            return value.Value

    @property
    def value(self) -> Any:
        """ Value of this variable. """
        return self._process_value(self._value)

    @property
    def raw_value(self) -> Variant:
        """Return the raw value as an OPC UA Variant."""
        return self._value

    @property
    def is_value_node_id(self) -> bool:
        """ Returns True if the value of this RemoteVariable is a not null Node ID. """
        return isinstance(self._value.Value, NodeId) and not self._value.Value.is_null()

    async def read_value(self, *, update_cache: bool = False) -> Any:
        """ Reads the actual value from the remote server, not the cached local one."""
        data_value = await self.ua_node.read_data_value()
        if update_cache:
            self.update_from_data_value(data_value)
        return self._process_value(data_value.Value)

    async def read_raw_value(self) -> Variant:
        """ Reads the actual raw value from the remote server. """
        data_value = await self.ua_node.read_data_value()
        return data_value.Value

    async def read_resolved_value(self) -> Any:
        """Reads the resolved value of this variable. Falls back to normal value if there is nothing to resolve.

        For example, if this variable value is a node id, resolve it to the display name of the target node.
        If the display name is not readable, fall back to the browse name. If that is also not readable, return the
        last part of the string identifier of the node.
        """
        if self.is_value_node_id:
            target_node = self._remote_server.ua_client.get_node(self._value.Value)
            try:
                display_name = await target_node.read_display_name()
                return display_name.Text
            except ua.UaError:
                self._logger.warning("Could not read the display name!", node_id=target_node.nodeid.to_string())
                try:
                    browse_name = await target_node.read_browse_name()
                    return browse_name.Name
                except ua.UaError:
                    self._logger.warning("Could not read the browse name!", node_id=target_node.nodeid.to_string())
                    if target_node.nodeid.NodeIdType == NodeIdType.String:
                        identifier = cast(str, target_node.nodeid.Identifier)
                        return identifier.split(".")[-1]

        return await self.read_value()  # fallback


    @property
    def valid_values(self) -> dict[int | str, str | None]:
        """ Valid values of this remote variable in dictionary form. Used for e.g. selection dropdown in front-end. """
        return self._valid_values

    @property
    def timestamp(self) -> datetime | None:
        """ Timestamp of last value change"""
        return self._timestamp

    @property
    def ua_data_type(self) -> str:
        """ Internal OPC UA data type. """
        return self._ua_data_type

    @property
    def ua_value_rank(self) -> int:
        """ Internal OPC UA value rank (-1 for Scalar, 0 for 1 or more, >=1 exact dimension). """
        return self._ua_value_rank

    def dto(self) -> dict[str, Any]:
        """ Returns a json serializable datatransfer object meant for initial setup, not for status updates! """
        return {
            "name": self.name,
            "node_id": self._ua_node_id.to_string(),
            "value": ua_value_to_dto(self.value),
            "valid_values": self.valid_values,
            "ua_data_type": self.ua_data_type,
            "ua_value_rank": self.ua_value_rank,
            "timestamp": self.timestamp.isoformat() if self.timestamp is not None else None,
            "is_writable": self.is_writable,
            "unit": self.unit.DisplayName.Text if self.unit is not None else None,
            "range": {
                "low": self.range.Low,
                "high": self.range.High
            } if self.range is not None else None,
            "children": [child.dto() for child in self.children.values()]
        }

    async def read_history(self,
                           start_time: datetime | None = None,
                           end_time: datetime | None = None,
                           num_values: int = 0,
                           return_bounds: bool = True) -> list[TimestampedValue]:
        """ Provide requested (default=all) historic values of this variable including their timestamps of the server.

        :param start_time: Start timestamp in UTC for the first data point of the period if specified.
        :param end_time: End timestamp in UTC for the last data point of the period if specified.
        :param num_values: Maximum number of values returned. 0 = No maximum.
        :param return_bounds: Include the bounding values?
        """
        return [TimestampedValue(value=entry.Value.Value, timestamp=entry.ServerTimestamp)
                for entry in await self.ua_node.read_raw_history(
                    starttime=start_time, endtime=end_time, numvalues=num_values, return_bounds=return_bounds)
                if entry.Value is not None]

    def update_from_data_value(self, value: DataValue | DataChangeNotif | None) -> None:
        """Update both value and timestamp of this RemoteVariable from given data value or subscription callback data."""
        if value is None:
            return
        elif isinstance(value, DataChangeNotif):
            value = value.monitored_item.Value

        self._value = value.Value
        self._timestamp = value.ServerTimestamp

    async def write_value(self, value: Any) -> None:
        """ Tries to directly write the given value to the server. Might fail if variable is not writable or
        user has currently no rights to write the variable. """
        if not self.is_writable:
            raise RuntimeError(f"RemoteVariable '{self.name}' is not writable!")

        try:
            await write_value(self.ua_node, value)
        except (BadUserAccessDenied, BadOutOfRange) as ex:
            raise ex
        except UaStatusCodeError:
            try:
                # TODO why is valid values not a list (at least for enums)?
                index = list(self.valid_values.values()).index(value)
                # enums always start with 0 -> key should be the index...
                # but we are not only dealing with enums
                key = list(self.valid_values.keys())[index]
                await write_value(self.ua_node, key)
            except Exception as err:
                raise RuntimeError(f"{value} is not a valid value (valid are: {self.valid_values}!") from err

    def __str__(self):
        ret_string = str(self.value)
        if self.unit is not None:
            ret_string += " " + (self.unit.DisplayName.Text or "<None>")
        if self.range is not None:
            ret_string += f" (Low: {self.range.Low}; High: {self.range.High})"

        return ret_string


async def _add_variable_node(node: Node,
                             node_mapping: dict[NodeId, RemoteVariable],
                             is_writable: bool,
                             remote_server: "RemoteServer") -> RemoteVariable:
    # Read all attributes we need at the same time
    bname_data_value, data_type_data_value, value_data_value, value_rank_value = await node.read_attributes(
        [ua.AttributeIds.BrowseName, ua.AttributeIds.DataType, ua.AttributeIds.Value, ua.AttributeIds.ValueRank]
    )
    node_browse_name: str = bname_data_value.Value.Value.Name  # type: ignore
    node_type_node_id: NodeId | None = data_type_data_value.Value.Value  # type: ignore

    ua_data_type = "UNKNOWN"
    if node_type_node_id is not None and node_type_node_id.NamespaceIndex == 0:
        try:
            ua_data_type = ObjectIdNames[node_type_node_id.Identifier]
        except KeyError:
            _LOGGER.warning("Could not determine UA data type", node_type_node_id=node_type_node_id)

    # Get valid values if data type is an enum
    valid_values: dict[int | str, str | None] = {}
    if node_type_node_id is not None:
        if isinstance(value_data_value.Value.Value, NodeId):  # type: ignore
            valid_values[""] = "<None>"
            for ref in await node.get_references(ua.FourByteNodeId(ua.ObjectIds.Utilizes)):  # TODO what about v3?
                valid_values[ref.NodeId.to_string()] = ref.DisplayName.Text
        elif node_type_node_id.NamespaceIndex != 0:  # not OPC UA namespace -> custom type  # TODO what about standard enums?
            (data_type_definition_data_value,) = await remote_server.ua_client.uaclient.read_attributes(
                [node_type_node_id], ua.AttributeIds.DataTypeDefinition
            )
            dtype_definition = data_type_definition_data_value.Value.Value
            if isinstance(dtype_definition, EnumDefinition):
                ua_data_type = "Enumeration"  # close enough
                for field in dtype_definition.Fields:
                    valid_values[field.Value] = field.Name
    else:
        _LOGGER.warning("Node has no valid data type!", bname=node_browse_name)


    remote_variable = RemoteVariable(name=node_browse_name,
                                     ua_node_id=node.nodeid,
                                     remote_server=remote_server,
                                     valid_values=valid_values,
                                     ua_data_type=ua_data_type,
                                     ua_value_rank=value_rank_value.Value.Value,  # type: ignore
                                     is_writable=is_writable)

    # handle properties
    for property_node in await node.get_properties():
        property_bname_data_value, property_value_data_value = await property_node.read_attributes([
            ua.AttributeIds.BrowseName, ua.AttributeIds.Value])
        property_name: str = property_bname_data_value.Value.Value.Name  # type: ignore
        property_value = property_value_data_value.Value.Value  # type: ignore

        if property_name == "EngineeringUnits":
            remote_variable.unit = property_value
        elif property_name == "EURange":
            remote_variable.range = property_value
        else:
            _LOGGER.warning(
                "Found unsupported property, ignoring!",
                property=property_node.nodeid.to_string(),
                node_bname=node_browse_name,
            )

    remote_variable.update_from_data_value(value_data_value)

    # handle further child variables recursively
    for child_node in await node.get_variables():
        child_remote_variable = await _add_variable_node(child_node, node_mapping, is_writable, remote_server)

        # TODO remove when no longer needed, handling modelling errors...
        if child_remote_variable.name == "EngineeringUnits":  # should be a property if correctly modeled
            remote_variable.unit = await child_node.read_value()
            _LOGGER.warning("Node has EngineeringUnits that are not properly modeled!", bname=node_browse_name)
            continue

        node_mapping[child_node.nodeid] = child_remote_variable  # add child to mapping
        remote_variable.children[child_remote_variable.name] = child_remote_variable

    return remote_variable



async def add_variable_nodes(
    m_node: Node,
    node_mapping: dict[NodeId, RemoteVariable],
    name_mapping: dict[str, RemoteVariable],
    is_writable: bool,
    remote_server: "RemoteServer",
) -> None:
    """Recursively add all variables to given mappings."""

    # TODO change when node-set is consistent everywhere, currently too restrictive
    # for child in await m_node.get_variables()
    for child in await m_node.get_children():
        if child.nodeid in remote_server.node_map:
            _LOGGER.warning("Node was already parsed, ignored!", node=m_node.nodeid.to_string())
            continue

        remote_variable = await _add_variable_node(child, node_mapping, is_writable, remote_server)

        node_mapping[child.nodeid] = remote_variable
        name_mapping[remote_variable.name] = remote_variable
        remote_server.node_map[child.nodeid] = remote_variable
