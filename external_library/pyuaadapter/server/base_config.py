from __future__ import annotations

import logging
from abc import ABC

from pyuaadapter.common import LogFormat
from pyuaadapter.common.enums import MachineryItemStates, SkillStates
from pyuaadapter.server.user import User


class BaseConfig(ABC):
    """ Contains default configuration options. """
    MODULE = None  # TODO remove
    DEBUG = True
    ENCRYPTION = False
    ENCRYPTION_CERTIFICATE_PATH = "server_certificate.der"
    ENCRYPTION_PRIVATE_KEY = "server_private_key.pem"

    # Logging stuff
    LOG_FORMAT = LogFormat.KeyValue  # or JSON
    """ Minimum logging level, lower levels will always be filtered. """
    LOG_LEVELS = {
        "sf.server.Server": logging.INFO,
        "sf.server.Module": logging.WARNING,
        "sf.server.Component": logging.WARNING,
        "sf.server.Port": logging.WARNING,
        "sf.server.Axis": logging.WARNING,
        "sf.server.SafetyState": logging.WARNING,
        "sf.server.Gripper": logging.WARNING,
        "sf.server.PowerTrain": logging.WARNING,
        "sf.server.Controller": logging.WARNING,
        "sf.server.Software": logging.WARNING,
        "sf.server.TaskControl": logging.WARNING,
        "sf.server.Motor": logging.WARNING,
        "sf.server.MotionDevice": logging.WARNING,
        "sf.server.MotionDeviceSystem": logging.WARNING,
        "sf.server.Laser": logging.WARNING,
        "sf.server.Resource": logging.WARNING,
        "sf.server.Storage": logging.WARNING,
        "sf.server.StorageSlot": logging.WARNING,
        "sf.server.Safety": logging.WARNING,
        "sf.server.Shuttle": logging.WARNING,
        "sf.server.Skill": logging.WARNING,
        "sf.server.AccessControl": logging.INFO,
        "sf.server.UaFiniteStateMachine": logging.ERROR,
        "asyncua": logging.ERROR,
    }

    HISTORY = "Memory"  # valid options: Memory or SQLite

    # OPC-UA
    NAMESPACE_URI = "http://smartfactory.de/UA/MachineSet"
    SERVER_NAME = "UNNAMED OPC-UA Adapter"
    ENDPOINT_ADDRESS = "opc.tcp://localhost:4843/server"
    REGISTER_AT_DISCOVERY_SERVER = False  # register at discovery service, only required for production
    DISCOVERY_SERVER_ADDRESS = "opc.tcp://172.17.10.20:4840"

    # Access Control
    USERS = [
        User(name="visitor",
             password=b'\x13\xd5\x16\x08]4\x94?\xf9\xb5Gd\xfc2\xaf^K\x91\xff\xfd\xed\xcd`\xe4sA\xd4Y\xab\xb2\xce8',
             priority=0, access=0, allow_multiple=True),
        User(name="orchestrator",
             password=b'\xf0v{\x9d;\x84gx\xd29\xd9 \xd0l\x80h\xda\x9b\xcf\x97\xdf\xe4\x0c\xa3\x90\xe2\x03\x8b\xd4J)\xea',
             priority=1, access=1, allow_multiple=False),
        User(name="operator",
             password=b'J\xbbW\x1ca\xca\x96\xa7\x8f\xa7\xe3\xd9\xf6\xc0\xfb\xbc\xaf\xc5I\x1fk5:\xc2q>X?Y5S\xfb',
             priority=2, access=2, allow_multiple=False),
        User(name="remote",  # remote operator, same password etc. as operator
             password=b'J\xbbW\x1ca\xca\x96\xa7\x8f\xa7\xe3\xd9\xf6\xc0\xfb\xbc\xaf\xc5I\x1fk5:\xc2q>X?Y5S\xfb',
             priority=2, access=2, allow_multiple=False),
        User(name="watchdog",  # watchdog for PSB access to stop skills when anomalies are detected
             password=b'J\xbbW\x1ca\xca\x96\xa7\x8f\xa7\xe3\xd9\xf6\xc0\xfb\xbc\xaf\xc5I\x1fk5:\xc2q>X?Y5S\xfb',
             priority=4, access=2, allow_multiple=False),
        User(name="developer",
             password=b"WIa\xe6\xe2k\xf7\xbe\xf9Q\xdcd>\x9c\xbc\xebJ\xb8\xf7K0U1\xfbn\xff\xab'\xaf\x08\x8b[",
             priority=10, access=3, allow_multiple=False)
    ]
    MINIMUM_ACCESS = 1
    ALLOW_RECONNECTION_FROM_SAME_HOST = True

    # Misc
    MODULE_INITIAL_STATE = MachineryItemStates.OutOfService  # TODO remove
    SKILLS_INITIAL_STATE = SkillStates.Halted  # TODO remove
    GATE_INITIAL_STATE = SkillStates.Halted  # TODO remove

    # Kafka Plugin related
    KAFKA_ENABLE = False
    KAFKA_BOOTSTRAP_SERVER = ""  # IP:Port of kafka bootstrap server
    KAFKA_SCHEMA_REGISTRY = ""  # URL (ie. http://<IP>:<Port>) of kafka schema registry
    KAFKA_SKILL_SCHEMA = None  # optional, path to custom skill schema
    KAKFA_MODULE_SCHEMA = None  # optional, path to custom module schema
    KAFKA_TOPIC_PREFIX = ""  # topics will be prefixed using this string, should be at least the module name
    KAFKA_TOPIC_SUFFIX = ""  # topics will be suffixed using this string
    KAFKA_BLACKLIST_SKILLS: list[str] = []  # names of skills not to publish to kafka

    CSV_ENABLE = False
    CSV_SKILL_FILENAME = "skill_data.csv"
    CSV_MODULE_FILENAME = "module_data.csv"

    # API URL for mapping the RFID number into a human-readable tag name.
    # should contain the same information as the backup mapping below. might be more up-to-date.
    PORT_API = "https://port-registry.services.plant.smartfactory.de/gates/rfid_tags/{}/name"
    PORT_API_ENABLE = False  # whether above API should be used. Fallback is always the local mapping below.

    # contains the local mapping from RFID number to human-readable tag name.
    RFID_NEIGHBOUR_MAPPING = {
        8: "Processing.Laser_P25_Gate1",
        25: "Transport.Rail_T1_Gate5",
        31: "Processing.StorageAndAssembly_P1_Gate1",
        35: "Delivery.Human_H2_Gate1",
        39: "Processing.CollaborativeAssembly_P17_Gate1",
        40: "Transport.Trak_T2_Gate1",
        41: "Processing.Data_Refueling_P4_Gate1",
        57: "QualityControl.SmartFactory_P3_Gate1",
        67: "Transport.Trak_T2_Gate2",
        68: "Processing.Roadshow_P18_Gate3",
        73: "Transport.Rail_T1_Gate2",
        80: "Transport.Rail_T1_Gate4",
        84: "Processing.Storage_P10_Gate1",
        91: "Processing.Roadshow_P18_Gate4",
        92: "Processing.Roadshow_P18_Gate3",
        93: "Processing.Roadshow_P18_Gate2",
        104: "Processing.ToolChangeModule_P11_Gate1",
        109: "Transport.Trak_T2_Gate4",
        123: "Transport.Trak_T2_Gate3",
        136: "Processing.Roadshow_P18_Gate1",
        143: "Processing.Storage_P24_Gate1",
        153: "Processing.Wedding_P13_Gate1",
        173: "Processing.3d_Printer_P15_Gate1",
        174: "Processing.Printer_P7_Gate1",
        177: "Processing.BinPicking_P26_Gate0",
        186: "Processing.HandAssembly_P9_Gate1",
        187: "Processing.UR5_P6_Gate6",
        188: "Processing.Harting_BlindModul_P8_Gate1",
        198: "Delivery.Human_H1_Gate1",
        201: "Processing.SubmoduleAtPort4_P12_Gate1",
        232: "QualityControl.Harting_P2_Gate1",
        239: "Transport.Rail_T1_Gate1",
        242: "Transport.Trak_T2_Gate4",
        244: "Transport.Trak_T2_Gate5",
        251: "Transport.Trak_T2_Gate3",
        324: "Transport.Rail_T1_Gate3",
    }
