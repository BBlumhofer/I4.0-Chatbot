from __future__ import annotations

from typing import TYPE_CHECKING

from asyncua import Node, ua
from asyncua.ua import NodeId
from typing_extensions import override

from pyuaadapter.client.base_remote_skill import SkillTypes, BaseRemoteSkill
from pyuaadapter.common.namespace_uri import NS_SFM_V3_URI

if TYPE_CHECKING:
    from .remote_server import RemoteServer


class RemoteSkill(BaseRemoteSkill):
    """Represents a remote skill for skill node-set version 3."""

    def __init__(self, name: str, base_node: Node, remote_server: "RemoteServer"):
        super().__init__(name, base_node, remote_server)

        self._ns_idx_methods = self._remote_server.namespace_map[NS_SFM_V3_URI]
        self._ns_idx_other = self._remote_server.namespace_map[NS_SFM_V3_URI]

    @override
    async def _setup_type_and_dependencies(self):
        ua_ref_depends_on = await (
            self._remote_server.ua_client.get_node(ua.ObjectIds.NonHierarchicalReferences).get_child(
                [f"{self._ns_idx_other}:DependsOn"]))  # Immutable node id
        ua_skill_parent = await self._ua_base_node.get_parent()
        for reference in await ua_skill_parent.get_references():  # type: ignore
            # reference: ReferenceDescription = reference
            if reference.BrowseName.Name == 'FiniteSkillType':
                self._type = SkillTypes.Finite
            elif reference.BrowseName.Name == 'ContinuousSkillType':
                self._type = SkillTypes.Continuous
            elif reference.ReferenceTypeId == ua_ref_depends_on.nodeid:
                if reference.IsForward:
                    self._depends_on[reference.NodeId] = reference.BrowseName.Name
                else:
                    self._dependency_of[reference.NodeId] = reference.BrowseName.Name

        if self._type == SkillTypes.Unknown:
            self.logger.warning(f"Could not determine skill type of {self.name}!")

    @override
    async def _get_dependency_reference_node_id(self) -> NodeId:
        non_hierarchical_references = self._remote_server.ua_client.get_node(ua.ObjectIds.NonHierarchicalReferences)
        try:
            return (await (non_hierarchical_references.get_child(f"{self._ns_idx_other}:UsesResource"))).nodeid
        except:  # legacy
            return (await (non_hierarchical_references.get_child("2:UseResource"))).nodeid
