from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING

from asyncua import Node, ua
from asyncua.ua import NodeId, uaerrors
from typing_extensions import override

from pyuaadapter.client.base_remote_skill import SkillTypes, BaseRemoteSkill
from pyuaadapter.common.namespace_uri import NS_SKILL_SET_URI, NS_MACHINE_SET_URI

if TYPE_CHECKING:
    from pyuaadapter.client.remote_server import RemoteServer


class RemoteSkill(BaseRemoteSkill):
    """Represents a remote skill for skill node-set version 4."""

    def __init__(self, name: str, base_node: Node, remote_server: "RemoteServer"):
        super().__init__(name, base_node, remote_server)

        self._ns_idx_methods = self._remote_server.namespace_map[NS_MACHINE_SET_URI]
        self._ns_idx_other = self._remote_server.namespace_map[NS_SKILL_SET_URI]

    @override
    async def _setup_type_and_dependencies(self):
        ua_ref_depends_on = await self._get_dependency_reference_node_id()
        ua_skill_parent: Node = await self._ua_base_node.get_parent()  # type: ignore

        try:
            ua_skill_requirements = await ua_skill_parent.get_child(f"{self._ns_idx_other}:Requirements") # Optional
        except uaerrors.BadNoMatch:
            ua_skill_requirements = None  # is optional, so no problem

        for reference in chain(await ua_skill_parent.get_references(),
                               [] if ua_skill_requirements is None else await ua_skill_requirements.get_references()):
            # reference: ReferenceDescription = reference
            if reference.BrowseName.Name == 'FiniteSkillType':
                self._type = SkillTypes.Finite
            elif reference.BrowseName.Name == 'ContinuousSkillType':
                self._type = SkillTypes.Continuous
            elif reference.ReferenceTypeId == ua_ref_depends_on:
                if reference.IsForward:
                    self._depends_on[reference.NodeId] = reference.BrowseName.Name
                else:
                    # reference.NodeId usually only points to Requirements folder
                    if reference.BrowseName.Name == "Requirements":
                        actual_node: Node = await self._remote_server.ua_client.get_node(reference.NodeId).get_parent()  # type: ignore
                        self._dependency_of[actual_node.nodeid] = (await actual_node.read_browse_name()).Name
                    else:
                        self._dependency_of[reference.NodeId] = reference.BrowseName.Name

        if self._type == SkillTypes.Unknown:
            self.logger.warning(f"Could not determine skill type of {self.name}!")

    @override
    async def _get_dependency_reference_node_id(self) -> NodeId:
        return ua.FourByteNodeId(ua.Int32(ua.ObjectIds.Requires))
