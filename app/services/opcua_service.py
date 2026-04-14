"""OPC UA service based on pyuaadapter client (v4 only)."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _import_remote_server_cls():
    """
    Import pyuaadapter lazily.

    In local dev the package can come from pip or from external_library.
    """
    try:
        from pyuaadapter.client.remote_server import RemoteServer
        return RemoteServer
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parents[2]
        fallback_pkg_root = repo_root / "external_library"
        import sys

        if str(fallback_pkg_root) not in sys.path:
            sys.path.insert(0, str(fallback_pkg_root))

        from pyuaadapter.client.remote_server import RemoteServer
        return RemoteServer


def _resolve_credentials_file() -> Path:
    cfg_path = Path(settings.opcua_credentials_file)
    if cfg_path.is_absolute():
        return cfg_path
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / cfg_path


def load_credentials_file() -> dict[str, dict[str, str]]:
    """Load endpoint credentials from cred.json-like file."""
    file_path = _resolve_credentials_file()
    if not file_path.exists():
        logger.warning("OPC UA credentials file not found: %s", file_path)
        return {}

    with file_path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)

    if isinstance(raw, dict) and "servers" in raw and isinstance(raw["servers"], list):
        result: dict[str, dict[str, str]] = {}
        for entry in raw["servers"]:
            endpoint = entry.get("endpoint")
            if not endpoint:
                continue
            result[endpoint] = {
                "username": entry.get("username", ""),
                "password": entry.get("password", ""),
            }
        return result

    if isinstance(raw, dict):
        return {
            endpoint: {
                "username": value.get("username", ""),
                "password": value.get("password", ""),
            }
            for endpoint, value in raw.items()
            if isinstance(value, dict)
        }

    return {}


class PyUaAdapterSessionManager:
    """Keeps pyuaadapter RemoteServer sessions per endpoint."""

    def __init__(self) -> None:
        self._servers: dict[str, Any] = {}
        self._credentials = load_credentials_file()

    def _resolve_login(
        self,
        endpoint: str,
        username: Optional[str],
        password: Optional[str],
    ) -> tuple[str, str]:
        creds = self._credentials.get(endpoint, {})
        return (
            username if username is not None else creds.get("username", ""),
            password if password is not None else creds.get("password", ""),
        )

    async def connect(
        self,
        endpoint: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> dict[str, Any]:
        RemoteServer = _import_remote_server_cls()
        resolved_user, resolved_pw = self._resolve_login(endpoint, username, password)

        existing = self._servers.get(endpoint)
        if existing is not None and existing.connected:
            return {
                "endpoint": endpoint,
                "status": "connected",
                "already_connected": True,
                "machines": sorted(existing.machines.keys()),
                "username": resolved_user,
            }

        remote = RemoteServer(
            url=endpoint,
            username=resolved_user,
            password=resolved_pw,
            browse_skills=True,
            browse_identification=True,
            browse_resources=True,
            browse_methods=True,
            browse_on_reconnect=True,
            setup_logging=False,
        )
        await remote.connect(timeout=10.0, reconnect_try_delay=3.0, max_retries=1)
        self._servers[endpoint] = remote

        return {
            "endpoint": endpoint,
            "status": "connected",
            "already_connected": False,
            "machines": sorted(remote.machines.keys()),
            "username": resolved_user,
        }

    async def disconnect(self, endpoint: str) -> dict[str, Any]:
        remote = self._servers.pop(endpoint, None)
        if remote is None:
            return {"endpoint": endpoint, "status": "not_connected"}
        await remote.disconnect()
        return {"endpoint": endpoint, "status": "disconnected"}

    async def get_connected(self, endpoint: str) -> Any:
        remote = self._servers.get(endpoint)
        if remote is None or not remote.connected:
            await self.connect(endpoint)
            remote = self._servers[endpoint]
        return remote


session_manager = PyUaAdapterSessionManager()


def _serialize_var(var: Any) -> dict[str, Any]:
    return {
        "name": var.name,
        "node_id": var.ua_node.nodeid.to_string(),
        "value": var.value,
        "is_writable": var.is_writable,
        "ua_data_type": var.ua_data_type,
        "ua_value_rank": var.ua_value_rank,
        "valid_values": var.valid_values,
        "timestamp": var.timestamp.isoformat() if var.timestamp else None,
    }


def _find_component(machine: Any, component_name: Optional[str]) -> Any:
    if not component_name:
        return machine

    queue = list(machine.components.values())
    while queue:
        comp = queue.pop(0)
        if comp.name == component_name:
            return comp
        queue.extend(comp.components.values())
    raise ValueError(f"Komponente '{component_name}' nicht gefunden.")


def _find_machine(remote: Any, machine_name: str) -> Any:
    machine = remote.machines.get(machine_name)
    if machine is None:
        raise ValueError(
            f"Maschine '{machine_name}' nicht gefunden. Verfuegbar: {sorted(remote.machines.keys())}"
        )
    return machine


def _select_skill(component: Any, skill_name: str, scope: str) -> Any:
    normalized_scope = (scope or "execution").strip().lower()
    if normalized_scope == "execution":
        skill_map = component.skill_set
    elif normalized_scope == "feasibility":
        skill_map = component.feasibility_check_set
    elif normalized_scope == "precondition":
        skill_map = component.precondition_check_set
    else:
        raise ValueError("scope muss execution, feasibility oder precondition sein")

    skill = skill_map.get(skill_name)
    if skill is None:
        raise ValueError(f"Skill '{skill_name}' nicht gefunden (scope={normalized_scope}).")
    return skill


async def connect_server(
    endpoint: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> dict[str, Any]:
    return await session_manager.connect(endpoint, username, password)


async def disconnect_server(endpoint: str) -> dict[str, Any]:
    return await session_manager.disconnect(endpoint)


async def list_skills(
    endpoint: str,
    machine_name: Optional[str] = None,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    remote = await session_manager.get_connected(endpoint)
    machine_names = [machine_name] if machine_name else sorted(remote.machines.keys())

    result: dict[str, Any] = {"endpoint": endpoint, "machines": {}}
    for m_name in machine_names:
        machine = _find_machine(remote, m_name)
        target_component = _find_component(machine, component_name)
        result["machines"][m_name] = {
            "component": target_component.name,
            "skills": [
                {
                    "name": skill.name,
                    "type": skill.type.name,
                    "state": skill.current_state.name,
                    "suspendable": skill.suspendable,
                    "min_access_level": skill.min_access_level,
                    "scope": "execution",
                }
                for skill in target_component.skill_set.values()
            ],
            "feasibility_checks": [
                {"name": skill.name, "state": skill.current_state.name, "scope": "feasibility"}
                for skill in target_component.feasibility_check_set.values()
            ],
            "precondition_checks": [
                {"name": skill.name, "state": skill.current_state.name, "scope": "precondition"}
                for skill in target_component.precondition_check_set.values()
            ],
        }
    return result


async def read_component_parameters(
    endpoint: str,
    machine_name: str,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    remote = await session_manager.get_connected(endpoint)
    machine = _find_machine(remote, machine_name)
    component = _find_component(machine, component_name)
    return {
        "endpoint": endpoint,
        "machine": machine_name,
        "component": component.name,
        "parameters": [_serialize_var(v) for v in component.parameter_set.values()],
    }


async def read_component_monitoring(
    endpoint: str,
    machine_name: str,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    remote = await session_manager.get_connected(endpoint)
    machine = _find_machine(remote, machine_name)
    component = _find_component(machine, component_name)
    return {
        "endpoint": endpoint,
        "machine": machine_name,
        "component": component.name,
        "monitoring": [_serialize_var(v) for v in component.monitoring.values()],
    }


async def read_component_attributes(
    endpoint: str,
    machine_name: str,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    remote = await session_manager.get_connected(endpoint)
    machine = _find_machine(remote, machine_name)
    component = _find_component(machine, component_name)
    return {
        "endpoint": endpoint,
        "machine": machine_name,
        "component": component.name,
        "attributes": [_serialize_var(v) for v in component.attributes.values()],
    }


async def read_skill_parameters(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    component_name: Optional[str] = None,
    scope: str = "execution",
) -> dict[str, Any]:
    remote = await session_manager.get_connected(endpoint)
    machine = _find_machine(remote, machine_name)
    component = _find_component(machine, component_name)
    skill = _select_skill(component, skill_name, scope)
    return {
        "endpoint": endpoint,
        "machine": machine_name,
        "component": component.name,
        "skill": skill.name,
        "scope": scope,
        "parameters": [_serialize_var(v) for v in skill.parameter_set.values()],
    }


async def read_skill_monitoring(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    component_name: Optional[str] = None,
    scope: str = "execution",
) -> dict[str, Any]:
    remote = await session_manager.get_connected(endpoint)
    machine = _find_machine(remote, machine_name)
    component = _find_component(machine, component_name)
    skill = _select_skill(component, skill_name, scope)
    return {
        "endpoint": endpoint,
        "machine": machine_name,
        "component": component.name,
        "skill": skill.name,
        "scope": scope,
        "monitoring": [_serialize_var(v) for v in skill.monitoring.values()],
    }


async def write_skill_parameter(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    parameter_name: str,
    value: Any,
    component_name: Optional[str] = None,
    scope: str = "execution",
) -> dict[str, Any]:
    if not settings.opcua_enable_write_execute:
        raise PermissionError("Schreiben von Skill-Parametern ist deaktiviert (OPCUA_ENABLE_WRITE_EXECUTE=false).")

    remote = await session_manager.get_connected(endpoint)
    machine = _find_machine(remote, machine_name)
    component = _find_component(machine, component_name)
    skill = _select_skill(component, skill_name, scope)

    variable = skill.parameter_set.get(parameter_name)
    if variable is None:
        raise ValueError(f"Parameter '{parameter_name}' im Skill '{skill_name}' nicht gefunden.")
    await variable.write_value(value)

    return {
        "endpoint": endpoint,
        "machine": machine_name,
        "component": component.name,
        "skill": skill.name,
        "parameter": parameter_name,
        "written_value": value,
        "status": "ok",
    }


async def execute_skill(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    component_name: Optional[str] = None,
    scope: str = "execution",
    action: str = "start",
    write_parameters: bool = False,
) -> dict[str, Any]:
    if not settings.opcua_enable_write_execute:
        raise PermissionError("Skill-Ausfuehrung ist deaktiviert (OPCUA_ENABLE_WRITE_EXECUTE=false).")

    remote = await session_manager.get_connected(endpoint)
    machine = _find_machine(remote, machine_name)
    component = _find_component(machine, component_name)
    skill = _select_skill(component, skill_name, scope)

    normalized_action = action.strip().lower()
    if normalized_action == "start":
        await skill.start(write_parameters=write_parameters)
    elif normalized_action == "reset":
        await skill.reset()
    elif normalized_action == "halt":
        await skill.halt()
    elif normalized_action == "suspend":
        await skill.suspend()
    else:
        raise ValueError("action muss start, reset, halt oder suspend sein")

    return {
        "endpoint": endpoint,
        "machine": machine_name,
        "component": component.name,
        "skill": skill.name,
        "scope": scope,
        "action": normalized_action,
        "state_after": skill.current_state.name,
        "status": "ok",
    }


def connect_server_sync(
    endpoint: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> dict[str, Any]:
    return asyncio.run(connect_server(endpoint, username, password))


def disconnect_server_sync(endpoint: str) -> dict[str, Any]:
    return asyncio.run(disconnect_server(endpoint))


def list_skills_sync(
    endpoint: str,
    machine_name: Optional[str] = None,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    return asyncio.run(list_skills(endpoint, machine_name, component_name))


def read_component_parameters_sync(
    endpoint: str,
    machine_name: str,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    return asyncio.run(read_component_parameters(endpoint, machine_name, component_name))


def read_component_monitoring_sync(
    endpoint: str,
    machine_name: str,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    return asyncio.run(read_component_monitoring(endpoint, machine_name, component_name))


def read_component_attributes_sync(
    endpoint: str,
    machine_name: str,
    component_name: Optional[str] = None,
) -> dict[str, Any]:
    return asyncio.run(read_component_attributes(endpoint, machine_name, component_name))


def read_skill_parameters_sync(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    component_name: Optional[str] = None,
    scope: str = "execution",
) -> dict[str, Any]:
    return asyncio.run(read_skill_parameters(endpoint, machine_name, skill_name, component_name, scope))


def read_skill_monitoring_sync(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    component_name: Optional[str] = None,
    scope: str = "execution",
) -> dict[str, Any]:
    return asyncio.run(read_skill_monitoring(endpoint, machine_name, skill_name, component_name, scope))


def write_skill_parameter_sync(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    parameter_name: str,
    value: Any,
    component_name: Optional[str] = None,
    scope: str = "execution",
) -> dict[str, Any]:
    return asyncio.run(
        write_skill_parameter(
            endpoint=endpoint,
            machine_name=machine_name,
            skill_name=skill_name,
            parameter_name=parameter_name,
            value=value,
            component_name=component_name,
            scope=scope,
        )
    )


def execute_skill_sync(
    endpoint: str,
    machine_name: str,
    skill_name: str,
    component_name: Optional[str] = None,
    scope: str = "execution",
    action: str = "start",
    write_parameters: bool = False,
) -> dict[str, Any]:
    return asyncio.run(
        execute_skill(
            endpoint=endpoint,
            machine_name=machine_name,
            skill_name=skill_name,
            component_name=component_name,
            scope=scope,
            action=action,
            write_parameters=write_parameters,
        )
    )
