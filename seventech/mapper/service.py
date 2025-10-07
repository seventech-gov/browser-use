"""Mapper service - uses browser-use Agent to map objectives into executable plans."""

import logging
from datetime import datetime, timezone

from browser_use import Agent
from browser_use.agent.views import AgentHistoryList
from browser_use.browser import BrowserProfile
from browser_use.llm.base import BaseChatModel

from seventech.mapper.views import MapObjectiveRequest, MapperConfig
from seventech.shared_views import MapperResult

logger = logging.getLogger(__name__)


class Mapper:
	"""Maps user objectives into actionable plans using LLM-driven browser automation.

	This component uses browser-use Agent to explore and complete an objective,
	recording all actions taken for later conversion into a deterministic plan.
	"""

	def __init__(self, llm: BaseChatModel, config: MapperConfig | None = None):
		"""Initialize the Mapper.

		Args:
			llm: LLM instance to use for browser automation
			config: Optional mapper configuration
		"""
		self.llm = llm
		self.config = config or MapperConfig()
		logger.info('Mapper initialized')

	async def map_objective(self, request: MapObjectiveRequest) -> MapperResult:
		"""Map an objective by running the browser-use Agent.

		Args:
			request: Mapping request containing objective and configuration

		Returns:
			MapperResult containing the agent's execution history
		"""
		logger.info(f'Starting to map objective: {request.objective}')

		try:
			# Create browser profile
			profile = BrowserProfile(
				headless=self.config.headless,
				disable_security=False,  # Keep security enabled
			)

			# Create agent with the objective
			agent = Agent(
				task=request.objective,
				llm=self.llm,
				browser_profile=profile,
				max_steps=self.config.max_steps,
			)

			# Run the agent and capture history
			logger.info('Running browser-use Agent...')
			history: AgentHistoryList = await agent.run()

			# Convert history to serializable format
			raw_history = self._serialize_history(history)

			logger.info(f'Mapping completed successfully. Steps taken: {len(history.history)}')

			return MapperResult(
				objective=request.objective,
				success=True,
				raw_history=raw_history,
				metadata={
					'starting_url': request.starting_url,
					'tags': request.tags,
					'plan_name': request.plan_name,
					'steps_count': len(history.history),
					'mapped_at': datetime.now(timezone.utc).isoformat(),
				},
			)

		except Exception as e:
			logger.error(f'Failed to map objective: {str(e)}', exc_info=True)
			return MapperResult(
				objective=request.objective,
				success=False,
				error_message=str(e),
				metadata={
					'error_type': type(e).__name__,
				},
			)

	def _serialize_history(self, history: AgentHistoryList) -> dict:
		"""Convert AgentHistoryList to serializable dict.

		Args:
			history: Agent execution history

		Returns:
			Serializable dictionary representation
		"""
		serialized = {
			'history': [],
			'final_result': None,
			'errors': [],
		}

		for step in history.history:
			step_data = {
				'step_number': step.metadata.step_number if step.metadata else None,
				'state': self._serialize_state(step.state) if step.state else None,
				'result': self._serialize_result(step.result) if step.result else None,
				'model_output': step.model_output.model_dump() if step.model_output else None,
			}
			serialized['history'].append(step_data)

		# Capture final result if available
		if hasattr(history, 'final_result') and history.final_result:
			serialized['final_result'] = str(history.final_result)

		# Capture any errors (errors is a method, not a property)
		if hasattr(history, 'errors'):
			errors = history.errors()
			if errors:
				serialized['errors'] = [str(e) for e in errors if e]

		return serialized

	def _serialize_state(self, state) -> dict:
		"""Serialize agent state."""
		if hasattr(state, 'model_dump'):
			return state.model_dump()
		return {'raw': str(state)}

	def _serialize_result(self, result) -> dict:
		"""Serialize action result."""
		if hasattr(result, 'model_dump'):
			return result.model_dump()
		return {'raw': str(result)}
