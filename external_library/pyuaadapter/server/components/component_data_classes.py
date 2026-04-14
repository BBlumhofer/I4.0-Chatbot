
from dataclasses import dataclass
from typing import List, Type, Dict, Any

from pyuaadapter.common.enums import MotionProfile, GripPointType, MotionDeviceCategory
from pyuaadapter.server.components.robotic_spec.base_axis import BaseAxis
from pyuaadapter.server.components.base_gripper import BaseGripper
from pyuaadapter.server.components.robotic_spec.base_power_train import BaseMotor, BasePowerTrain
from pyuaadapter.server.components.robotic_spec.base_controller import BaseTaskControl

@dataclass
class Axis:

    """ Data class containing values of axis """
    motion_profile: MotionProfile

    load: float = 0
    load_unit: str = "kg"
    instantiate_load: bool = False

    instantiate_speed: bool = False
    speed_unit: str = "m/s"

    instantiate_acceleration: bool = False
    acceleration_unit: str = "m/s²"

    position_unit: str = "mm"

    # sf specific
    instantiate_carrier_id: bool = False
    instantiate_product_id: bool = False
    instantiate_is_carrier_empty: bool = False
    instantiate_is_axis_empty: bool = False

    component_type: Type[BaseAxis] = BaseAxis
    component_kwargs: Dict[str, Any] = None


@dataclass
class Gripper:

    """ Data class containing values of gripper """
    grip_point_type: GripPointType
    instantiate_part_gripped: bool = False

    component_type = BaseGripper


@dataclass
class Motor:

    """ Data class containing values of motor """
    motor_temperature_unit: str = "°C"

    component_type: Type[BaseMotor] = BaseMotor
    component_kwargs: Dict[str, Any] = None


@dataclass
class PowerTrain:

    """ Data class containing values of power train """
    motors: List[Motor] = None

    component_type: Type[BasePowerTrain] = BasePowerTrain
    component_kwargs: Dict[str, Any] = None


@dataclass
class TaskControl:
    """ Data class containing values of task control """

    instantiate_execution_mode: bool = False

    component_type: Type[BaseTaskControl] = BaseTaskControl
    component_kwargs: Dict[str, Any] = None

@dataclass
class Controller:
    """ Data class containing values of controller """

    instantiate_parameter_set: bool = False

    cabinet_fan_speed_unit: str = "m/s"
    instantiate_cabinet_fan_speed: bool = False

    cpu_fan_speed_unit: str = "m/s"
    instantiate_cpu_fan_speed: bool = False

    input_voltage_unit: str = "V"
    instantiate_input_voltage: bool = False

    startup_time: float = 0
    instantiate_startup_time: bool = False

    temperature_unit: str = "°C"
    instantiate_temperature: bool = False

    total_energy_consumption_unit: str = "W·h"
    instantiate_total_energy_consumption: bool = False

    instantiate_total_power_on_time: bool = False

    instantiate_ups_state: bool = False

    softwares: int = 0
    task_controls: List[TaskControl] = None


@dataclass
class Roboter:
    """ Data class containing values of roboter """
    motion_device_category: MotionDeviceCategory

    load: float = 798
    load_unit: str = "g"
    instantiate_load: bool = False

    axes: List[Axis] = None
    power_trains: List[PowerTrain] = None
    grippers: List[Gripper] = None

    instantiate_in_control: bool = False
    instantiate_on_path: bool = False


@dataclass
class Safety:
    """ Data class containing values of safety """

    instantiate_housing: bool = False
    instantiate_environment: bool = False
    instantiate_sto: bool = False



@dataclass
class Shuttle:
    """ Data class containing values of shuttle """
    load_capacity: float = 0
    load_cap_unit: str = "kg"

    velocity_unit: str = "m/s"
    position_unit: str = "mm"
    acceleration_unit: str = "m/s²"
    target_pos_unit: str = "m/s²"

    instantiate_velocity: bool = False
    instantiate_acceleration: bool = False
    instantiate_target_pos: bool = False
    instantiate_current_port: bool = False
    instantiate_target_port: bool = False

    instantiate_shuttle_locked: bool = False
    instantiate_product_type: bool = False
    instantiate_load_capacity: bool = False


@dataclass(frozen=True)
class AcPe:
    """ Data class for AC values for 3 phases to neutral, see https://reference.opcfoundation.org/ECM/v100/docs/9.3 """
    L1: float
    L2: float
    L3: float


@dataclass(frozen=True)
class AcPp:
    """ Data class for AC values for potential difference of three phases,
    see https://reference.opcfoundation.org/ECM/v100/docs/9.4 """
    L1L2: float
    L2L3: float
    L3L1: float





