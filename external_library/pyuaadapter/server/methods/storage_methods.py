from __future__ import annotations

import json
import typing

from asyncua import Node, ua
from asyncua.ua import UaError

from pyuaadapter.client.remote_variable import ua_value_to_simple
from pyuaadapter.server.base_method import BaseMethod

if typing.TYPE_CHECKING:
    from pyuaadapter.server.components.base_storage_slot import BaseStorageSlot
    from pyuaadapter.server.components.base_storage import BaseStorage


async def slots_to_json_str(slots: dict[str, "BaseStorageSlot"] | typing.Iterable["BaseStorageSlot"]) -> str:
    if isinstance(slots, dict):
        slots = slots.values()
    data = {}  # TODO typing for import and export
    for slot in slots:
        data[slot.name] = {
            "IsSlotEmpty": await slot.read_slot_empty(),
            "IsCarrierEmpty": await slot.read_carrier_empty(),
            "CarrierID": await slot.read_carrier_id(),
            "CarrierType": ua_value_to_simple(await slot.read_carrier_type()),
            "ProductID": await slot.read_product_id(),
            "ProductType": ua_value_to_simple(await slot.read_product_type())
            # State is not stored, will be set automatically based on above
        }
    return json.dumps(data)

class ExportStorageDataMethod(BaseMethod):
    _machinery_item: "BaseStorage"
    _result_json: Node

    def __init__(self, machinery_item: "BaseStorage"):
        super().__init__("ExportStorageData", machinery_item)
        from pyuaadapter.server.components.base_storage import BaseStorage

        if not isinstance(machinery_item, BaseStorage):
            raise RuntimeError(f"Given machinery item '{machinery_item.name}' is not a storage!")

    async def init(self, location = None, existing_node: Node | None = None):
        await super().init(location, existing_node)

        # add a result variables
        self._result_json = await self.add_result_variable("JsonExport", "", historize=True)

    async def execute_method(self):
        await self._result_json.write_value(await slots_to_json_str(self._machinery_item.slots))

class ImportStorageDataMethod(BaseMethod):
    _machinery_item: "BaseStorage"
    _param_json: Node

    def __init__(self, machinery_item: "BaseStorage"):
        super().__init__("ImportStorageData", machinery_item)
        from pyuaadapter.server.components.base_storage import BaseStorage

        if not isinstance(machinery_item, BaseStorage):
            raise RuntimeError(f"Given machinery item '{machinery_item.name}' is not a storage!")

    async def init(self, location = None, existing_node: Node = None):
        await super().init(location, existing_node)

        # add a result variables
        self._param_json = await self.add_parameter_variable("JsonImport", "", historize=True)

    async def execute_method(self):
        try:
            raw = await self._param_json.read_value()
            parsed_data: dict = json.loads(raw)

            for slot_name, slot_data in parsed_data.items():
                try:
                    slot = self._machinery_item.slots[slot_name]

                    slot_empty = slot_data.get("IsSlotEmpty", None)
                    carrier_empty = slot_data.get("IsCarrierEmpty", None)
                    if slot_empty is not None:
                        if slot_empty:
                            await slot.free_slot()
                            continue  # slot is empty, we are done, ignore potentially conflicting data
                        else:
                            # we need to write this explicitly in case nothing else is provided
                            await slot.ua_slot_empty.write_value(False)
                    if carrier_empty is not None:
                        if carrier_empty:
                            await slot.set_carrier_empty()
                        else:
                            # we need to write this explicitly in case nothing else is provided
                            await slot.ua_carrier_empty.write_value(False)

                    carrier_id = slot_data.get("CarrierID", None)
                    if carrier_id == "":  # we don't want to write empty strings, so set to None instead
                        carrier_id = None
                    carrier_type = slot_data.get("CarrierType", None)
                    product_id = slot_data.get("ProductID", None)
                    if product_id == "":  # we don't want to write empty strings, so set to None instead
                        product_id = None
                    product_type = slot_data.get("ProductType", None)

                    await slot.update_slot_content(
                        carrier_id=carrier_id,
                        carrier_type=carrier_type,
                        product_id=product_id,
                        product_type=product_type
                    )

                    await self._log_info(f"Successfully imported data for slot '{slot_name}'.")
                except KeyError:
                    await self._log_error(f"Could not find slot '{slot_name}' in storage!")
                except UaError:
                    await self._log_error(f"Could not import data for slot '{slot_name}'.")

            await self._param_json.write_value("")  # reset input only on successful import
        except Exception as ex:
            await self._log_error(f"Invalid JSON given: {ex}!")
            raise ua.UaStatusCodeError(ua.StatusCodes.BadSyntaxError)