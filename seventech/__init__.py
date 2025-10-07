"""SevenTech Automation Platform.

A deterministic browser automation platform that separates AI mapping from execution.

Components:
- Mapper: Maps objectives using LLM (one-time)
- Planner: Creates deterministic plans
- Executor: Executes plans without LLM (repeatable)
- Storage: Persists plans and results
- API: REST interface for automation
"""

from seventech.executor.service import Executor
from seventech.executor.views import ExecutePlanRequest, ExecutorConfig
from seventech.mapper.interactive import InteractiveMapper
from seventech.mapper.service import Mapper
from seventech.mapper.session import InputRequest, MapperSession, SessionStatus
from seventech.mapper.views import MapObjectiveRequest, MapperConfig
from seventech.planner.service import Planner
from seventech.shared_views import (
	ActionType,
	Artifact,
	ArtifactType,
	ExecutionResult,
	ExecutionStatus,
	MapperResult,
	Plan,
	PlanMetadata,
	PlanStep,
)
from seventech.storage.service import Storage

__version__ = '1.0.0'

__all__ = [
	# Services
	'Mapper',
	'InteractiveMapper',
	'Planner',
	'Executor',
	'Storage',
	# Mapper
	'MapperConfig',
	'MapObjectiveRequest',
	'MapperResult',
	# Interactive Mapping
	'MapperSession',
	'SessionStatus',
	'InputRequest',
	# Executor
	'ExecutorConfig',
	'ExecutePlanRequest',
	'ExecutionResult',
	'ExecutionStatus',
	# Plan models
	'Plan',
	'PlanMetadata',
	'PlanStep',
	'ActionType',
	# Artifacts
	'Artifact',
	'ArtifactType',
]
