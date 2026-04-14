# Step-Bau-Tools für StorageModule
import json
import os
from datetime import datetime
from typing import Optional, Annotated, List, Dict, Any

from aaspyclasses.submodels.production_plan.step import StepStateEnum
# Step-Bau-Tools für StorageModule
from aaspyclasses.submodels.production_plan.templates.storage_module import StorageModule
from agent_management.client.client import AgentManagementClient
from agent_management.common.agent_item import FullAgentIdentification
from agent_management.common.i40_message_types import StepModeEnum
from fastmcp import FastMCP, Context
from pydantic import Field

# -----------------------------------------------------------------------------
# Order tools

# Configuration
BASE_URL = os.getenv("AGENT_REGISTRY_URL", "http://172.17.200.155:8001")
API_KEY = os.getenv("AGENT_REGISTRY_KEY", "mjadijOISJIDzz&251q9jdfca")

# Create FastMCP server with comprehensive configuration
mcp = FastMCP(
    name="AgentManagement-MCP-Server",
    instructions="""
    This server provides comprehensive access to AgentManagement functionality through MCP.
    
    Key capabilities:
    - Agent lifecycle management (spawn, restart, kill)
    - Agent registration and discovery
    - Production step management and surgery operations
    - Dynamic agent data access through resources
    - Templated prompts for common operations
    
    Use the tools to perform operations, resources to access data, and prompts for guidance.
    In many tools the conversaionId is required. The conversationId is the Product Identifier to know which product is related.
    """,
    include_fastmcp_meta=True
)

# Global client instance for reuse
agent_client: Optional[AgentManagementClient] = None


async def get_agent_client() -> AgentManagementClient:
    """Get or create the global agent registry client."""
    global agent_client
    if agent_client is None:
        agent_client = AgentManagementClient(base_url=BASE_URL)
    return agent_client


# -----------------------------------------------------------------------------
# Inlined MCP Tools (previously in mcp_tools.py)
# -----------------------------------------------------------------------------

# Note: these tools use the global `mcp` instance and `get_agent_client()` defined above.

@mcp.tool(
    name="get_all_registered_agents",
    description="Retrieve a list of all agents currently registered in the AgentRegistry",
    tags={"registry", "query", "agents"},
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def get_all_registered_agents(ctx: Context) -> List[str]:
    await ctx.info("Fetching all registered agents from AgentRegistry")
    client = await get_agent_client()
    try:
        result = await client.registry.get_all_registered_agents()
        await ctx.info(f"Found {len(result)} registered agents")
        return result
    except Exception as e:
        await ctx.error(f"Failed to fetch registered agents: {str(e)}")
        raise


@mcp.tool(
    name="register_agent",
    description="Register a new agent in the AgentRegistry with full configuration details",
    tags={"registry", "create", "agents"},
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False
    }
)
async def register_agent(
        agent_id: Annotated[str, Field(description="Unique identifier for the agent")],
        name: Annotated[str, Field(description="Human-readable name for the agent")],
        agent_type: Annotated[str, Field(
            description="Type or category of the agent: ManagementHolon, CPPM_EnergyHolon,CPPM_ResourceHolon,ProductHolon or Island_ResourceHolon")],
        url: Annotated[
            Optional[str], Field(description="URL endpoint for the Asset Administration Shell of the Asset")] = None,
        ref: Annotated[Optional[str], Field(description="Reference to the parent holon")] = None,
        agents: Annotated[Optional[List[str]], Field(description="Sub Agents/Children of the Agent")] = None,
        capabilities: Annotated[Optional[List[str]], Field(description="Capabilities of the Agent")] = None,
        subs: Annotated[Optional[List[str]], Field(description="Subscriptions of the Agent")] = None,
        neighbors: Annotated[Optional[List[str]], Field(description="Neighbor Agents of this Agent")] = None,
        ctx: Context = None
) -> None:
    await ctx.info(f"Registering agent '{name}' with ID '{agent_id}'")

    agent = FullAgentIdentification(
        id=agent_id,
        name=name,
        type=agent_type,
        url=url,
        ref=ref,
        agents=agents,
        capabilities=capabilities,
        subs=subs,
        neighbors=neighbors
    )

    client = await get_agent_client()
    try:
        await client.registry.register_agent(agent)
        await ctx.info(f"Successfully registered agent '{name}'")
    except Exception as e:
        await ctx.error(f"Failed to register agent '{name}': {str(e)}")
        raise


@mcp.tool(
    name="unregister_agent",
    description="Remove an agent from the AgentRegistry",
    tags={"registry", "delete", "agents"},
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True
    }
)
async def unregister_agent(
        agent_id: Annotated[str, Field(description="ID of the agent to unregister")],
        ctx: Context = None
) -> None:
    await ctx.info(f"Unregistering agent with ID '{agent_id}'")

    client = await get_agent_client()
    try:
        await client.registry.unregister_agent(agent_id)
        await ctx.info(f"Successfully unregistered agent '{agent_id}'")
    except Exception as e:
        await ctx.error(f"Failed to unregister agent '{agent_id}': {str(e)}")
        raise


@mcp.tool(
    name="get_agent_details",
    description="Get detailed information about a specific agent",
    tags={"registry", "query", "agents"},
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True
    }
)
async def get_agent_details(
        agent_id: Annotated[str, Field(description="ID of the agent to query")],
        ctx: Context = None
) -> Dict[str, Any]:
    await ctx.info(f"Fetching details for agent '{agent_id}'")

    client = await get_agent_client()
    try:
        agent = await client.registry.get_agent_details(agent_id)
        await ctx.info(f"Retrieved details for agent '{agent.name}'")
        return agent.model_dump()
    except Exception as e:
        await ctx.error(f"Failed to get details for agent '{agent_id}': {str(e)}")
        raise


@mcp.tool(
    name="spawn_agent",
    description="Start a new instance of an agent. Used to create agents. Agent will automatically register.",
    tags={"lifecycle", "spawn", "agents"},
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False
    }
)
async def spawn_agent(
        receiver: Annotated[str, Field(description="ID of the agent that spawns the agent - should be an agent "
                                                   "of type management holon or an agent that has no reference,"
                                                   " i.e. no parent")],
        agent_id: Annotated[str, Field(description="ID of the agent to spawn")],
        ctx: Context = None
) -> None:
    await ctx.info(f"Spawning agent '{agent_id}'")

    client = await get_agent_client()
    try:
        await client.lifecycle_management.spawn_agent(receiver=receiver, agent_to_spawn=agent_id)
        await ctx.info(f"Successfully spawned agent '{agent_id}'")
    except Exception as e:
        await ctx.error(f"Failed to spawn agent '{agent_id}': {str(e)}")
        raise


@mcp.tool(
    name="restart_agent",
    description="Restart an existing agent instance",
    tags={"lifecycle", "restart", "agents"},
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False
    }
)
async def restart_agent(
        receiver: Annotated[str, Field(description="ID of the agent to restart")],
        ctx: Context = None
) -> None:
    await ctx.info(f"Restarting agent '{receiver}'")

    client = await get_agent_client()
    try:
        await client.lifecycle_management.restart_agent(receiver=receiver)
        await ctx.info(f"Successfully restarted agent '{receiver}'")
    except Exception as e:
        await ctx.error(f"Failed to restart agent '{receiver}': {str(e)}")
        raise


@mcp.tool(
    name="kill_agent",
    description="Stop and terminate an agent instance",
    tags={"lifecycle", "kill", "agents"},
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True
    }
)
async def kill_agent(
        receiver: Annotated[str, Field(description="ID of the agent to kill")],
        ctx: Context = None
) -> None:
    await ctx.info(f"Killing agent '{receiver}'")

    client = await get_agent_client()
    try:
        await client.lifecycle_management.kill_agent(receiver=receiver)
        await ctx.info(f"Successfully killed agent '{receiver}'")
    except Exception as e:
        await ctx.error(f"Failed to kill agent '{receiver}': {str(e)}")
        raise


# -----------------------------------------------------------------------------
# Inlined MCP Resources (previously in mcp_resources.py)
# -----------------------------------------------------------------------------

@mcp.resource(
    name="agent_registry_status",
    description="Current status and overview of the AgentRegistry system",
    uri="agentregistry://system/status"
)
async def agent_registry_status(ctx: Context) -> str:
    await ctx.info("Fetching AgentRegistry system status")
    try:
        client = await get_agent_client()
        agents = await client.registry.get_all_registered_agents()
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "system_status": "online",
            "total_agents": len(agents),
            "registered_agents": agents,
            "base_url": getattr(client, '_base_url', BASE_URL),
            "api_version": "v1",
            "last_updated": datetime.now().isoformat()
        }
        await ctx.info(f"System status retrieved - {len(agents)} agents registered")
        return json.dumps(status_data, indent=2)
    except Exception as e:
        await ctx.error(f"Failed to fetch system status: {str(e)}")
        error_status = {
            "timestamp": datetime.now().isoformat(),
            "system_status": "error",
            "error_message": str(e),
            "total_agents": 0,
            "registered_agents": []
        }
        return json.dumps(error_status, indent=2)


@mcp.resource(
    name="agents_list",
    description="Complete list of all registered agents with basic information",
    uri="agentregistry://agents/list"
)
async def agents_list(ctx: Context) -> str:
    await ctx.info("Fetching complete agents list")
    try:
        client = await get_agent_client()
        agents = await client.registry.get_all_registered_agents()
        agents_data = {
            "timestamp": datetime.now().isoformat(),
            "total_count": len(agents),
            "agents": []
        }
        for agent_id in agents:
            agents_data["agents"].append({
                "id": agent_id,
                "status": "registered"
            })
        await ctx.info(f"Retrieved information for {len(agents)} agents")
        return json.dumps(agents_data, indent=2)
    except Exception as e:
        await ctx.error(f"Failed to fetch agents list: {str(e)}")
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "total_count": 0,
            "agents": []
        }
        return json.dumps(error_data, indent=2)


@mcp.resource(
    name="agent_details/{agent_id}",
    description="Detailed information about a specific agent",
    uri="agentregistry://agents/{agent_id}"
)
async def agent_details(ctx: Context, agent_id: str) -> str:
    await ctx.info(f"Fetching details for agent '{agent_id}'")
    try:
        client = await get_agent_client()
        agents = await client.registry.get_all_registered_agents()
        if agent_id not in agents:
            not_found_data = {
                "timestamp": datetime.now().isoformat(),
                "agent_id": agent_id,
                "status": "not_found",
                "error": f"Agent '{agent_id}' is not registered in the system"
            }
            return json.dumps(not_found_data, indent=2)
        agent_data = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "status": "registered",
            "registration_confirmed": True,
            "available_operations": ["spawn", "restart", "kill", "repeat_action", "terminate_action"]
        }
        await ctx.info(f"Retrieved details for agent '{agent_id}'")
        return json.dumps(agent_data, indent=2)
    except Exception as e:
        await ctx.error(f"Failed to fetch details for agent '{agent_id}': {str(e)}")
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "status": "error",
            "error_message": str(e)
        }
        return json.dumps(error_data, indent=2)


@mcp.prompt(
    name="register_new_agent",
    description="Interactive prompt for registering a new agent in the system",
    tags={"registration", "setup", "agent-creation"}
)
async def register_new_agent_prompt(
        ctx: Context,
        agent_type: Optional[str] = None,
        use_case: Optional[str] = None
) -> str:
    prompt_content = f"""
# Agent Registration Assistant
\n+This prompt helps you prepare a complete registration for a new agent (role-aware).
Provide the following fields when calling the `register_agent` tool. The server recognises these common roles (agent_type):

- ManagementHolon
- CPPM_EnergyHolon
- CPPM_ResourceHolon
- ProductHolon
- Island_ResourceHolon

Required parameters for `register_agent`:
- agent_id: Unique identifier (string)
- name: Human-readable name
- agent_type: One of the roles listed above

Optional but recommended parameters:
- url: URL endpoint of the agent's AAS (Asset Administration Shell)
- ref: Reference to parent holon or external system
- agents: List of sub-agent IDs (children)
- capabilities: List of capability identifiers or human labels
- subs: List of subscription topics or channels
- neighbors: List of neighbor agent IDs

Example JSON payload for `register_agent`:

```
{
    "agent_id": "P17",
    "name": "CollaborativeAssemblyModule",
    "agent_type": "CPPM_ResourceHolon",
    "url": "http://92.205.177.115:8000/#/shell/UDE3",
    "ref": "RH2",
    "agents": [],
    "capabilities": [],
    "subs": [],
    "neighbors": ["P18"]
}
```

Best practices:
- Use clear, descriptive `agent_id` values (no spaces).
- Choose the `agent_type` role that best matches the agent's responsibility.
- Add `capabilities` to enable discovery by workflow planners.
- List `neighbors`/`agents` to express topology and hierarchy.

{f'Pre-configured for {use_case} use case.' if use_case else ''}
"""
    await ctx.info(f"Generated agent registration prompt{f' for {agent_type} agent' if agent_type else ''}")
    return prompt_content


@mcp.prompt(
    name="kafka_messaging_guide",
    description="Guide for using Kafka messaging capabilities in the AgentManagement system",
    tags={"kafka", "messaging", "monitoring"}
)
async def kafka_messaging_guide(
        ctx: Context,
        topic_category: Optional[str] = None
) -> str:
    await ctx.info(f"Generating Kafka messaging guide{f' for category: {topic_category}' if topic_category else ''}")
    guide = """
# Kafka Messaging Guide for AgentManagement

This server can interact with a Kafka broker for monitoring, command forwarding and eventing.

Useful steps:
1. Discover topics: use `list_kafka_topics(category)` to find lifecycle / production / monitoring topics.
2. Inspect a topic: use `get_kafka_topic_info(topic_name)` for broker and description.
3. Read recent messages: use `read_kafka_messages(topic_name, max_messages)` to sample events.
4. Send commands: use `send_kafka_message(topic_name, message)` to publish control messages (e.g., Spawn_Agent, Kill_Agent).

Example: send a status-check to an agent group

```
await send_kafka_message("Request_Agent", {"action":"status_check","target":"assembly_station_*"})
```

Note: Kafka tools throw an error when Kafka libraries are not installed or broker is unreachable.
"""
    return guide


# -----------------------------------------------------------------------------
# Kafka integration (inlined from kafka_integration.py)
# -----------------------------------------------------------------------------

try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
    from kafka import KafkaConsumer

    KAFKA_AVAILABLE = True
except Exception:
    KAFKA_AVAILABLE = False

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "172.17.200.155:9092")

_kafka_consumer = None
_kafka_producer = None

# Minimal topic map
KAFKA_TOPICS = {
    "AgentKilled_External": {"description": "Notifications when agents are killed", "category": "lifecycle"},
    "Kill_Agent": {"description": "Commands to kill agents", "category": "lifecycle"},
    "Restart_Agent": {"description": "Commands to restart agents", "category": "lifecycle"},
    "Spawn_Agent": {"description": "Commands to spawn agents", "category": "lifecycle"},
    "AnswerAgent": {"description": "Responses from agents", "category": "communication"},
}


def get_topic_info(topic_name: str) -> Dict[str, Any]:
    if topic_name in KAFKA_TOPICS:
        return {"name": topic_name, **KAFKA_TOPICS[topic_name], "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS}
    return {"name": topic_name, "description": "Unknown topic", "category": "unknown",
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS}


def get_topics_by_category(category: str = None) -> Dict[str, Dict[str, Any]]:
    if category is None:
        return KAFKA_TOPICS
    return {t: info for t, info in KAFKA_TOPICS.items() if info.get("category") == category}


async def consume_messages(topic_name: str, max_messages: int = 10, timeout_seconds: int = 30) -> List[Dict[str, Any]]:
    if not KAFKA_AVAILABLE:
        raise RuntimeError("Kafka libraries not available")
    messages = []
    consumer = AIOKafkaConsumer(topic_name, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS, auto_offset_reset='earliest',
                                enable_auto_commit=False, group_id=f'mcp-reader-{datetime.now().timestamp()}',
                                value_deserializer=lambda x: x.decode('utf-8') if x else None)
    await consumer.start()
    try:
        start = datetime.now()
        async for msg in consumer:
            if len(messages) >= max_messages:
                break
            if (datetime.now() - start).seconds > timeout_seconds:
                break
            try:
                val = msg.value
                try:
                    parsed = json.loads(val) if val else None
                except Exception:
                    parsed = val
                messages.append({"topic": msg.topic, "partition": msg.partition, "offset": msg.offset,
                                 "timestamp": datetime.fromtimestamp(
                                     msg.timestamp / 1000).isoformat() if msg.timestamp else None,
                                 "key": msg.key.decode('utf-8') if msg.key else None, "value": parsed})
            except Exception as e:
                messages.append({"topic": msg.topic, "error": str(e)})
    finally:
        await consumer.stop()
    return messages


# -----------------------------------------------------------------------------
# Kafka MCP Tools
# -----------------------------------------------------------------------------

@mcp.tool(name="list_kafka_topics", description="List available Kafka topics", tags={"kafka", "monitoring"})
def list_kafka_topics(category: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    return get_topics_by_category(category)


@mcp.tool(name="get_kafka_topic_info", description="Get information about a Kafka topic", tags={"kafka", "monitoring"})
def mcp_get_kafka_topic_info(topic_name: str) -> Dict[str, Any]:
    return get_topic_info(topic_name)


@mcp.tool(name="read_kafka_messages", description="Read recent messages from a Kafka topic",
          tags={"kafka", "monitoring"})
async def mcp_read_kafka_messages(topic_name: str, max_messages: int = 10, timeout_seconds: int = 10) -> List[
    Dict[str, Any]]:
    return await consume_messages(topic_name, max_messages=max_messages, timeout_seconds=timeout_seconds)


# -----------------------------------------------------------------------------
# Missing registry/hierarchy tools
# -----------------------------------------------------------------------------

@mcp.tool(name="get_agents_of_agent", description="Get all sub-agents registered under a specific agent",
          tags={"registry", "query", "hierarchy"})
async def get_agents_of_agent(agent_id: str, ctx: Context = None) -> List[Dict[str, Any]]:
    await ctx.info(f"Fetching sub-agents for agent '{agent_id}'")
    client = await get_agent_client()
    try:
        agents = await client.registry.get_agents_of_agent(agent_id)
        return [a.model_dump() for a in agents]
    except Exception as e:
        await ctx.error(str(e))
        raise


@mcp.tool(name="register_agent_at_agent", description="Register an agent as a sub-agent under another agent",
          tags={"registry", "create", "hierarchy"})
async def register_agent_at_agent(parent_agent_id: str, agent_id: str, name: str, agent_type: str,
                                  url: Optional[str] = None, ref: Optional[str] = None, ctx: Context = None) -> Dict[
    str, Any]:
    await ctx.info(f"Registering sub-agent '{name}' under parent '{parent_agent_id}'")

    agent = FullAgentIdentification(id=agent_id, name=name, type=agent_type, url=url, ref=ref, agents=[],
                                    capabilities=[], subs=[], neighbors=[])
    client = await get_agent_client()
    try:
        result = await client.registry.register_agent_at_agent(parent_agent_id, agent)
        return result.model_dump()
    except Exception as e:
        await ctx.error(str(e))
        raise


# -----------------------------------------------------------------------------
# Surgery tools
# -----------------------------------------------------------------------------

@mcp.tool(name="repeat_action", description="Request agent to repeat last action", tags={"surgery"})
async def repeat_action(agent_id: str, conversation_id: str, ctx: Context = None) -> None:
    await ctx.info(f"Requesting repeat_action for '{agent_id}'")

    client = await get_agent_client()
    try:
        await client.surgery.repeat_action(agent_id, conversation_id)
    except Exception as e:
        await ctx.error(str(e))
        raise


@mcp.tool(name="terminate_action", description="Request agent to terminate current action", tags={"surgery"})
async def terminate_action(agent_id: str, conversation_id: str, ctx: Context = None) -> List[str]:
    await ctx.info(f"Requesting terminate_action for '{agent_id}'")

    client = await get_agent_client()
    try:
        return await client.surgery.terminate_action(agent_id, conversation_id)
    except Exception as e:
        await ctx.error(str(e))
        raise


@mcp.tool(name="previously_action", description="Request agent to execute previous action", tags={"surgery"})
async def previously_action(agent_id: str, conversation_id: str, ctx: Context = None) -> None:
    await ctx.info(f"Requesting previously_action for '{agent_id}'")

    client = await get_agent_client()
    try:
        await client.surgery.previously_action(agent_id, conversation_id)
    except Exception as e:
        await ctx.error(str(e))
        raise


@mcp.tool(name="idle_mode", description="Enable or disable agent idle mode", tags={"surgery"})
async def idle_mode(agent_id: str, enable: bool, ctx: Context = None) -> None:
    await ctx.info(f"Setting idle_mode for '{agent_id}' to {enable}")

    client = await get_agent_client()
    try:
        await client.surgery.idle_mode(agent_id, enable)
    except Exception as e:
        await ctx.error(str(e))
        raise


@mcp.tool(name="change_step_state", description="Change step execution state", tags={"surgery"})
async def change_step_state(agent_id: str, state: StepModeEnum, conversation_id: str, ctx: Context = None) -> None:
    await ctx.info(f"Changing step state for '{agent_id}' to {state}")

    client = await get_agent_client()
    try:
        await client.surgery.change_step_state(agent_id, state, conversation_id)
    except Exception as e:
        await ctx.error(str(e))
        raise


@mcp.tool(name="kill_step", description="Kill current step execution", tags={"surgery"})
async def kill_step(agent_id: str, conversation_id: str, ctx: Context = None) -> None:
    await ctx.info(f"Killing step for '{agent_id}'")

    client = await get_agent_client()
    try:
        return await client.surgery.kill_step(agent_id, conversation_id)
    except Exception as e:
        await ctx.error(str(e))
        raise


@mcp.tool(name="delete_step", description="Delete a specific step from execution plan", tags={"surgery"})
async def delete_step(agent_id: str, step_id: str, conversation_id: str, ctx: Context = None) -> None:
    await ctx.info(f"Deleting step {step_id} for '{agent_id}'")

    client = await get_agent_client()
    try:
        await client.surgery.delete_step(agent_id, step_id, conversation_id)
    except Exception as e:
        await ctx.error(str(e))
        raise


# -----------------------------------------------------------------------------
# Step Creation Tools for StorageModule
# -----------------------------------------------------------------------------

@mcp.tool(
    name="order_storage_module_step_retrieve_amr_step",
    description="Erzeuge einen Auslagerungsschritt zum menschen oder amr Step für das StorageModule. Das Lagert aus dem eigenen Lager ein Produkt aus an eine Uebergabestelle für den Mensch oder einen AMR. Übergib als Input Parameter eine ProduktID, einen ProduktTypen oder eine CarrierID",
    tags={"step", "storage", "create""order"}
)
async def create_storage_retrieve_from_hbw_to_amr_step(
        productid: str | None, product_type: str | None, carrier_id: str, ctx: Context = None) -> None:
    """Erzeugt einen RetrieveFromHbwToAMRStep für das StorageModule."""
    input_parameter = {}
    if productid is not None and productid != "":
        input_parameter["ProductID"] = productid

    if product_type is not None and product_type != "":
        input_parameter["ProductType"] = product_type

    if carrier_id is not None and carrier_id != "":
        input_parameter["CarrierID"] = carrier_id
    await ctx.log(f"sending Request with InputParameter {input_parameter}")
    step = StorageModule.RetrieveFromHbwToAMRStep(status=StepStateEnum.PLANNED, input_parameter=input_parameter)

    # Step model expected by client.order.order_step; pass-through as dict
    client = await get_agent_client()
    try:
        return await client.order.order_step("RH2", step)
    except Exception as e:
        await ctx.error(str(e))
        raise


# -----------------------------------------------------------------------------
# Prompt: Step-Workflow (Step erzeugen und bestellen)
# -----------------------------------------------------------------------------

@mcp.prompt(
    name="step_order_workflow",
    description="Anleitung: Wie ein Produktions-Step erzeugt und bestellt wird (z.B. für StorageModule)",
    tags={"production", "step", "workflow", "order"}
)
async def step_order_workflow_prompt(ctx: Context, step_type: str = "RetrieveFromHbwToAMRStep") -> str:
    prompt_content = f"""
# Produktions-Step bestellen: Schritt-für-Schritt-Anleitung

Um einen Produktions-Step (z.B. für das StorageModule) zu bestellen, gehe wie folgt vor:

1. Erzeuge den Step mit dem passenden Tool:
   - Beispiel für einen Storage-Retrieval-Step:
     ```python
     retrieve_to_amr_input = {{"ProductType": "Cab_A_Blue"}}
     step = await create_storage_retrieve_from_hbw_to_amr_step(status="PLANNED", input_parameter=retrieve_to_amr_input)
     ```

2. Bestelle den erzeugten Step mit dem order_step-Tool:
   - Beispiel:
     ```python
     result = await order_step(receiver_id="RH2", step=step, sender_id="P_sf_aas123")
     ```

Hinweise:
- Der Step muss immer zuerst erzeugt werden und dann als Argument an order_step übergeben werden.
- Für andere Step-Typen (z.B. StoreFromAMRToHbwStep) verwende das entsprechende Step-Erzeugungs-Tool.
- Die Parameter status und input_parameter müssen passend zum Step-Typ gewählt werden.

Unterstützte Step-Erzeugungs-Tools:
- create_storage_retrieve_from_hbw_to_amr_step
- create_storage_store_from_amr_to_hbw_step

"""
    await ctx.info("Step-Order-Workflow-Prompt generiert")
    return prompt_content


"""
AgentManagement MCP Server

A FastMCP server that exposes AgentManagement functionality as MCP tools, resources, and prompts.
This server allows LLMs to interact with the AgentManagement API through the Model Context Protocol.

Features:
- Agent lifecycle management (spawn, restart, kill agents)
- Agent registry operations (register, unregister, query agents)
- Surgery operations (modify agent behavior, step management)
- Order operations (production management, step ordering)
- Dynamic resource access for agent data and configurations
- Prompt templates for common agent operations
"""


# -----------------------------------------------------------------------------
# Additional Resources
# -----------------------------------------------------------------------------

@mcp.resource(name="system_configuration", description="Current system configuration and settings",
              uri="AgentManagement://system/config")
async def system_configuration(ctx: Context) -> str:
    await ctx.info("Fetching system configuration")
    try:
        client = await get_agent_client()
        config_data = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {"name": "AgentManagement MCP Server", "version": "1.0.0"},
            "api_configuration": {"base_url": getattr(client, '_base_url', BASE_URL), "authentication": "API Key"},
            "mcp_capabilities": {"tools": True, "resources": True, "prompts": True}
        }
        return json.dumps(config_data, indent=2)
    except Exception as e:
        await ctx.error(str(e))
        return json.dumps({"error": str(e)}, indent=2)


@mcp.resource(name="api_endpoints", description="Available API endpoints and their documentation",
              uri="agentmanagement://api/endpoints")
async def api_endpoints(ctx: Context) -> str:
    await ctx.info("Generating API endpoints documentation")
    endpoints_data = {"registry": ["GET /agents", "POST /agents", "DELETE /agents", "GET /agents/{id}"]}
    return json.dumps({"timestamp": datetime.now().isoformat(), "api_documentation": endpoints_data}, indent=2)


# -----------------------------------------------------------------------------
# End of inlined features
# -----------------------------------------------------------------------------


@mcp.prompt(
    name="troubleshoot_agent",
    description="Diagnostic prompt for troubleshooting agent issues",
    tags={"troubleshooting", "diagnostics", "support"}
)
async def troubleshoot_agent_prompt(
        ctx: Context,
        agent_id: Optional[str] = None,
        issue_type: Optional[str] = None
) -> str:
    prompt_content = f"""
# Agent Troubleshooting Guide
\n+Use this checklist to diagnose agent issues. Call the tools mentioned for each step.
\n+1) Verify registration
    - Tool: get_all_registered_agents
    - Look for: '{agent_id or '[agent-id]'}'
\n+2) Get configuration
    - Tool: get_agent_details(agent_id)
    - Check: agent_type (role), url, capabilities, neighbors, agents
\n+3) Test lifecycle
    - Try: spawn_agent(agent_id) / restart_agent(agent_id)
\n+4) Check communications
    - If agent uses Kafka: read_kafka_messages(topic_name) or send a test message
\n+5) Surgery operations (if running)
    - Use: repeat_action, terminate_action, previously_action as appropriate
\n+6) If registration or lifecycle fails: verify API connectivity to the registry (BASE_URL) and API key.
\n+{f'Suggested focus: {issue_type}' if issue_type else ''}
"""
    await ctx.info(f"Generated troubleshooting prompt{f' for agent {agent_id}' if agent_id else ''}")
    return prompt_content


@mcp.prompt(
    name="production_workflow",
    description="Guide for setting up and managing production workflows",
    tags={"production", "workflow", "automation"}
)
async def production_workflow_prompt(
        ctx: Context,
        workflow_type: Optional[str] = None,
        aas_id: Optional[str] = None
) -> str:
    prompt_content = f"""
# Production Workflow Management
\n+This guide helps plan and run a production workflow that uses role-aware agents.
\n+Steps:
1) Start production: call `start_production(aas_id)` or order specific steps with `order_step`.
2) Monitor: use `agent_registry_status` resource and Kafka topics (Step_Update, UpdateState) to track progress.

Example flow:
```

1. start_production("aas_id")
```
"""
    await ctx.info("Generated production workflow prompt")
    return prompt_content


if __name__ == "__main__":
    # Run the server with STDIO transport by default
    mcp.run()
