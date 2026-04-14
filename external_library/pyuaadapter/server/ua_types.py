import time
from pathlib import Path
from typing import Dict

import structlog
from asyncua import Node, Server, ua

from pyuaadapter.server import BaseConfig
from pyuaadapter.server.nodesets import ua_files


class UaTypes:
    """ Class for creating and storing all OPC-UA types. """
    asset_type: Node
    component_type: Node
    port_type: Node
    storage_slot_type: Node
    storage_type: Node
    axis_type: Node
    gripper_type: Node
    safety_type: Node
    shuttle_type: Node
    module_type: Node
    users_type: Node
    user_type: Node

    messages_type: Node
    notification_type: Node
    monitoring_type: Node

    machine_identification_type: Node
    component_identification_type: Node
    components_type: Node
    machinery_item_state_machine_type: Node
    machinery_operation_mode_state_machine_type: Node

    cartesian_frame_angle_orientation_type: Node
    spatial_object: Node
    spatial_object_list: Node

    functional_group_type: Node
    skill_state_machine_type: Node
    skill_element_type: Node
    base_skill_type: Node
    skill_set_type: Node
    continuous_skill_type: Node
    finite_skill_type: Node

    finite_state_machine_type: Node
    state_type: Node
    initial_state_type: Node
    transition_type: Node
    ref_from_state: Node
    ref_to_state: Node
    state_machine_type: Node
    state_variable_type: Node

    depends_ref: Node
    utilize_ref: Node
    interface_ref: Node

    base_resource_type: Node
    resources_type: Node

    base_event: int
    alert_event: Node

    method_set_type: Node
    method_type: Node

    slot_state_enum: Node

    ns_uri_idx_dict: Dict[str, int] = {} # TODO save at central location and use, currently not really used
    ns_di: int
    ns_rsl: int
    ns_machinery: int
    ns_skill_set: int
    ns_machine_set: int

    logger = structlog.getLogger("sf.server.Server")

    # TODO instantiate_util.py Line 117:
    # only HasComponent seems to be instantiated, mutiple references exists for types that have subtype reference of HasComponent
    # QuickFix in AsyncUa
    """
     duplicated_references = [x for x in descs if ((c_rdesc.BrowseName.Name == x.BrowseName.Name) and (c_rdesc.ReferenceTypeId != x.ReferenceTypeId))] # check for multiple nodes

        if len(duplicated_references) > 0 and c_rdesc.ReferenceTypeId == ua.NodeId(ua.ObjectIds.HasComponent): #skip if there is a mutiple node with has component
            continue
    """

    @classmethod
    async def import_xml(cls, server: Server, file: str) -> int:
        """
        imports xml from known string

        :param file: str located inside ua_files.py
        :param file: files to access nodesets inside 'nodesets' folder
        """
        time_start = time.monotonic()
        path = Path(__file__).parent.joinpath(file)
        nodes = await server.import_xml(path)
        idx = nodes[0].NamespaceIndex
        uri: str = (await server.get_namespace_array())[idx]
        cls.ns_uri_idx_dict[uri] = idx
        cls.logger.info("Imported nodes from XML node set!", file_name=path.name, uri=uri, ns_idx=idx,
                        no_of_nodes=len(nodes), elapsed=time.monotonic()-time_start)
        return idx

    @classmethod
    async def init_class(cls, server: Server, config: BaseConfig) -> int:
        """
        Initializes the class members. Call once before using any OPC-UA type.

        :param server: OPC-UA server instance
        :param config: BaseConfig from the server
        """

        # for tests clear ns_uri_idx_dict
        cls.ns_uri_idx_dict = {}

        cls.ns_di = await cls.import_xml(server, ua_files.NS_DI_XML_FILE)
        cls.ns_rsl = await cls.import_xml(server, ua_files.NS_RSL_XML_FILE)
        cls.ns_machinery = await cls.import_xml(server, ua_files.NS_MACHINERY_XML_FILE)
        cls.ns_skill_set = await cls.import_xml(server, ua_files.NS_SKILL_SET_XML_FILE)
        cls.ns_machine_set = await cls.import_xml(server, ua_files.NS_MACHINE_SET_XML_FILE)
        # check if namespace exists otherwise creates a new for customization
        ns_idx = -1

        for _idx, _namespace in enumerate(await server.get_namespace_array()):
            if _namespace == config.NAMESPACE_URI:
                ns_idx = _idx
                break

        if ns_idx == -1:
            ns_idx = await server.register_namespace(config.NAMESPACE_URI)
            cls.ns_uri_idx_dict[config.NAMESPACE_URI] = ns_idx

        ##########################################################################
        # assets
        
        cls.asset_type = server.get_node(f"ns={cls.ns_machine_set};i=1002")
        cls.component_type = server.get_node(f"ns={cls.ns_machine_set};i=1008")
        cls.storage_slot_type = server.get_node(f"ns={cls.ns_machine_set};i=1017")
        cls.storage_type = server.get_node(f"ns={cls.ns_machine_set};i=1018")
        cls.gripper_type = server.get_node(f"ns={cls.ns_machine_set};i=1020")
        cls.safety_type = server.get_node(f"ns={cls.ns_machine_set};i=1021")
        cls.shuttle_type = server.get_node(f"ns={cls.ns_machine_set};i=1019")

        cls.port_type = server.get_node(f"ns={cls.ns_machine_set};i=1010")
        cls.module_type = server.get_node(f"ns={cls.ns_machine_set};i=1009")

        cls.users_type = server.get_node(f"ns={cls.ns_machine_set};i=1024")
        cls.user_type = server.get_node(f"ns={cls.ns_machine_set};i=1023")
        
        ##########################################################################
        # notification and monitoring types
        cls.notification_type = server.get_node(f"ns={cls.ns_machine_set};i=1003")
        cls.messages_type = server.get_node(f"ns={cls.ns_machine_set};i=1000")
        cls.monitoring_type = server.get_node(f"ns={cls.ns_machine_set};i=1006")

        ##########################################################################
        # skill types
        cls.base_skill_type = server.get_node(f"ns={cls.ns_skill_set};i=1001")
        cls.skill_set_type = server.get_node(f"ns={cls.ns_skill_set};i=1002")
        cls.continuous_skill_type = server.get_node(f"ns={cls.ns_machine_set};i=1016")
        cls.finite_skill_type = server.get_node(f"ns={cls.ns_machine_set};i=1015")

        cls.functional_group_type = server.get_node(f"ns={cls.ns_di};i=1005")
        cls.skill_element_type = server.get_node(f"ns={cls.ns_machine_set};i=1013")
        cls.skill_state_machine_type = server.get_node(f"ns={cls.ns_machine_set};i=1014")

        cls.method_set_type = server.get_node(f"ns={cls.ns_skill_set};i=1005")
        cls.method_type = server.get_node(f"ns={cls.ns_skill_set};i=1004")
        
        cls.depends_ref = await server.nodes.reference_types.get_child(
            ["0:References", "0:HierarchicalReferences", f"0:Requires"])
        cls.utilize_ref = await server.nodes.reference_types.get_child(
            ["0:References", "0:NonHierarchicalReferences", f"0:Utilizes"])
        cls.interface_ref = await server.nodes.reference_types.get_child(
            ["0:References", "0:NonHierarchicalReferences", f"0:HasInterface"])

        ##########################################################################
        # FSM types
        cls.finite_state_machine_type = await server.get_root_node().get_child(
            ["0:Types", "0:ObjectTypes", "0:BaseObjectType", "0:StateMachineType", "FiniteStateMachineType"])
        cls.state_type = await server.get_root_node().get_child(
            ["0:Types", "0:ObjectTypes", "0:BaseObjectType", "0:StateType"])
        cls.initial_state_type = await server.get_root_node().get_child(
            ["0:Types", "0:ObjectTypes", "0:BaseObjectType", "0:StateType", "0:InitialStateType"])

        # necessary types for transitions
        cls.transition_type = await server.get_root_node().get_child(
            ["0:Types", "0:ObjectTypes", "0:BaseObjectType", "0:TransitionType"])
        cls.ref_from_state = await server.nodes.reference_types.get_child(
            ["0:References", "0:NonHierarchicalReferences", "0:FromState"])
        cls.ref_to_state = await server.nodes.reference_types.get_child(
            ["0:References", "0:NonHierarchicalReferences", "0:ToState"])

        cls.state_variable_type = await server.get_root_node().get_child(
            ["0:Types", "0:VariableTypes", "0:BaseVariableType", "0:BaseDataVariableType", "0:StateVariableType"])
        cls.state_machine_type = await server.get_root_node().get_child(
            ["0:Types", "0:ObjectTypes", "0:BaseObjectType", "0:StateMachineType"])

        ##########################################################################
        # RSL types
        cls.cartesian_frame_angle_orientation_type = server.get_node(f"ns={cls.ns_rsl};i=2004")
        cls.spatial_object = server.get_node(f"ns={cls.ns_rsl};i=1002")
        cls.spatial_object_list = server.get_node(f"ns={cls.ns_rsl};i=1003")

        ##########################################################################
        # machinery types
        cls.machine_identification_type = server.get_node(f"ns={cls.ns_machinery};i=1012")
        cls.component_identification_type = server.get_node(f"ns={cls.ns_machinery};i=1005")
        cls.components_type = server.get_node(f"ns={cls.ns_machinery};i=1006")
        cls.machinery_item_state_machine_type = server.get_node(f"ns={cls.ns_machinery};i=1002")
        cls.machinery_operation_mode_state_machine_type = server.get_node(f"ns={cls.ns_machinery};i=1008")

        ##########################################################################
        # Custom resource types
        cls.base_resource_type = server.get_node(f"ns={cls.ns_machine_set};i=1011")
        cls.resources_type = server.get_node(f"ns={cls.ns_machine_set};i=1005")

        ##########################################################################
        # event types
        cls.base_event = ua.ObjectIds.BaseEventType
        cls.alert_event = server.get_node(f"ns={cls.ns_machine_set};i=1001")

        ##########################################################################
        # enum types
        cls.slot_state_enum = server.get_node(f"ns={cls.ns_machine_set};i=3001")

        return ns_idx
