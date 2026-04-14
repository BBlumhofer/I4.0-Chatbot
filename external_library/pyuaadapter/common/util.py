from __future__ import annotations

import asyncio
from typing import Any

from asyncua import Node, ua
from asyncua.ua import VariantType, NodeId

from pyuaadapter.common import NULL_NODE_ID


async def read_value(node: Node) -> Any:
    """ Reads the value of the given node and transforms the NULL_NODE_ID into None. """
    value = await node.read_value()
    if isinstance(value, NodeId) and value.is_null():
        return None
    else:
        return value

async def read_all_variables(location: Node) -> dict[str, Any]:
    """ Return all variables of the given node in dictionary form. """
    if location is None:
        raise ValueError("Given location is None!")
    ret = {}
    for node in await location.get_children():
        name, value = await asyncio.gather(node.read_browse_name(), node.read_value())
        ret[str(name.Name)] = value
    return ret

async def _write_value(node: Node, value: Any, variant_type: VariantType):
    # convert node id string to NodeId, this is not done automatically by asyncua
    if variant_type == ua.VariantType.NodeId and isinstance(value, str):
        if value == "":
            await node.write_value(NULL_NODE_ID)
        else:
            await node.write_value(ua.NodeId.from_string(value))
    elif variant_type == ua.VariantType.NodeId and value is None:
        await node.write_value(NULL_NODE_ID)  # we cannot write None here, it needs to be an (invalid) node id instead!
    else:
        await node.write_value(value, variant_type)

async def write_value(node: Node, value: Any, variant_type: VariantType | None = None) -> None:
    """ Writes the given value to the given node. Will try to use existing variant type of the node. """
    # Note: asyncua is very strict, e.g. float is not automatically cast to double and trying to write that will fail!
    if isinstance(value, ua.Variant):
        await _write_value(node, value.Value, value.VariantType)
    if variant_type is not None:
        await _write_value(node, value, variant_type)
    else:
        # we need to figure out the correct variant type to use ourselves
        data_value_value = (await node.read_data_value()).Value
        if data_value_value is None:
            await node.write_value(value)  # try without variant type, might fail
        else:
            await _write_value(node, value, data_value_value.VariantType)


async def get_all_variables_with_browse_name(node: Node) -> dict[str, Node]:
    """Gather all child variables for given node and store them in a dict."""
    node_dict = {}
    for child in await node.get_variables():
        node_dict[str((await child.read_browse_name()).Name)] = child
    return node_dict
