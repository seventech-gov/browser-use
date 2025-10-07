"""Shared data models for SevenTech automation platform."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from uuid_extensions import uuid7str


class ActionType(str, Enum):
	"""Types of actions that can be executed in a plan."""

	GOTO = 'goto'
	CLICK = 'click'
	INPUT = 'input'
	SELECT = 'select'
	SCROLL = 'scroll'
	WAIT = 'wait'
	EXTRACT = 'extract'
	SCREENSHOT = 'screenshot'
	DOWNLOAD = 'download'
	UPLOAD = 'upload'


class PlanStep(BaseModel):
	"""A single step in an execution plan."""

	model_config = ConfigDict(extra='forbid')

	sequence_id: int = Field(description='Order of execution')
	action: ActionType = Field(description='Type of action to perform')
	params: dict[str, Any] = Field(default_factory=dict, description='Action parameters')
	description: str = Field(default='', description='Human-readable description of step')

	# Optional: store original browser-use action for reference
	original_action: str | None = Field(default=None, description='Original action name from browser-use')
	original_params: dict[str, Any] | None = Field(default=None, description='Original parameters from browser-use')


class PlanMetadata(BaseModel):
	"""Metadata about an objective plan."""

	model_config = ConfigDict(extra='forbid')

	plan_id: str = Field(default_factory=uuid7str, description='Unique identifier for this plan')
	name: str = Field(description='Human-readable name for the objective')
	description: str = Field(description='Detailed description of what this plan achieves')
	url: str | None = Field(default=None, description='Starting URL for this plan')
	required_params: list[str] = Field(default_factory=list, description='Parameter names required at execution time')
	tags: list[str] = Field(default_factory=list, description='Tags for categorization and search')
	expected_output: str | None = Field(
		default=None, description='Description of the expected output/result (e.g., "valor do IPTU em reais")'
	)
	created_at: str | None = Field(default=None, description='ISO timestamp of creation')
	updated_at: str | None = Field(default=None, description='ISO timestamp of last update')


class Plan(BaseModel):
	"""A complete execution plan for an objective."""

	model_config = ConfigDict(extra='forbid')

	metadata: PlanMetadata = Field(description='Plan metadata')
	steps: list[PlanStep] = Field(description='Ordered list of steps to execute')


class ArtifactType(str, Enum):
	"""Types of artifacts that can be produced."""

	TEXT = 'text'
	IMAGE = 'image'
	PDF = 'pdf'
	FILE = 'file'
	JSON = 'json'
	SCREENSHOT = 'screenshot'


class Artifact(BaseModel):
	"""An artifact produced during plan execution."""

	model_config = ConfigDict(extra='forbid')

	artifact_id: str = Field(default_factory=uuid7str, description='Unique identifier')
	type: ArtifactType = Field(description='Type of artifact')
	name: str = Field(description='Artifact name')
	content: str | None = Field(default=None, description='Text content or base64 encoded data')
	file_path: str | None = Field(default=None, description='Path to file if stored on disk')
	metadata: dict[str, Any] = Field(default_factory=dict, description='Additional metadata')


class ExecutionStatus(str, Enum):
	"""Status of plan execution."""

	SUCCESS = 'success'
	PARTIAL_SUCCESS = 'partial_success'
	FAILURE = 'failure'
	TIMEOUT = 'timeout'
	ERROR = 'error'


class ExecutionResult(BaseModel):
	"""Result of executing a plan."""

	model_config = ConfigDict(extra='forbid')

	execution_id: str = Field(default_factory=uuid7str, description='Unique execution identifier')
	plan_id: str = Field(description='ID of the plan that was executed')
	status: ExecutionStatus = Field(description='Execution status')
	artifacts: list[Artifact] = Field(default_factory=list, description='Artifacts produced')
	steps_completed: int = Field(default=0, description='Number of steps successfully completed')
	total_steps: int = Field(default=0, description='Total number of steps in plan')
	error_message: str | None = Field(default=None, description='Error message if execution failed')
	execution_time_ms: int | None = Field(default=None, description='Total execution time in milliseconds')
	metadata: dict[str, Any] = Field(default_factory=dict, description='Additional execution metadata')


class MapperResult(BaseModel):
	"""Result from the mapper component."""

	model_config = ConfigDict(extra='forbid')

	objective: str = Field(description='The objective that was mapped')
	success: bool = Field(description='Whether mapping was successful')
	raw_history: dict[str, Any] | None = Field(default=None, description='Raw AgentHistory data')
	error_message: str | None = Field(default=None, description='Error message if mapping failed')
	metadata: dict[str, Any] = Field(default_factory=dict, description='Additional metadata')
