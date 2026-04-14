from __future__ import annotations

import asyncio
import contextlib
import traceback
from abc import ABC, abstractmethod
from asyncio import Task
from typing import Awaitable, Callable, Literal

from asyncua import Node, Server, uamethod
from asyncua.server.internal_session import InternalSession
from asyncua.ua import NodeId
from typing_extensions import override

from ..common.enums import SkillStates
from ..common.exceptions import PyUaRuntimeError
from .base_skill import BaseSkill
from .ua_fsm import UaFiniteStateMachine
from .user import INTERNAL_USER, User

TRIGGER = Literal[
    "halt", "halting_done", "reset", "resetting_done", "start", "starting_done", "suspend", "suspending_done"]
""" All state machine transition triggers for the skill state machine. """

class BaseSkillLogic(BaseSkill, ABC):
    """ Base class for all python-native skills (with state machine logic). """
    _machine: UaFiniteStateMachine
    tasks: dict[str, Task]
    """ Keeps track of tasks related to skill execution and their name. 
    These tasks will get canceled and emptied before  handle_halting() is called. """

    @override
    async def init(self, location: Node | None = None, existing_node: Node | None = None) -> None:
        await super().init(location, existing_node)
        from pyuaadapter.server import UaTypes
        from pyuaadapter.server.base_skill_finite import BaseSkillFinite

        self.tasks = {}

        self._machine = UaFiniteStateMachine(name=f"{self.name}_StateMachine",
                                             states=SkillStates,  # type: ignore
                                             initial=self._machinery_item.config.SKILLS_INITIAL_STATE,
                                             exclude_states=[] if isinstance(self, BaseSkillFinite)
                                                    else [SkillStates.Completed, SkillStates.Completing])
        await self._add_transitions()
        # ensure initialization comes first
        await self._machine.init(self.ua_state_machine, UaTypes.skill_state_machine_type)

    @override
    async def enable_historizing(self, server: Server, count: int = 1000) -> None:
        await super().enable_historizing(server, count)
        await self._machine.enable_historizing(server, count)

    async def _add_transitions(self) -> None:
        self._machine.add_transition(trigger="reset", source=["Halted", "Starting", "Suspended", "Completed"],
                                     dest="Resetting",
                                     conditions=[self._condition_access_allowed, self._condition_reset_allowed],
                                     after=self._after_resetting)
        self._machine.add_transition(trigger="resetting_done", source="Resetting", dest="Ready")

        self._machine.add_transition(trigger="halt", source=["Ready", "Running", "Suspended", "Starting", "Resetting",
                                                             "Suspending", "Completed"],
                                     dest="Halting", conditions=[self._condition_access_allowed],
                                     after=self._after_halting)
        self._machine.add_transition(trigger="halting_done", source="Halting", dest="Halted")

        self._machine.add_transition(trigger="start", source=["Ready", "Suspended"], dest="Starting",
                                     conditions=[self._condition_access_allowed, self._condition_startup_completed,
                                                self._condition_skill_ready, self._condition_dependencies_ready,
                                                self._condition_start_allowed],
                                     after=self._after_starting)
        self._machine.add_transition(trigger="starting_done", source="Starting", dest="Running",
                                     after=self._after_running)

        self._machine.add_transition(trigger="suspend", source="Running", dest="Suspending",
                                     conditions=[self._condition_access_allowed, self._condition_is_suspendable,
                                                self._condition_suspend_allowed],
                                     after=self._after_suspending)
        self._machine.add_transition(trigger="suspending_done", source="Suspending", dest="Suspended")

    async def _after_resetting(self, *args, **kwargs):
        """Is called by the finite state machine after the RESETTING state is entered."""
        await self._wrap_handle_method(self._handle_resetting, "resetting_done")

    async def _after_halting(self, *args, **kwargs):
        """Is called by the finite state machine after the HALTING state is entered."""
        # prevent infinite loop
        await self._wrap_handle_method(self._handle_halting, "halting_done", "halting_done",
                                       cancel_others=True)

    async def _after_starting(self, *args, **kwargs):
        """Is called by the finite state machine after the STARTING state is entered."""
        await self._wrap_handle_method(self._handle_starting, "starting_done")

    @abstractmethod
    async def _after_running(self, *args, **kwargs):
        raise NotImplementedError

    async def _after_suspending(self, *args, **kwargs):
        """Is called by the finite state machine after the SUSPENDING state is entered."""
        await self._wrap_handle_method(self._handle_suspending, "suspending_done")

    async def _wrap_handle_method(self, handle_method: Callable[[], Awaitable],
                                  success_trigger: TRIGGER | None,
                                  fail_trigger: TRIGGER = "halt",
                                  cancel_others: bool = False):
        self.logger.debug("_wrap_handle_method called", handle_method_name=handle_method.__name__,
                          success_trigger=success_trigger, fail_trigger=fail_trigger, cancel_others=cancel_others)

        if cancel_others:
            for task in self.tasks.values():
                if not task.cancelled() and not task.done():
                    self.logger.debug("Canceling task...", task_name=task.get_name())
                    task.cancel()
            self.tasks.clear()
        # else:
        #     with contextlib.suppress(ValueError):
        #         await asyncio.wait(self.tasks)  # tasks might be empty and raise a ValueError
        #         self.tasks.clear()

        async def _wrapped():
            try:
                await handle_method()
                if success_trigger is not None:
                    await self._machine.trigger(success_trigger, INTERNAL_USER)  # type: ignore
            except PyUaRuntimeError as err:
                await self._log_error(err.msg, code=err.error_code)
                await asyncio.shield(self._machine.trigger(fail_trigger, INTERNAL_USER))  # type: ignore
            except Exception as ex:
                self.logger.exception(ex)
                await self._log_error(f"Caught unhandled unknown exception: \n {traceback.format_exc()}")
                await asyncio.shield(self._machine.trigger(fail_trigger, INTERNAL_USER))  # type: ignore

        def _remove_task(finished_task: Task):
            with contextlib.suppress(KeyError):
                del self.tasks[finished_task.get_name()]
                self.logger.debug("Removed finished task", task_name=finished_task.get_name())

        task_name = f"Task_{self.name}_{handle_method.__name__}"
        with contextlib.suppress(KeyError):
            existing_task = self.tasks[task_name]
            if not existing_task.done() and not existing_task.cancelled():
                self.logger.debug("Task already exists, skipping task creation!", task_name=task_name)
                return

        task = asyncio.create_task(_wrapped(), name=task_name)
        self.tasks[task_name] = task
        task.add_done_callback(_remove_task)  # remove task when done


    ######################################
    # skill logic callbacks from the state machine

    async def _handle_resetting(self):
        """Is called to handle user-specific logic during RESETTING state. After this function is done,
        the skill will automatically advance to the READY state."""
        pass

    async def _handle_starting(self):
        """Is called to handle user-specific logic during the STARTING state. After this function is done,
        the skill will automatically advance to the RUNNING state."""
        pass

    @abstractmethod
    async def _handle_running(self):
        """Is called to handle user-specific logic during the RUNNING state. After this function is done,
         the skill will automatically advance to the COMPLETED state if it is finite, else HALTING state.

        Note: This continues to be executed during SUSPENDING and SUSPENDED states. If your skill supports
        suspending, you have to check in what state the skill is!"""
        raise NotImplementedError

    async def _handle_halting(self):
        """Is called to handle user-specific logic during the HALTING state. After this function is done,
        the skill will automatically advance to the HALTED state."""
        pass

    async def _handle_suspending(self):
        """Is called to handle user-specific logic during the SUSPENDING state. After this function is done,
        the skill will automatically advance to the SUSPENDED state."""
        pass  # Optional, only for suspendable skills

    ######################################
    # OPC-UA Callbacks

    @uamethod
    @override
    async def _ua_start(self, _parent: NodeId, session: InternalSession):
        self.logger.debug("Start method called", username=session.user.name)
        return await self._machine.try_trigger(session.user, 'start')

    @uamethod
    @override
    async def _ua_suspend(self, _parent: NodeId, session: InternalSession):
        self.logger.debug("Suspend method called", username=session.user.name)
        return await self._machine.try_trigger(session.user, 'suspend')

    @uamethod
    @override
    async def _ua_reset(self, _parent: NodeId, session: InternalSession):
        self.logger.debug("Reset method called", username=session.user.name)
        return await self._machine.try_trigger(session.user, 'reset')

    @uamethod
    @override
    async def _ua_halt(self, _parent: NodeId, session: InternalSession):
        self.logger.debug("Halt method called", username=session.user.name)
        return await self._machine.try_trigger(session.user, 'halt')

    ######################################
    # Internal skill interface (for composite skills)

    @override
    async def start(self, user: User | None = None) -> None:
        await self._machine.trigger('start', INTERNAL_USER)  # type: ignore

    @override
    async def suspend(self, user: User | None  = None) -> None:
        await self._machine.trigger('suspend', INTERNAL_USER)  # type: ignore

    @override
    async def reset(self, user: User | None  = None) -> None:
        await self._machine.trigger('reset', INTERNAL_USER)  # type: ignore

    @override
    async def halt(self, user: User | None  = None) -> None:
        await self._machine.trigger('halt', INTERNAL_USER)  # type: ignore

    @property
    def current_state(self) -> SkillStates:
        """ Current state of the skill. """
        return self._machine.state  # type: ignore
