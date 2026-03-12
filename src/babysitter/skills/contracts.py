
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future

#region Basic
@dataclass
class Context:
    """Mutual Context passed through skills"""
    input: Any = None
    prompt: Optional[str] = None
    timestamp: float = field(default_factory=lambda: time.time())

    # Results/States
    data: dict[str, Any] = field(default_factory=dict) # Skill can write/read from data

    # Events/Debugs
    events: list[str] = field(default_factory=list)

@dataclass
class SkillResult:
    """Result after a skill run
        updates: dict of context updates (skills can write to context.data or other fields as needed)
        output: optional main output of the skill (e.g. a description, an action, etc.) that can be stored under a specific key in context.data by the caller or left as is
        events: list of events/debug messages to log or process
    
    """
    
    updates: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    events: list[str] = field(default_factory=list)


class BaseSkill(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def should_run(self, context: Context) -> bool:
        pass

    @abstractmethod
    def run(self, context: Context) -> SkillResult:
        pass
#endregion


#region Skill Wrappers
class AsyncSkill:
    """Wrap a blocking skill so it runs in the background and does not block the caller.
    Stores latest completed result into context.data dictionary"""
    def __init__(self, 
                 inner_skill:BaseSkill, 
                 store_key:str,
                 max_inflight: int=1, 
                 executor:ThreadPoolExecutor |None =None):
        self.inner_skill = inner_skill
        self.name = f"async({inner_skill.name})"
        self.store_key = store_key
        self._lock = threading.Lock()
        # track inflight futures to enforce max_inflight limit, and to pull results back into context when done
        # inflight futures are what? The currently running background tasks that have not yet completed. We need to track them so we can:
        # 1. Enforce the max_inflight limit
        # 2. Pull results back into the context when they complete
        self._inflight : set[Future] = set() 
        self._executor = executor or ThreadPoolExecutor(max_workers=1)
        self._max_inflight = max_inflight

    def should_run(self, context: Context) -> bool:
        return self.inner_skill.should_run(context)

    def run(self, context: Context) -> SkillResult:
        with self._lock:
            done = {f for f in self._inflight if f.done()}
            self._inflight -= done # remove completed futures from inflight

            if len(self._inflight) >= self._max_inflight: 
                return SkillResult(events=[f"{self.name}: skipped (hit inflight max)"])

            snapshot = Context(input=context.input.copy() if hasattr(context.input, 'copy') else context.input,
                               prompt=context.prompt,
                               data=dict(context.data), # shallow copy
                               events=list(context.events))
            future = self._executor.submit(self.inner_skill.run, snapshot)
            self._inflight.add(future)
            return SkillResult(events=[f"{self.name}: started async task"])

    def pull_completed_into(self, context: Context):
        """Check for completed futures and pull their results into the context"""
        with self._lock:
            done = {f for f in self._inflight if f.done()}
            for f in done:
                self._inflight.remove(f)
                result = f.result()
                context.data.update(result.updates)
                context.events.extend(result.events)
                if result.output is not None:
                    context.data[self.store_key] = result.output
#endregion

#region Composite Skills
class SequenceSkill(BaseSkill):
    """Run skills in sequence, passing the same context through each"""
    def __init__(self, skills: list[Skill], name: Optional[str]=None):
        self.skills = skills
        if name is None:
            self.name = f"Sequence({', '.join(s.name for s in skills)})"
        else:
            self.name = name

    def should_run(self, context: Context) -> bool:
        return any(skill.should_run(context) for skill in self.skills)

    def run(self, context: Context) -> SkillResult:
        local_context = Context(input=context.input, prompt=context.prompt, data=dict(context.data), events=list(context.events))
        final_output = None
        for skill in self.skills:
            if skill.should_run(local_context):
                result = skill.run(local_context)
                local_context.data.update(result.updates)
                if result.output is not None:
                    local_context.data[skill.name] = result.output
                    final_output = result.output
                local_context.events.extend(result.events)
        return SkillResult(updates=local_context.data, output=final_output, events=local_context.events)
    
class ParallelSkill(BaseSkill):
    """Run skills in parallel, passing the same context to each. Waits for all to complete and aggregates results."""
    def __init__(self, skills: list[BaseSkill], name: Optional[str]=None):
        self.skills = skills
        if name is None:
            self.name = f"Parallel({', '.join(s.name for s in skills)})"
        else:
            self.name = name

    def should_run(self, context: Context) -> bool:
        return any(skill.should_run(context) for skill in self.skills)

    def run(self, context: Context) -> SkillResult:
        runnable_skills = [skill for skill in self.skills if skill.should_run(context)]
        if not runnable_skills:
            return SkillResult(events=[f"{self.name}: no skills to run"])
        
        with ThreadPoolExecutor(max_workers=len(runnable_skills)) as executor:
            futures = {executor.submit(skill.run, context): skill 
                       for skill in self.skills if skill.should_run(context)}
            updates = {}
            events = []
            outputs = {}
            for future, skill in futures.items():
                try:
                    result = future.result()
                except Exception as ex:
                    events.append(f"{skill.name}: failed with {ex}")
                    continue
                updates.update(result.updates)
                events.extend(result.events)
                if result.output is not None:
                    outputs[skill.name] = result.output
        return SkillResult(updates=updates, output=outputs, events=events)
    
from typing import Callable


class ConditionalSkill(BaseSkill):
    def __init__(
        self,
        inner_skill: BaseSkill,
        predicate: Callable[[Context], bool],
        name: str | None = None,
    ):
        super().__init__(name or f"conditional({inner_skill.name})")
        self.inner_skill = inner_skill
        self.predicate = predicate

    def should_run(self, context: Context) -> bool:
        return self.predicate(context) and self.inner_skill.should_run(context)

    def run(self, context: Context) -> SkillResult:
        return self.inner_skill.run(context)
#endregion

#region helpers
def clone_context(context: Context) -> Context:
    return Context(
        input=context.input.copy() if hasattr(context.input, "copy") else context.input,
        prompt=context.prompt,
        data=dict(context.data),
        events=list(context.events),
    )
#endregion







         
                
                 