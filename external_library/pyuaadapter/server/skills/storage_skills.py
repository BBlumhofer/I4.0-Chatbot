from __future__ import annotations

import asyncio
import random
import time
import typing
import uuid
from abc import ABC
from asyncio import Task

from asyncua import Node, ua
from typing_extensions import override

from pyuaadapter.common import NULL_NODE_ID
from pyuaadapter.common.enums import SkillStates, SlotStates
from pyuaadapter.common.exceptions import PyUaRuntimeError
from pyuaadapter.common.util import read_value
from pyuaadapter.server import UaTypes
from pyuaadapter.server.base_skill_finite import BaseSkillFinite
from pyuaadapter.server.resources.base_resource import BaseResource
from pyuaadapter.server.resources.carrier_resource import CarrierResource
from pyuaadapter.server.user import User

if typing.TYPE_CHECKING:
    from pyuaadapter.server.base_machinery_item import BaseMachineryItem
    from pyuaadapter.server.components.base_storage_slot import BaseStorageSlot
    from pyuaadapter.server.components.base_storage import BaseStorage


class BaseStorageSkill(BaseSkillFinite, ABC):
    _param_carrier_type: Node
    _param_product_type: Node
    _param_timeout: Node

    def __init__(self,
                 name: str,
                 machinery_item: "BaseMachineryItem",
                 *, carrier_resources: list[CarrierResource],
                 product_resources: list[BaseResource],
                 minimum_access_level: int = 2,  # no orchestrator
                 **kwargs):
        super().__init__(name=name, machinery_item=machinery_item, suspendable=False,
                         minimum_access_level=minimum_access_level, **kwargs)

        if len(product_resources) == 0:
            raise RuntimeError("No product resources given!")
        if len(carrier_resources) == 0:
            raise RuntimeError("No carrier resources given!")
        self._product_resources = product_resources
        self._carrier_resources = carrier_resources
        self._running_task: Task | None = None

    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        await super().init(location, existing_node)

        self._param_product_type = await self.add_parameter_variable("ProductType", NULL_NODE_ID)
        for resource in self._product_resources:  # setup references so clients know which node IDs are accepted
            await self._param_product_type.add_reference(target=resource.ua_node, reftype=UaTypes.utilize_ref)

        self._param_carrier_type = await self.add_parameter_variable("CarrierType", NULL_NODE_ID)
        for resource in self._carrier_resources:  # setup references so clients know which node IDs are accepted
            await self._param_carrier_type.add_reference(target=resource.ua_node, reftype=UaTypes.utilize_ref)


        self._param_timeout = await self.add_parameter_variable(
            "Timeout", StoreSkill.TIMEOUT, unit="s", _range=(0.1, 300))

    @override
    async def _condition_start_allowed(self, _user: User) -> bool:
        """ Is called when trying to start the skill, make sure our product type parameter is valid. """
        param_product_type_node_id = await self._param_product_type.read_value()
        param_carrier_type_node_id = await self._param_carrier_type.read_value()

        product_type_set = False
        carrier_type_set = False

        # Check our parameter product type
        for resource in self._product_resources:
            if resource.ua_node.nodeid == param_product_type_node_id:
                product_type_set = True
                break
        if not product_type_set and param_product_type_node_id != NULL_NODE_ID:
            await self._log_error(f"Given Product Type NodeID '{param_product_type_node_id}' is invalid!")

        # Check our parameter carrier type
        for resource in self._carrier_resources:
            if resource.ua_node.nodeid == param_carrier_type_node_id:
                carrier_type_set = True
                break
        if not carrier_type_set and param_carrier_type_node_id != NULL_NODE_ID:
            await self._log_error(f"Given Carrier Type NodeID '{param_carrier_type_node_id}' is invalid!")

        # at least one of our parameters must be set
        if product_type_set or carrier_type_set:
            return True

        await self._log_error("At least set one parameter to a non null value!")
        raise ua.UaStatusCodeError(ua.StatusCodes.BadOutOfRange)

    @override
    async def _handle_resetting(self):
        await self._param_product_type.write_value(NULL_NODE_ID)
        await self._param_carrier_type.write_value(NULL_NODE_ID)


class StoreSkill(BaseStorageSkill):
    """
    This skill is meant to provide a way to specify the product type when storing new carriers into slots.
    It monitors the associated storage slot `slot_empty` monitoring variable until in is False, in which case the
    given parameters are written to the slot and the skill is completed. If the parametrized timeout is reached, the
    skill will halt instead.
    """

    NAME: str = "Store"
    TIMEOUT = 60.0
    machinery_item: "BaseStorageSlot"

    # _monitoring_remaining_time: Node

    def __init__(self, machinery_item: "BaseStorageSlot",
                 *, carrier_resources: list[CarrierResource],
                 product_resources: list[BaseResource],
                 minimum_access_level: int = 2,
                 **kwargs):
        super().__init__(name=StoreSkill.NAME, machinery_item=machinery_item, carrier_resources=carrier_resources,
                         product_resources=product_resources, minimum_access_level=minimum_access_level, **kwargs)

        from pyuaadapter.server.components.base_storage_slot import BaseStorageSlot

        if not isinstance(machinery_item, BaseStorageSlot):
            raise RuntimeError(f"Given machinery item '{machinery_item.name}' is not a storage slot!")

    @property
    def slot(self) -> "BaseStorageSlot":
        return self.machinery_item

    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        await super().init(location, existing_node)

        # self._monitoring_remaining_time = await self.add_monitoring_variable("RemainingTime", StoreSkill.TIMEOUT)

    @override
    async def _handle_halting(self):
        await self.slot.update_slot_content()

    @override
    async def _handle_running(self):
        # define logic that is executed in the RUNNING state

        # read our parameters. Note that they are changeable while the skill is running
        carrier_type = await read_value(self._param_carrier_type)
        product_type = await read_value(self._param_product_type)
        timeout = await read_value(self._param_timeout)

        # mark our slot as being loaded
        await self.slot.set_current_state(SlotStates.GetsLoaded)

        start_time = time.monotonic()
        while True:
            if not await self.slot.read_slot_empty():  # something is in our monitored slot
                await self.slot.update_slot_content(
                    carrier_type=carrier_type,
                    product_type=product_type)
                break  # Note: the update_slot_content also updates the slot state

            remaining_time = timeout - (time.monotonic() - start_time)
            if remaining_time > 0:
                # TODO decide to re-enable it with less updates per second or to remove it
                # await self._monitoring_remaining_time.write_value(remaining_time)
                await asyncio.sleep(.1)
            else:
                # await self._monitoring_remaining_time.write_value(0.0)
                raise PyUaRuntimeError("Timeout")


class StoreAllEmptySkill(BaseStorageSkill):
    """
    This skill is meant to provide an easy way to specify the product type when storing multiple new carriers into slots.
    It utilizes the `StoreSkill` for each empty slot of the given storage machinery item.
    """

    NAME: str = "StoreAllEmpty"
    TIMEOUT = 60.0
    machinery_item: "BaseStorage"

    _monitoring_total: Node
    _monitoring_remaining: Node
    _result_successes: Node
    _result_failures: Node

    def __init__(self, machinery_item: "BaseStorage",
                 *, carrier_resources: list[CarrierResource],
                 product_resources: list[BaseResource],
                 minimum_access_level: int = 2,
                 **kwargs):
        super().__init__(name=StoreAllEmptySkill.NAME, machinery_item=machinery_item,
                         carrier_resources=carrier_resources, product_resources=product_resources,
                         minimum_access_level=minimum_access_level, **kwargs)

        from pyuaadapter.server.components.base_storage import BaseStorage

        if not isinstance(machinery_item, BaseStorage):
            raise RuntimeError(f"Given machinery item '{machinery_item.name}' is not a storage!")

        self.skills: list[BaseSkillFinite] = []
        """ list of skills that we are starting and monitoring. """

    @property
    def storage(self) -> "BaseStorage":
        return self.machinery_item

    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        await super().init(location, existing_node)

        self._monitoring_total = await self.add_monitoring_variable("Total", 0)
        self._monitoring_remaining = await self.add_monitoring_variable("Remaining", 0)

        self._result_successes = await self.add_result_variable("Successes", 0)
        self._result_failures = await self.add_result_variable("Failures", 0)

        for slot in self.storage.slots.values():
            try:
                await self.add_dependency(slot.skills[StoreSkill.NAME])
            except KeyError:
                pass  # Optional

    @override
    async def _condition_dependencies_ready(self, _) -> bool:
        return True  # we do not care about the status of the other store skills, we manage them directly

    @override
    async def _handle_resetting(self):
        await super()._handle_resetting()
        self.skills.clear()
        await self._monitoring_total.write_value(0)
        await self._monitoring_remaining.write_value(0)
        await self._result_successes.write_value(0)
        await self._result_failures.write_value(0)

    @override
    async def _handle_halting(self):
        await self._halt_running_called_skills()

    @override
    async def _handle_running(self):
        # define logic that is executed in the RUNNING state

        # read our parameters. Note that they are changeable while the skill is running
        carrier_type = await read_value(self._param_carrier_type)
        product_type = await read_value(self._param_product_type)
        timeout = await read_value(self._param_timeout)

        for slot in self.storage.slots.values():
            if not await slot.read_slot_empty():
                continue  # is not empty, so we cannot fill it with this skill
            try:
                skill = typing.cast(BaseSkillFinite, slot.skills[StoreSkill.NAME])
                if skill.current_state == SkillStates.Running:
                    continue  # is already in use, cannot be used by this skill
                self.skills.append(skill)
            except KeyError:
                await self._log_warning(f"Slot '{slot.name}' has no {StoreSkill.NAME} skill!")

        await self._monitoring_total.write_value(len(self.skills))

        # Try resetting all collected skills
        for skill in self.skills:
            try:
                await skill.reset()
            except:
                pass  # Skills that are already ready will fail here

        await self._log_info(f"Trying to start {len(self.skills)} store skills...")

        # Start all collected skills
        for skill in self.skills:
            try:
                parameters = {"CarrierType": carrier_type, "ProductType": product_type, "Timeout": timeout}
                await self.call_other_finite_skill(skill, parameters=parameters, wait_for_completion=False,
                                                   reset_after_completion=False)
            except ua.UaStatusCodeError:
                raise PyUaRuntimeError("Could not start dependent skill, stopping!") from None


        # Wait until all collected skills are done, whether successful (Completed) or unsuccessful (Halted)
        while True:
            skill_states = [skill.current_state for skill in self.skills]
            no_of_completed = skill_states.count(SkillStates.Completed)
            no_of_halted = skill_states.count(SkillStates.Halted)

            remaining = len(self.skills) - (no_of_halted + no_of_completed)
            await self._monitoring_remaining.write_value(remaining)
            if remaining <= 0:
                break

            await asyncio.sleep(0.1)

        await self._result_successes.write_value(no_of_completed)
        await self._result_failures.write_value(no_of_halted)

VALID_COMBINATIONS = {
    "WST_A" : ["Cab_Chassis", "Semitrailer_Chassis", "Semitrailer_Truck", "Semitrailer"],
    "WST_B" : ["Cab_A_Blue", "Cab_B_Red", "Trailer_Body_Blue", "Trailer_Body_White",
               "Trailer_Body_White_Penholder"],
    "WST_C" : ["Truck"],
    "WST_G" : ["Lid_A_Black", "Lid_A_White", "Lid_A_Blue", "Lid_A_Gray"]
}
""" Mapping of carrier and valid products. """

async def update_slot_random(
        slot: BaseStorageSlot,
        *,
        resources: dict[str, BaseResource],
        carrier_id_count: int = 0,
        chance_new_carrier: float = 0.4,
        chance_new_product: float = 0.5,
        chance_free: float = 0.1) -> None:
    """ Update a single slot randomly.

        :param slot: Storage slot instance to update randomly.
        :param resources: Which resources to use
        :param carrier_id_count: Carrier ID count, is part of the carrier ID according to a schema.
        :param chance_new_carrier: Percent chance to set a new carrier to a slot (0.0-1.0).
        :param chance_new_product: Percent chance to set a new product to a slot (0.0-1.0).
            Only used when a new carrier was set for the slot.
        :param chance_free: Percent chance to free a slot (0.0-1.0)
    """
    if random.random() < chance_new_carrier:
        carrier_type_str = random.choice(list(VALID_COMBINATIONS.keys()))
        carrier_type = resources[carrier_type_str].ua_node.nodeid
        carrier_id = f"{carrier_type_str}_{carrier_id_count}"  # carrier ID naming schema

        if random.random() < chance_new_product:
            product_id = str(uuid.uuid4()) if random.random() > 0.5 else ""
            product_type_str = random.choice(VALID_COMBINATIONS[carrier_type_str])
            product_type = resources[product_type_str].ua_node.nodeid
        else:
            await slot.set_carrier_empty()
            product_id = None  # won't be updated
            product_type = None  # won't be updated

        await slot.update_slot_content(
            carrier_id=carrier_id, carrier_type=carrier_type, product_id=product_id, product_type=product_type
        )
    elif random.random() < chance_free:
        await slot.free_slot()
    # else: nothing to do

async def update_storage_random(
    storage: BaseStorage,
    *,
    carrier_id_start: int = 0,
    chance_new_carrier: float = 0.4,
    chance_new_product: float = 0.5,
    chance_free: float = 0.1
) -> None:
    """
    Iterate through all slots and update them randomly based on configured chances.

    The chance for a slot staying as-is is 1 - chances for a new carrier and free slot.

    :param storage: Storage instance to update randomly.
    :param carrier_id_start: Carrier ID start number, will be increased by one for each slot.
    :param chance_new_carrier: Percent chance to set a new carrier to a slot (0.0-1.0).
    :param chance_new_product: Percent chance to set a new product to a slot (0.0-1.0).
        Only used when a new carrier was set for the slot.
    :param chance_free: Percent chance to free a slot (0.0-1.0)
    """
    resources = storage.root_parent.resources
    carrier_id_count = carrier_id_start
    for slot in storage.slots.values():
        await update_slot_random(slot,
                                 resources=resources,
                                 carrier_id_count=carrier_id_count,
                                 chance_new_carrier=chance_new_carrier,
                                 chance_new_product=chance_new_product,
                                 chance_free=chance_free)
        carrier_id_count += 1

