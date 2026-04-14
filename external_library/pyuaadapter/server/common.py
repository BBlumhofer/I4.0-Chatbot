from __future__ import annotations

import asyncio
import inspect
import pickle
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

import structlog
from asyncua import Node, Server, ua
from asyncua.ua import NodeId, QualifiedName, Variant, VariantType
from asyncua.ua.uaerrors import BadInvalidState, BadNodeIdExists
from transitions import MachineError

from pyuaadapter.common.enums import SkillStates

if TYPE_CHECKING:
    from pyuaadapter.server.base_asset import BaseAsset
    from pyuaadapter.server.base_skill import BaseSkill

_LOGGER = structlog.get_logger("sf.server.common")

with open(Path(__file__).parent.joinpath("nodesets/unit_to_eu_map.pickle"), "rb") as pickle_file:
    UNIT_TO_EU_MAP: dict[str, ua.EUInformation] = pickle.load(pickle_file)

def get_eu(unit: str | int) -> ua.EUInformation:
    if isinstance(unit, int):
        for eu in UNIT_TO_EU_MAP.values():
            if eu.UnitId == unit:
                return eu
    elif isinstance(unit, str):
        try:
            return UNIT_TO_EU_MAP[unit]
        except KeyError:
            pass

    raise RuntimeError(f"Given unit '{unit}' is neither a valid unit id nor display name!")

def get_node_id(location: Node, bname: QualifiedName | str, ns_idx: int | None = None) -> ua.NodeId:
    """ Returns a (new) Node ID in the standard hierarchical format based on given parameters.

    Arguments:
         location : OPC UA parent node in the hierarchy
         bname : Browse name of the new Node ID. If QualifiedName, the namespace index from there will be used.
         ns_idx : (optional) OPC UA namespace index, if None, the namespace index of the location node id will be used.
    """
    if isinstance(bname, QualifiedName):
        ns_idx = bname.NamespaceIndex  # will override the ns_idx parameter if also provided
        new_bname: str = bname.Name
    elif isinstance(bname, str):
        new_bname = bname
    else:
        raise TypeError(f"Given bname '{bname}' is neither a QualifiedName nor a string!")

    if ns_idx is None:
        ns_idx = location.nodeid.NamespaceIndex
    if isinstance(location.nodeid.Identifier, str):
        return ua.NodeId(ua.String(f"{location.nodeid.Identifier!s}.{new_bname}"), ua.Int16(ns_idx))
    else:
        # TODO get browse name instead?
        return ua.NodeId(ua.String(f"{new_bname}"), ua.Int16(ns_idx))

async def write_range(node: Node, _range: tuple[float, float]) -> None:
    range_node = await node.get_child("0:EURange")
    await range_node.write_value(ua.Range(Low=ua.Double(_range[0]), High=ua.Double(_range[1])))

async def write_unit(node: Node, unit: str | int, engineering_unit: str = "EngineeringUnits") -> None:
    engineering_units = get_eu(unit)

    eu_node = await node.get_child(f"0:{engineering_unit}")
    await eu_node.write_value(engineering_units)


async def write_optional(node: Node | None, value: Any, variant_type: ua.VariantType | None = None) -> None:
    # TODO use our write_value & what about writing None?
    if node is not None and value is not None:
        await node.write_value(value, varianttype=variant_type)


async def read_optional(node: Node | None) -> Variant | None:
    if node is None:
        return None
    return await node.read_value()

async def add_reference(parent: Node, child: Node,
                        _dict: dict[str, Node] | None = None,
                        reference: int = ua.ObjectIds.HasComponent) -> None:
    """ Helper function to add a new reference to given location and add it with browse name to dict. """

    await parent.add_reference(child, reference)

    if _dict is not None:
        _dict[(await child.read_browse_name()).Name] = child


async def add_object(ns_idx: int,
                     location: Node,
                     bname: QualifiedName | str,
                     object_tyoe: Node | NodeId | int,
                     instantiate_optional: bool = False) -> Node:
    """ Helper function to add a new variable to given location with a fixed NodeId format. """
    node_id = get_node_id(location, bname, ns_idx)
    return await location.add_object(nodeid=node_id, bname=bname, objecttype=object_tyoe,  # type: ignore
                                     instantiate_optional=instantiate_optional)

async def add_variable(ns_idx: int,
                       location: Node,
                       bname: QualifiedName | str,
                       val: Any,
                       varianttype: VariantType | None = None,
                       datatype: NodeId | int | None = None,
                       unit: str | int | None = None,
                       _range: tuple[float, float] | None = None,
                       variabletype: NodeId | None = None) -> Node:
    """ Helper function to add a new variable to given location with a fixed NodeId format. """

    node_id = get_node_id(location, bname, ns_idx)
    _LOGGER.debug("Adding variable...", node_id=node_id.to_string(), value=val, varianttype=varianttype,
                  datatype=datatype, unit=unit, range=_range, variabletype=variabletype)

    try:
        if variabletype is not None:
            node = await location.add_object(nodeid=node_id, bname=bname, objecttype=variabletype,
                                             instantiate_optional=True)
        elif unit is None:
            if _range is not None:  # notify programmer of their error instead of silently ignoring it
                raise ValueError("Ranges can only be used in combination with a unit!")
            return await location.add_variable(nodeid=node_id, bname=bname, val=val, varianttype=varianttype,
                                               datatype=datatype)
        elif unit is not None and _range is None:
            node = await location.add_object(nodeid=node_id, bname=bname, objecttype=ua.ObjectIds.AnalogUnitType,
                                             instantiate_optional=False)
        else:
            node = await location.add_object(nodeid=node_id, bname=bname, objecttype=ua.ObjectIds.AnalogUnitRangeType,
                                             instantiate_optional=False)
    except BadNodeIdExists:
        _LOGGER.warning("Variable node already exists, skipping instantiation!", node_id=node_id.to_string())
        node = Node(location.session, node_id)

    if val is not None:
        await node.write_value(val)

    if unit is not None:
        await write_unit(node, unit)

    if _range is not None:
        await write_range(node, _range)

    return node


async def add_property(ns_idx: int,
                       location: Node,
                       bname: QualifiedName | str,
                       val: Any,
                       varianttype: VariantType | None = None,
                       datatype: NodeId | int | None = None) -> Node:
    """ Helper function to add a new property to given location with a fixed NodeId format. """
    node_id = get_node_id(location, bname, ns_idx)
    _LOGGER.debug("Adding property...", node_id=node_id.to_string(), value=val, varianttype=varianttype,
        datatype=datatype)
    return await location.add_property(nodeid=node_id, bname=bname, val=val, varianttype=varianttype,
                                       datatype=datatype)

async def add_interface(server: Server,
                     ns_idx: int,
                     location: Node,
                     interface_type: Node | NodeId | int) -> Dict[str, Node]:
     """ Helper function to add a new property to given location with a fixed NodeId format. """
     from pyuaadapter.server import UaTypes

     asyncua_interface: Node = server.get_node(interface_type)
     _LOGGER.debug("Adding interface reference...", location=location.nodeid.to_string(),
                   target=asyncua_interface.nodeid.to_string())
     await location.add_reference(asyncua_interface, UaTypes.interface_ref)

     interface_nodes: Dict[str, Node] = {}

     for node in (await asyncua_interface.get_children()):
         browse_name = await node.read_browse_name()
         node_class = await node.read_node_class()

         # Handle Variables & Properties
         if node_class == ua.NodeClass.Variable:
             data_type = await node.read_data_type()

             value = await node.read_value()

             interface_nodes[browse_name.Name] =await add_variable(
                 ns_idx=ns_idx, location=location, bname=browse_name,
                 val=value, varianttype=None, datatype=data_type,
                 variabletype=node.nodeid)

     return interface_nodes


async def get_child_without_ns(parent: Node, display_name: str) -> Node:
    """ Returns the first child node with given display name while ignoring the namespace index. """
    for child in await parent.get_children():
        if (await child.read_display_name()).Text == display_name:
            return child
    raise RuntimeError(f"Could not find any child with display name '{display_name}' in "
                       f"node '{parent.nodeid.to_string()}'")


async def reset_skill_and_wait(skill: 'BaseSkill') -> None:
    """Reset the given skill and wait until it finished (successfully reached Ready state or Halted on failure).

    Note: This will only wait for the 'Halting' skill state, but not for other skill transition states!
    """
    # we need to wait for skills still in halting state to reach halted
    if skill.current_state == SkillStates.Halting:
        await skill.wait_for_state(SkillStates.Halted)

    if skill.current_state in (SkillStates.Halted, SkillStates.Suspended, SkillStates.Completed):
        await skill.reset()
        # resetting takes time, we need to wait until the skill is actually ready!
        await skill.wait_for_state(SkillStates.Ready)


async def halt_skill_and_wait(skill: 'BaseSkill') -> None:
    """Halt the given skill and wait until it finished and is in the Halted state."""
    try:
        await skill.halt()
        # halting takes time, we need to wait until the skill is actually halted!
        await skill.wait_for_state(SkillStates.Halted)
    except (BadInvalidState, MachineError):
        pass  # assume that skill is already halted
    except Exception as ex:
        raise RuntimeError(f"Could not halt skill '{skill.name}'!") from ex


async def reset_skills_parallel_and_wait(skills: Iterable["BaseSkill"],
                                         timeout: float | None = 60.0) -> None:
    """Reset all given skills in 'parallel'."""
    tasks = [asyncio.create_task(reset_skill_and_wait(skill)) for skill in skills]
    for coro in asyncio.as_completed(tasks, timeout=timeout):
        await coro  # may raise


async def halt_skills_parallel_and_wait(skills: Iterable['BaseSkill'],
                                        timeout: float | None = 60.0) -> None:
    """ Halt all given skills in 'parallel'. """
    tasks = [asyncio.create_task(halt_skill_and_wait(skill)) for skill in skills]
    for coro in asyncio.as_completed(tasks, timeout=timeout):
        await coro  # may raise


# TODO check if namespace as arg is needed
def create_missing_objects(bname: str, ua_type_attribute: str, ua_type_namespace_attribute: str):
    """
    Checks existence of browse name related to SF-internal nodeset
    -> adds object with ua type in defined namespace

    :param bname: the browse name of the related object
    :param ua_type_attribute: the object type of the object of interest -> should be an attribute of UaTypes
    :param ua_type_namespace_attribute: the namespace of the object to create --> should be an attribute of UaTypes
    """

    def decorator(func):
        async def wrapper(self: 'BaseAsset', *args, **kwargs):
            from pyuaadapter.server import UaTypes

            namespace = getattr(UaTypes, ua_type_namespace_attribute)

            for child_node in await self.ua_node.get_children():
                # Forced to override existing Identification cause machinery identification required
                # Remove therefore duplicated elements

                child_qualified_name = await child_node.read_browse_name()

                # make sure that only one identification exist
                if (bname == "Identification" and (child_qualified_name.Name == bname) and
                        child_qualified_name.NamespaceIndex != namespace):
                    self.logger.warning("Delete node since node bname already exists", bname=bname,
                                        node=child_node.nodeid.to_string())
                    await child_node.delete()
                elif (child_qualified_name.Name == bname) and (child_qualified_name.NamespaceIndex == namespace):
                    self.logger.debug("Init node since node bname and ns already exists", bname=bname,
                                      node=child_node.nodeid.to_string())
                    await func(self)
                    return

            # check if caller is same --> only create if called by super method
            caller_name = inspect.stack()[1].function

            if caller_name == func.__name__ or caller_name not in ["init", "_run"] or bname == "Identification":
                object_type = getattr(UaTypes, ua_type_attribute)
                self.logger.debug(
                    "Creating AddIn...", namespace=namespace, bname=bname, object_type=object_type.nodeid.to_string()
                )
                # TODO no add_in ref and why do i need to add namespace in bname???...
                obj = await add_object(self.ns_idx, self.ua_node, ua.QualifiedName(bname, namespace), object_type)
                if obj.nodeid.Identifier == 0:
                    self.logger.warning("Could not create AddIn since required node id exists", bname=bname)
                await func(self, *args, **kwargs)
            else:
                self.logger.debug("Skipped AddIn creation", bname=bname)

        return wrapper
    return decorator