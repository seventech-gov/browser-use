"""Interactive mapper with user input capability during mapping."""

import logging
from typing import Callable

from browser_use import Agent
from browser_use.agent.views import ActionResult
from browser_use.browser import BrowserProfile
from browser_use.llm.base import BaseChatModel
from browser_use.tools.service import Tools

from seventech.mapper.collector import CollectedParameter
from seventech.mapper.session import InputRequest, MapperSession, SessionStatus
from seventech.mapper.views import MapObjectiveRequest, MapperConfig
from seventech.shared_views import MapperResult

logger = logging.getLogger(__name__)


class InteractiveMapper:
	"""Interactive mapper that can request user input during mapping.

	This allows mapping objectives that require dynamic data (like CPF,
	inscrição imobiliária, etc.) by pausing execution and asking the user.

	Example flow:
		1. Start mapping objective
		2. Agent encounters field needing user data
		3. Agent calls ask_user_for_input action
		4. Mapper pauses and requests input via callback
		5. User provides value
		6. Mapper continues with that value
		7. Final plan includes parameter placeholders
	"""

	def __init__(
		self,
		llm: BaseChatModel,
		config: MapperConfig | None = None,
		input_callback: Callable[[InputRequest], str] | None = None,
	):
		"""Initialize the Interactive Mapper.

		Args:
			llm: LLM instance to use for browser automation
			config: Optional mapper configuration
			input_callback: Callback function to get user input
				Receives InputRequest, returns user-provided value
		"""
		self.llm = llm
		self.config = config or MapperConfig(headless=False)  # Interactive mode requires visible browser
		self.input_callback = input_callback
		logger.info('InteractiveMapper initialized')

	async def map_objective(
		self, request: MapObjectiveRequest, session: MapperSession | None = None
	) -> tuple[MapperResult, MapperSession]:
		"""Map an objective interactively, requesting user input when needed.

		Args:
			request: Mapping request containing objective
			session: Optional existing session to use (for API integration)

		Returns:
			Tuple of (MapperResult, MapperSession with collected parameters)
		"""
		# Use provided session or create new one
		if session is None:
			session = MapperSession(objective=request.objective)
			session.on_input_needed = self._handle_input_request

		session.set_status(SessionStatus.RUNNING)

		logger.info(f'Starting interactive mapping: {request.objective}')

		try:
			# Create browser profile
			profile = BrowserProfile(
				headless=False,  # Must be visible for interactive mapping
				disable_security=False,
			)

			# Create custom Tools with interactive action registered
			custom_tools = self._create_custom_tools(session)

			# Add instructions to system prompt for using interactive actions
			enhanced_task = self._enhance_task_with_instructions(request.objective)

			# Create agent with custom tools
			agent = Agent(
				task=enhanced_task,
				llm=self.llm,
				browser_profile=profile,
				max_steps=self.config.max_steps,
				tools=custom_tools,
			)

			# Run the agent
			logger.info('Running browser-use Agent in interactive mode...')
			history = await agent.run()

			# Serialize history
			from seventech.mapper.service import Mapper

			mapper = Mapper(self.llm, self.config)
			raw_history = mapper._serialize_history(history)

			# Complete session
			session.complete()

			# Create mapper result with parameter information
			mapper_result = MapperResult(
				objective=request.objective,
				success=True,
				raw_history=raw_history,
				metadata={
					'starting_url': request.starting_url,
					'tags': request.tags,
					'plan_name': request.plan_name,
					'steps_count': len(history.history),
					'interactive_session_id': session.session_id,
					'collected_parameters': session.collector.to_dict(),
					'parameter_names': session.collector.get_parameter_names(),
					'result_location': session.result_location,  # Where the final result is located
				},
			)

			logger.info(
				f'Interactive mapping completed. Parameters collected: {len(session.collector.parameters)}'
			)

			# Save mapper result to JSON file
			self._save_mapper_result(mapper_result, session.session_id)

			return mapper_result, session

		except Exception as e:
			logger.error(f'Interactive mapping failed: {str(e)}', exc_info=True)
			session.fail(str(e))

			return (
				MapperResult(
					objective=request.objective,
					success=False,
					error_message=str(e),
					metadata={
						'error_type': type(e).__name__,
						'session_id': session.session_id,
						'collected_parameters': session.collector.to_dict(),
					},
				),
				session,
			)

	def _create_custom_tools(self, session: MapperSession) -> Tools:
		"""Create custom Tools instance with interactive actions registered.

		Args:
			session: Mapping session

		Returns:
			Tools instance with custom actions
		"""
		# Create tools instance
		tools = Tools(display_files_in_done_text=True)

		# Register custom action using decorator
		@tools.action(
			'Request user input for a field (CPF, email, etc.). Returns the value. Use returned value immediately to fill the field. Call ONCE per field.'
		)
		async def ask_user_for_input(
			field_name: str, field_label: str, prompt: str, xpath: str = '', placeholder: str = ''
		) -> ActionResult:
			"""Ask user to provide input for a field.

			Use this when you encounter a field that requires user-specific data
			that you don't have (like CPF, inscrição imobiliária, email, etc.).

			Args:
				field_name: Internal name for the field (e.g., 'inscricao_imobiliaria')
				field_label: Human-readable label (e.g., 'Inscrição Imobiliária')
				prompt: Question to ask user (e.g., 'Por favor, insira sua inscrição imobiliária')
				xpath: XPath of the field where this will be used
				placeholder: Example value to show user

			Returns:
				ActionResult with the user-provided value
			"""
			logger.info(f'Agent requesting user input: {field_label}')

			# Request input through session (async)
			value = await session.request_input(
				field_name=field_name,
				field_label=field_label,
				prompt=prompt,
				xpath=xpath or None,
				placeholder=placeholder or None,
			)

			logger.info(f'User provided value for {field_label}: {value}')

			# Return clear result telling agent to USE this value
			result_message = (
				f'User provided {field_label}: "{value}"\n'
				f'NEXT STEP: Use this value to fill the field using input() action.'
			)

			return ActionResult(
				extracted_content=result_message,
				long_term_memory=f'Received {field_name}={value} from user',
				include_in_memory=True,
				is_done=False,
			)

		@tools.action(
			'Mark the location of the final result/output that needs to be extracted. IMPORTANT: Only call this AFTER you see the correct value displayed.'
		)
		async def mark_result_location(index: int, description: str) -> ActionResult:
			"""Mark where the final result is located on the page.

			Use this action to indicate which element contains the final result
			that answers the objective (e.g., "valor do IPTU", "saldo da conta", etc.).

			CRITICAL: You must verify the element shows the correct value BEFORE marking it.
			Look at the current page state and confirm the element at the given index
			displays the information requested in the objective.

			Args:
				index: The index of the element containing the result
				description: What this result represents (e.g., "valor total do IPTU: R$ 1.234,56")

			Returns:
				ActionResult confirming the result location was marked
			"""
			logger.info(f'Agent marking result location: index={index}, description={description}')

			# Store basic information - rich context will be extracted during planning
			session.result_location = {'index': index, 'description': description}

			result_message = f'✓ Marked element #{index} as final result: {description}'

			return ActionResult(
				extracted_content=result_message,
				long_term_memory=f'Result location marked: {description} at element #{index}',
				include_in_memory=True,
				is_done=False,
			)

		logger.info('Created custom Tools with ask_user_for_input and mark_result_location actions')
		return tools

	def _enhance_task_with_instructions(self, original_task: str) -> str:
		"""Add instructions about using interactive actions.

		Args:
			original_task: Original task description

		Returns:
			Enhanced task with interactive instructions
		"""
		instructions = """
CRITICAL INSTRUCTIONS FOR USER INPUT & RESULT EXTRACTION:

1. You have TWO special actions available:
   - ask_user_for_input: Request user-specific data (CPF, inscrição imobiliária, etc.)
   - mark_result_location: Mark where the final result/answer is located

2. When you encounter a field requiring user-specific data:
   a) Call ask_user_for_input ONCE with the field details
   b) The action RETURNS the user-provided value immediately
   c) Use the returned value to fill the field using input() action
   d) NEVER ask for the same field twice

3. When you find the FINAL RESULT that answers the objective:
   a) Identify which element contains the answer (e.g., "R$ 1.234,56" for IPTU value)
   b) Call mark_result_location(index=<element_index>, description="what this value represents")
   c) Call extract() to capture the page content with the result
   d) ONLY AFTER extract(), call done() to finish

4. COMPLETE WORKFLOW EXAMPLE - Getting IPTU value:
   Step 1: Navigate to IPTU site
   Step 2: Call ask_user_for_input(field_name='inscricao_imobiliaria', ...)
   Step 3: Use returned value: input(index=5, text=<inscricao_value>)
   Step 4: Click submit button
   Step 5: Wait for result page to load
   Step 6: Identify element with IPTU value (e.g., element #23 shows "R$ 1.234,56")
   Step 7: Call mark_result_location(index=23, description="valor do IPTU em reais")
   Step 8: Call extract() to capture the result
   Step 9: Call done() to finish

5. MANDATORY FINAL STEPS:
   - ALWAYS call mark_result_location before extract()
   - ALWAYS call extract() before done()
   - NEVER call done() without first calling extract()
   - The extract() captures the result that will be returned to the user

6. IMPORTANT:
   - ask_user_for_input gives you the value immediately - use it right away
   - mark_result_location should be called when you see the final answer
   - Do NOT guess or invent personal data - always ask user first

Your objective: {original_task}
"""
		return instructions.format(original_task=original_task)

	def _handle_input_request(self, request: InputRequest) -> str:
		"""Handle input request from session.

		Args:
			request: Input request

		Returns:
			User-provided value

		Raises:
			RuntimeError: If no input callback is configured
		"""
		if self.input_callback:
			return self.input_callback(request)

		# Fallback: use command-line input
		print(f'\n🤔 {request.prompt}')
		if request.placeholder:
			print(f'   Exemplo: {request.placeholder}')
		if request.xpath:
			print(f'   Campo: {request.xpath}')

		value = input(f'\n{request.field_label}: ').strip()

		if not value and request.required:
			raise ValueError(f'Campo obrigatório: {request.field_label}')

		return value

	def get_collected_parameters(self, session: MapperSession) -> list[CollectedParameter]:
		"""Get parameters collected during a session.

		Args:
			session: Mapping session

		Returns:
			List of collected parameters
		"""
		return session.get_collected_parameters()

	def _save_mapper_result(self, mapper_result: MapperResult, session_id: str) -> None:
		"""Save mapper result to JSON file.

		Args:
			mapper_result: Mapper result to save
			session_id: Session ID to use as filename
		"""
		from pathlib import Path

		import json

		# Create results directory if it doesn't exist
		results_dir = Path('seventech/mapper/results')
		results_dir.mkdir(parents=True, exist_ok=True)

		# Create filename with session ID
		filename = results_dir / f'{session_id}.json'

		# Prepare data for JSON serialization
		result_data = {
			'session_id': session_id,
			'objective': mapper_result.objective,
			'success': mapper_result.success,
			'error_message': mapper_result.error_message,
			'metadata': mapper_result.metadata,
			'raw_history': mapper_result.raw_history,  # Complete history for planner
		}

		# Save to JSON file
		with open(filename, 'w', encoding='utf-8') as f:
			json.dump(result_data, f, indent=2, ensure_ascii=False)

		logger.info(f'Saved mapper result to {filename}')
