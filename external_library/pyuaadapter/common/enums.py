from enum import IntEnum


class SkillStates(IntEnum):
    """Represents the skill states including the correct state number according to the skill node-set specification."""
    Halted = 11
    """State indicating that the skill is halted (=stopped). To leave this state, the skill needs to be reset.
    Note: Skills can halt for various reasons, e.g. internal failures, external safety trigger, etc."""
    Ready = 12
    """State indicating that the skill is ready to be started."""
    Running = 13
    """State indicating that the skill is running."""
    Suspended = 14
    """State indicating that the skill is suspended."""
    Completed = 15
    """State indicating that the skill is completed. 
    Only used for finite skills, because continuous skills do not complete."""

    Starting = 16
    """Intermediate state leading to Running on success or Halting on failure."""
    Halting = 17
    """Intermediate state always leading to Halted."""
    Completing = 18
    """Intermediate state leading to Completed on success or Halting on failure.
    Only used for finite skills, because continuous skills do not complete."""
    Resetting = 19
    """Intermediate state leading to Ready on success or Halting on failure."""
    Suspending = 20
    """Intermediate state leading to Suspended on success or Halting on failure."""


class MachineryItemStates(IntEnum):
    """ Represents the machinery states.

    Documentation from https://reference.opcfoundation.org/Machinery/v103/docs/12.2"""
    NotAvailable = 0
    """The machine is not available and does not perform any activity (e.g., switched off, in energy saving mode)"""
    OutOfService = 1
    """The machine is not functional and does not perform any activity (e.g., error, blocked)"""
    NotExecuting = 2
    """The machine is available & functional and does not perform any activity. 
    It waits for an action from outside to start or restart an activity."""
    Executing = 3
    """The machine is available & functional and is actively performing an activity (pursues a purpose)."""


class MachineryOperationModes(IntEnum):
    """ Represents the machinery operation mode.

    Documentation from https://reference.opcfoundation.org/Machinery/v103/docs/13.2 """
    None_ = 0
    """No machinery operation mode available."""
    Maintenance = 1
    """Mode with the intention to carry out maintenance or servicing activities."""
    Setup = 2
    """Mode with the intention to carry out setup, preparation or postprocessing activities of a production process."""
    Processing = 3
    """Mode with the intention to carry out the value adding activities."""

class MotionDeviceCategory(IntEnum):
    Other = 0
    Articulated_Robot = 1
    Scara_Robot = 2
    Cartesian_Robot = 3
    Spherical_Robot = 4
    Parallel_Robot = 5
    Cylindrical_Robot = 6


class MotionProfile(IntEnum):
    Other = 0
    Rotary = 1
    Rotary_Endless = 2
    Linear = 3
    Linear_Endless = 4


class GripPointType(IntEnum):
    Parallel = 0
    Vacuum_Based = 1
    Multi_Finger = 2


class LaserSystemStates(IntEnum):
    Off = 0
    EnergySaving = 1
    Idle = 2
    SetUp = 3
    LaserReady = 4
    Maintenance = 5
    Error = 6
    LaserOn = 7


class LaserStates(IntEnum):
    Undefined = 0
    Ready = 1
    Active = 2
    Error = 3



class SlotStates(IntEnum):
    """ Represents the state of a single storage slot. """
    Uninitialized = 0
    """ Slot is not initialized. This is an invalid state!"""
    Empty = 1
    """ No Carrier detected. """
    LoadedUnknown = 2
    """ Carrier detected, Carrier ID and Carrier type unknown. """
    LoadedKnown = 3
    """ Carrier detected AND [Carrier ID OR Carrier type] known. """
    GetsLoaded = 4
    """ Slot is being targeted for loading by a skill. """
    GetsEmptied = 5
    """ Slot is being targeted for unloading by a skill. """

