"""Session manager for interactive mapping sessions via API."""

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from seventech.mapper.session import InputRequest, MapperSession, SessionStatus
from seventech.shared_views import MapperResult

logger = logging.getLogger(__name__)


class PendingInputRequest(BaseModel):
	"""A pending input request waiting for user response."""

	model_config = ConfigDict(extra='forbid')

	request: InputRequest
	response_future: Any = Field(exclude=True)  # asyncio.Future, excluded from serialization


class MappingSessionState(BaseModel):
	"""Complete state of a mapping session for API responses."""

	model_config = ConfigDict(extra='forbid')

	session_id: str
	objective: str
	status: SessionStatus
	created_at: str
	updated_at: str
	steps_completed: int
	collected_parameters: list[dict[str, Any]]
	current_input_request: dict[str, Any] | None
	error_message: str | None


class SessionManager:
	"""Manages active interactive mapping sessions.

	This allows multiple concurrent mapping sessions to run independently,
	each waiting for user input via API calls.
	"""

	def __init__(self):
		"""Initialize the session manager."""
		self.sessions: dict[str, MapperSession] = {}
		self.pending_inputs: dict[str, PendingInputRequest] = {}
		self.mapper_results: dict[str, MapperResult] = {}
		logger.info('SessionManager initialized')

	def create_session(self, session_id: str, objective: str) -> MapperSession:
		"""Create a new mapping session.

		Args:
			session_id: Session identifier
			objective: Mapping objective

		Returns:
			New MapperSession
		"""
		session = MapperSession(objective=objective, session_id=session_id)
		self.sessions[session_id] = session
		logger.info(f'Session created: {session_id}')
		return session

	def get_session(self, session_id: str) -> MapperSession | None:
		"""Get a session by ID.

		Args:
			session_id: Session identifier

		Returns:
			MapperSession or None if not found
		"""
		return self.sessions.get(session_id)

	def get_session_state(self, session_id: str) -> MappingSessionState | None:
		"""Get serializable session state.

		Args:
			session_id: Session identifier

		Returns:
			MappingSessionState or None if not found
		"""
		session = self.get_session(session_id)
		if not session:
			return None

		return MappingSessionState(
			session_id=session.session_id,
			objective=session.objective,
			status=session.status,
			created_at=session.created_at,
			updated_at=session.updated_at,
			steps_completed=session.steps_completed,
			collected_parameters=[p.model_dump() for p in session.collector.list_parameters()],
			current_input_request=session.current_input_request.model_dump()
			if session.current_input_request
			else None,
			error_message=session.error_message,
		)

	async def request_input(self, session_id: str, request: InputRequest) -> str:
		"""Register an input request and wait for response.

		Args:
			session_id: Session identifier
			request: Input request details

		Returns:
			User-provided value

		Raises:
			TimeoutError: If no response within timeout
		"""
		# Create future to wait for response
		loop = asyncio.get_event_loop()
		response_future = loop.create_future()

		# Store pending request
		self.pending_inputs[session_id] = PendingInputRequest(request=request, response_future=response_future)

		logger.info(f'Session {session_id}: Waiting for input - {request.field_label}')

		try:
			# Wait for user to provide input via API (with 5 minute timeout)
			value = await asyncio.wait_for(response_future, timeout=300)
			logger.info(f'Session {session_id}: Received input - {value}')
			return value

		except asyncio.TimeoutError:
			logger.error(f'Session {session_id}: Input request timed out')
			raise TimeoutError(f'Input request timed out for session {session_id}')

		finally:
			# Clean up pending request
			self.pending_inputs.pop(session_id, None)

	def provide_input(self, session_id: str, value: str) -> bool:
		"""Provide user input for a pending request.

		Args:
			session_id: Session identifier
			value: User-provided value

		Returns:
			True if input was accepted, False if no pending request
		"""
		pending = self.pending_inputs.get(session_id)
		if not pending:
			logger.warning(f'Session {session_id}: No pending input request')
			return False

		# Set the future result
		if not pending.response_future.done():
			pending.response_future.set_result(value)
			logger.info(f'Session {session_id}: Input provided')
			return True

		return False

	def get_pending_input(self, session_id: str) -> InputRequest | None:
		"""Get pending input request for a session.

		Args:
			session_id: Session identifier

		Returns:
			InputRequest or None if no pending request
		"""
		pending = self.pending_inputs.get(session_id)
		return pending.request if pending else None

	def store_result(self, session_id: str, result: MapperResult):
		"""Store mapper result for a session.

		Args:
			session_id: Session identifier
			result: Mapper result
		"""
		self.mapper_results[session_id] = result
		logger.info(f'Session {session_id}: Result stored')

	def get_result(self, session_id: str) -> MapperResult | None:
		"""Get mapper result for a session.

		Args:
			session_id: Session identifier

		Returns:
			MapperResult or None if not available
		"""
		return self.mapper_results.get(session_id)

	def delete_session(self, session_id: str) -> bool:
		"""Delete a session and clean up resources.

		Args:
			session_id: Session identifier

		Returns:
			True if session was deleted, False if not found
		"""
		if session_id in self.sessions:
			self.sessions.pop(session_id)
			self.pending_inputs.pop(session_id, None)
			self.mapper_results.pop(session_id, None)
			logger.info(f'Session {session_id}: Deleted')
			return True

		return False

	def list_sessions(self) -> list[MappingSessionState]:
		"""List all active sessions.

		Returns:
			List of session states
		"""
		states = []
		for session_id in self.sessions.keys():
			state = self.get_session_state(session_id)
			if state:
				states.append(state)
		return states

	def cancel_session(self, session_id: str) -> bool:
		"""Cancel a running session.

		Args:
			session_id: Session identifier

		Returns:
			True if session was cancelled
		"""
		session = self.get_session(session_id)
		if not session:
			return False

		session.cancel()

		# Cancel any pending input
		pending = self.pending_inputs.get(session_id)
		if pending and not pending.response_future.done():
			pending.response_future.cancel()

		return True
