"""OPC UA toolset based on pyuaadapter client (v4 only)."""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.services import opcua_service as svc

logger = logging.getLogger(__name__)


def connect_to_server(
    endpoint: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> dict[str, Any]:
    """Connect to OPC UA server with pyuaadapter v4 client."""
    return svc.connect_server_sync(endpoint, username, password)


def disconnect(endpoint: str) -> dict[str, Any]:
    """Disconnect current pyuaadapter session for endpoint."""
    return svc.disconnect_server_sync(endpoint)


def list_skills(
    endpoint: str,
    machine_name: Optional[str] = None,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    """Read skills for machines/components (v4 skill set only)."""
    return svc.list_skills_sync(
        endpoint=endpoint,
        machine_name=machine_name,
        component_name=component_name,
    )


def read_component_parameters(
    endpoint: str,
    machine_name: str,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    """Read component parameter variables."""
    return svc.read_component_parameters_sync(
        endpoint=endpoint,
        machine_name=machine_name,
        component_name=component_name,
    )


def read_component_monitoring(
    endpoint: str,
    machine_name: str,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    """Read component monitoring variables."""
    return svc.read_component_monitoring_sync(
        endpoint=endpoint,
        machine_name=machine_name,
        component_name=component_name,
    )


def read_component_attributes(
    endpoint: str,
    machine_name: str,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    """Read component attributes."""
    return svc.read_component_attributes_sync(
        endpoint=endpoint,
        machine_name=machine_name,
        component_name=component_name,
    )


def read_skill_parameters(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    component_name: Optional[str] = None,
    scope: str = "execution",
) -> dict[str, Any]:
    """Read skill parameter set (execution/feasibility/precondition)."""
    return svc.read_skill_parameters_sync(
        endpoint=endpoint,
        machine_name=machine_name,
        skill_name=skill_name,
        component_name=component_name,
        scope=scope,
    )


def read_skill_monitoring(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    component_name: Optional[str] = None,
    scope: str = "execution",
) -> dict[str, Any]:
    """Read skill monitoring variables."""
    return svc.read_skill_monitoring_sync(
        endpoint=endpoint,
        machine_name=machine_name,
        skill_name=skill_name,
        component_name=component_name,
        scope=scope,
    )


def write_skill_parameter(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    parameter_name: str,
    value: Any,
    component_name: Optional[str] = None,
    scope: str = "execution",
) -> dict[str, Any]:
    """Write one skill parameter (requires OPCUA_ENABLE_WRITE_EXECUTE=true)."""
    return svc.write_skill_parameter_sync(
        endpoint=endpoint,
        machine_name=machine_name,
        skill_name=skill_name,
        parameter_name=parameter_name,
        value=value,
        component_name=component_name,
        scope=scope,
    )


def execute_skill(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    component_name: Optional[str] = None,
    scope: str = "execution",
    action: str = "start",
    write_parameters: bool = False,
) -> dict[str, Any]:
    """Execute skill action (start/reset/halt/suspend) when enabled by flag."""
    return svc.execute_skill_sync(
        endpoint=endpoint,
        machine_name=machine_name,
        skill_name=skill_name,
        component_name=component_name,
        scope=scope,
        action=action,
        write_parameters=write_parameters,
    )


OPCUA_TOOL_REGISTRY: dict[str, Any] = {
    "connect_to_server": connect_to_server,
    "disconnect": disconnect,
    "list_skills": list_skills,
    "read_component_parameters": read_component_parameters,
    "read_component_monitoring": read_component_monitoring,
    "read_component_attributes": read_component_attributes,
    "read_skill_parameters": read_skill_parameters,
    "read_skill_monitoring": read_skill_monitoring,
    "write_skill_parameter": write_skill_parameter,
    "execute_skill": execute_skill,
}
