class PyUaAdapterError(Exception):
    """ Base for all PyUaAdapter related exceptions. """
    pass


class SkillHaltedError(PyUaAdapterError):
    """ Is raised when a skill other than the own skill is halted. (i.e. when calling other skills) """
    pass

class UnsupportedSkillNodeSetError(PyUaAdapterError):
    """ Is raised when the client fails to browse correctly through the remote OPC UA server."""
    pass

class SkillNotSuspendableError(PyUaAdapterError):
    """Is raised when failing to suspend a skill that is not suspendable."""
    pass

class PyUaRuntimeError(PyUaAdapterError):
    """Is raised by user code when something goes wrong. Use this exception instead of the build-in RuntimeError."""
    def __init__(self, msg: str, error_code: str = ""):
        self.msg = msg
        self.error_code = error_code
