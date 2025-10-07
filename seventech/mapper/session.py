"""Interactive mapping session management."""

import inspect
import logging
from collections.abc import Awaitable
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field
from uuid_extensions import uuid7str

from seventech.mapper.collector import CollectedParameter, ParameterCollector

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
	"""Status of a mapping session."""

	INITIALIZED = 'initialized'
	RUNNING = 'running'
	WAITING_FOR_INPUT = 'waiting_for_input'
	COMPLETED = 'completed'
	FAILED = 'failed'
	CANCELLED = 'cancelled'


class InputRequest(BaseModel):
	"""Request for user input during mapping."""

	model_config = ConfigDict(extra='forbid')

	request_id: str = Field(default_factory=uuid7str, description='Unique request identifier')
	field_name: str = Field(description='Name of the field requesting input')
	field_label: str = Field(description='Human-readable label for the field')
	prompt: str = Field(description='Prompt to show to user')
	xpath: str | None = Field(default=None, description='XPath of the field')
	placeholder: str | None = Field(default=None, description='Placeholder/example value')
	current_step: int | None = Field(default=None, description='Current step number')
	required: bool = Field(default=True, description='Whether input is required')


class MapperSession:
	"""Manages state for an interactive mapping session.

	This session allows pausing mapper execution to collect user input
	for fields that require dynamic data (CPF, inscrição imobiliária, etc.).
	"""

	def __init__(self, objective: str, session_id: str | None = None):
		"""Initialize a mapping session.

		Args:
			objective: The mapping objective
			session_id: Optional session ID (generated if not provided)
		"""
		self.session_id = session_id or uuid7str()
		self.objective = objective
		self.status = SessionStatus.INITIALIZED
		self.created_at = datetime.now(timezone.utc).isoformat()
		self.updated_at = self.created_at

		# Parameter collection
		self.collector = ParameterCollector()

		# Current input request (when paused)
		self.current_input_request: InputRequest | None = None

		# Callbacks (can be sync or async)
		self.on_input_needed: Callable[[InputRequest], str] | Callable[[InputRequest], Awaitable[str]] | None = None
		self.on_status_change: Callable[[SessionStatus], None] | None = None

		# Session metadata
		self.metadata: dict[str, Any] = {}
		self.steps_completed = 0
		self.error_message: str | None = None

		# Result location (marked by Agent during mapping)
		self.result_location: dict[str, Any] | None = None

		logger.info(f'MapperSession created: {self.session_id} - {objective}')

	def set_status(self, status: SessionStatus):
		"""Update session status.

		Args:
			status: New status
		"""
		old_status = self.status
		self.status = status
		self.updated_at = datetime.now(timezone.utc).isoformat()

		logger.info(f'Session {self.session_id}: {old_status} → {status}')

		if self.on_status_change:
			self.on_status_change(status)

	async def request_input(
		self,
		field_name: str,
		field_label: str,
		prompt: str,
		xpath: str | None = None,
		placeholder: str | None = None,
		required: bool = True,
	) -> str:
		"""Request input from user and pause session.

		Args:
			field_name: Name of the field (sanitized)
			field_label: Human-readable label
			prompt: Prompt to show user
			xpath: XPath of the field
			placeholder: Placeholder/example
			required: Whether input is required

		Returns:
			The value provided by user

		Raises:
			RuntimeError: If no input callback is configured
		"""
		# Create input request
		request = InputRequest(
			field_name=field_name,
			field_label=field_label,
			prompt=prompt,
			xpath=xpath,
			placeholder=placeholder,
			current_step=self.steps_completed,
			required=required,
		)

		self.current_input_request = request
		self.set_status(SessionStatus.WAITING_FOR_INPUT)

		logger.info(f'Session {self.session_id}: Requesting input for {field_label}')

		# Get input from callback
		if not self.on_input_needed:
			raise RuntimeError('No input callback configured for interactive session')

		try:
			# Check if callback is async or sync
			value: str
			if inspect.iscoroutinefunction(self.on_input_needed):
				value = await self.on_input_needed(request)
			else:
				value = self.on_input_needed(request)  # type: ignore[assignment]

			# Collect the parameter
			self.collector.collect(
				name=field_name,
				value=value,
				label=field_label,
				xpath=xpath,
				description=prompt,
				example=placeholder,
				step_number=self.steps_completed,
			)

			self.current_input_request = None
			self.set_status(SessionStatus.RUNNING)

			return value

		except Exception as e:
			logger.error(f'Error getting user input: {e}')
			self.set_status(SessionStatus.FAILED)
			self.error_message = str(e)
			raise

	def complete(self):
		"""Mark session as completed."""
		self.set_status(SessionStatus.COMPLETED)
		self.current_input_request = None
		logger.info(f'Session {self.session_id}: Completed with {len(self.collector.parameters)} parameters')

	def fail(self, error_message: str):
		"""Mark session as failed.

		Args:
			error_message: Error description
		"""
		self.error_message = error_message
		self.set_status(SessionStatus.FAILED)
		logger.error(f'Session {self.session_id}: Failed - {error_message}')

	def cancel(self):
		"""Cancel the session."""
		self.set_status(SessionStatus.CANCELLED)
		logger.info(f'Session {self.session_id}: Cancelled')

	def get_collected_parameters(self) -> list[CollectedParameter]:
		"""Get all collected parameters.

		Returns:
			List of collected parameters
		"""
		return self.collector.list_parameters()

	def to_dict(self) -> dict[str, Any]:
		"""Export session to dictionary.

		Returns:
			Dictionary representation
		"""
		return {
			'session_id': self.session_id,
			'objective': self.objective,
			'status': self.status.value,
			'created_at': self.created_at,
			'updated_at': self.updated_at,
			'parameters': self.collector.to_dict(),
			'steps_completed': self.steps_completed,
			'error_message': self.error_message,
			'metadata': self.metadata,
			'current_input_request': self.current_input_request.model_dump() if self.current_input_request else None,
		}
