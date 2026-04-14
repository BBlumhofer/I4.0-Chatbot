"""
Backward-compatibility shim.

All Neo4j tool logic has been moved to the ``app.tools.neo4j`` sub-package
(one file per AAS submodel).  This module re-exports the public symbols so
that existing imports continue to work without modification.

Prefer importing from ``app.tools.neo4j`` directly in new code.
"""
from app.tools.neo4j import SUBMODEL_REGISTRY, VALID_SUBMODELS  # noqa: F401
