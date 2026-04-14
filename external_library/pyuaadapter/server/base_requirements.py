from __future__ import annotations

from abc import ABC

import structlog
from asyncua import Node

from .ua_types import UaTypes


class BaseRequirements(ABC):
    """ Base class for requirements """
    # TODO add init_requirements method from asset in this class, see placeholder method
    logger: structlog.BoundLogger
    _ua_node: Node
    ua_requirements_folder: Node

    def __init__(self):
        self._dependencies: list[BaseRequirements] = []  # these are checked before this skill can be executed

    async def _add_dependency_reference(self, other: Node,
                                        source: Node | None = None) -> None:
        """
         Adds dependency reference from a source node to a target node
        :param other: the target node
        :param source: optional source, if source is None requirements folder node is used
        """

        if source is None:
            source = self.ua_requirements_folder

        await source.add_reference(other, UaTypes.depends_ref)  # type: ignore
        self.logger.debug("Added dependency reference", target=other.nodeid.to_string(),
                          source=source.nodeid.to_string())

    async def add_dependency(self, other: BaseRequirements | Node,
                             source: Node | None = None) -> None:
        """
        Adds the given skill, port or other OPC UA node as a dependency of this skill.

        Influences the conditions before this skill can be executed:
        * If the dependency is a port, it must be coupled.
        * If the dependency is a finite skill, it must be ready.
        * If the dependency is a continuous skill, it must be running.
        """

        if not hasattr(self, "ua_requirements_folder"):
            await self._init_requirements()

        if other is None:
            raise RuntimeError("No dependency is given!")

        if isinstance(other, BaseRequirements):
            self._dependencies.append(other)
            await self._add_dependency_reference(other._ua_node, source)
        else:
            await self._add_dependency_reference(other, source)

    async def _init_requirements(self):
        pass
