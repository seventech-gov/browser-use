"""Planner service - transforms mapper output into deterministic execution plans."""

import logging
import re
from datetime import datetime, timezone

from seventech.shared_views import (
	ActionType,
	MapperResult,
	Plan,
	PlanMetadata,
	PlanStep,
)

logger = logging.getLogger(__name__)


class Planner:
	"""Converts browser-use Agent history into deterministic execution plans.

	This component analyzes the actions taken by the Mapper (via Agent) and
	creates a structured, parameterized plan that can be executed repeatedly
	without requiring an LLM.
	"""

	def __init__(self):
		"""Initialize the Planner."""
		logger.info('Planner initialized')

	def create_plan(self, mapper_result: MapperResult, plan_name: str | None = None) -> Plan:
		"""Create an execution plan from mapper results.

		Args:
			mapper_result: Result from the Mapper containing agent history
			plan_name: Optional name for the plan

		Returns:
			Structured execution plan

		Raises:
			ValueError: If mapper result is invalid or unsuccessful
		"""
		if not mapper_result.success:
			raise ValueError(f'Cannot create plan from failed mapping: {mapper_result.error_message}')

		if not mapper_result.raw_history:
			raise ValueError('Mapper result contains no history data')

		logger.info(f'Creating plan from mapper result for objective: {mapper_result.objective}')

		# Extract collected parameters from interactive session (if any)
		collected_params = mapper_result.metadata.get('collected_parameters', {})
		parameter_names = mapper_result.metadata.get('parameter_names', [])

		# Extract result location if marked by Agent
		result_location = mapper_result.metadata.get('result_location')

		logger.info(f'Found {len(parameter_names)} collected parameters from interactive session')
		if result_location:
			logger.info(f'Result location marked: {result_location}')

		# Extract steps from history
		steps = self._extract_steps(mapper_result.raw_history, collected_params, result_location)

		# Identify required parameters (combine auto-detected + collected)
		auto_detected_params = self._identify_parameters(steps)
		required_params = list(set(auto_detected_params + parameter_names))

		logger.info(f'Total required parameters: {len(required_params)} ({len(auto_detected_params)} auto-detected, {len(parameter_names)} collected)')

		# Extract expected output from result location
		expected_output = result_location.get('description') if result_location else None

		# Create metadata
		metadata = PlanMetadata(
			name=plan_name or self._generate_plan_name(mapper_result.objective),
			description=mapper_result.objective,
			url=mapper_result.metadata.get('starting_url'),
			required_params=required_params,
			tags=mapper_result.metadata.get('tags', []),
			expected_output=expected_output,
			created_at=datetime.now(timezone.utc).isoformat(),
		)

		plan = Plan(metadata=metadata, steps=steps)

		logger.info(f'Plan created: {plan.metadata.plan_id} with {len(steps)} steps and {len(required_params)} parameters')

		return plan

	def _extract_steps(
		self, raw_history: dict, collected_params: dict | None = None, result_location: dict | None = None
	) -> list[PlanStep]:
		"""Extract executable steps from agent history.

		Args:
			raw_history: Serialized agent history
			collected_params: Optional collected parameters from interactive session
			result_location: Optional location of final result (index + description)

		Returns:
			List of plan steps
		"""
		steps = []
		sequence_id = 0
		collected_params = collected_params or {}

		# Try to enrich result_location with xpath from history
		if result_location and not result_location.get('xpath'):
			result_location = self._enrich_result_location_with_xpath(raw_history, result_location)

		for history_item in raw_history.get('history', []):
			model_output = history_item.get('model_output')
			if not model_output:
				continue

			# Get actions directly from model_output (it's a list)
			actions = model_output.get('action', [])

			# Process each action in the list
			for action in actions:
				# Handle different action types from browser-use
				step = self._convert_action_to_step(action, sequence_id, collected_params, result_location)
				if step:
					steps.append(step)
					sequence_id += 1

		logger.info(f'Extracted {len(steps)} steps from history')
		return steps

	def _enrich_result_location_with_xpath(self, raw_history: dict, result_location: dict) -> dict:
		"""Extract rich context for the result element from history.

		Args:
			raw_history: Serialized agent history
			result_location: Result location with index

		Returns:
			Enhanced result_location with xpath, text_content, attributes, etc.
		"""
		target_index = result_location.get('index')
		if target_index is None:
			return result_location

		enriched = result_location.copy()

		logger.info(f'Enriching result_location for index {target_index}')
		logger.info(f'Raw history has {len(raw_history.get("history", []))} items')

		# Search through history for the state snapshot that contains this element
		for i, history_item in enumerate(raw_history.get('history', [])):
			# Check state snapshots
			state = history_item.get('state')
			if i < 3:  # Only log first 3 items to avoid spam
				logger.info(f'Item {i}: has state={state is not None}, keys={list(history_item.keys())}')

			if state and isinstance(state, dict):
				# Look for selector_map in state
				selector_map = state.get('selector_map', {})
				if i < 3:
					logger.info(f'Item {i}: selector_map has {len(selector_map)} entries')

				# selector_map is dict[int, node_info]
				if target_index in selector_map:
					node_info = selector_map[target_index]

					# Extract rich information
					if isinstance(node_info, dict):
						# Capture xpath
						if 'xpath' in node_info and node_info['xpath']:
							enriched['xpath'] = node_info['xpath']

						# Capture text content
						text_content = (
							node_info.get('value')
							or node_info.get('innerText')
							or node_info.get('textContent')
							or node_info.get('node_value')
						)
						if text_content:
							enriched['text_content'] = text_content
							logger.info(f'Captured text content for element {target_index}: {text_content[:100]}')

						# Capture attributes
						if 'attributes' in node_info and isinstance(node_info['attributes'], dict):
							attrs = node_info['attributes']
							if attrs.get('id'):
								enriched['element_id'] = attrs['id']
							if attrs.get('class'):
								enriched['element_class'] = attrs['class']
							if attrs.get('name'):
								enriched['element_name'] = attrs['name']

						# Capture tag name
						if 'tag_name' in node_info:
							enriched['tag_name'] = node_info['tag_name']

						logger.info(f'Rich context extracted for element {target_index}: {list(enriched.keys())}')
						return enriched

			# Also check actions that might have xpath
			model_output = history_item.get('model_output')
			if model_output:
				actions = model_output.get('action', [])
				for action in actions:
					if not action:
						continue

					action_name = list(action.keys())[0] if action.keys() else ''
					action_params = action.get(action_name, {})

					# If this action used our target index
					if action_params.get('index') == target_index:
						# Capture xpath if available
						if 'xpath' in action_params and action_params['xpath'] and 'xpath' not in enriched:
							enriched['xpath'] = action_params['xpath']

		if 'xpath' in enriched or 'text_content' in enriched:
			logger.info(f'Partial context found for element {target_index}')
		else:
			logger.warning(f'No rich context found for result element {target_index}')

		return enriched

	def _convert_action_to_step(
		self, action: dict, sequence_id: int, collected_params: dict | None = None, result_location: dict | None = None
	) -> PlanStep | None:
		"""Convert a browser-use action into a plan step.

		Args:
			action: Action dictionary from agent history (format: {"action_name": {params}})
			sequence_id: Step sequence number
			collected_params: Optional collected parameters from interactive session
			result_location: Optional location of final result (index + description)

		Returns:
			PlanStep or None if action cannot be converted
		"""
		collected_params = collected_params or {}

		# Action structure is: {"action_name": {params}}
		# Extract the action name (should be the only key)
		if not action:
			return None

		action_name = list(action.keys())[0] if action.keys() else ''
		action_params = action.get(action_name, {})

		# Skip mark_result_location - it's metadata, not an executable action
		if action_name == 'mark_result_location':
			logger.debug('Skipping mark_result_location - metadata only')
			return None

		# Map browser-use actions to our action types
		action_mapping = {
			'navigate': ActionType.GOTO,
			'click': ActionType.CLICK,
			'input': ActionType.INPUT,
			'select': ActionType.SELECT,
			'scroll': ActionType.SCROLL,
			'wait': ActionType.WAIT,
			'extract': ActionType.EXTRACT,
			'screenshot': ActionType.SCREENSHOT,
		}

		action_type = action_mapping.get(action_name)
		if not action_type:
			logger.debug(f'Skipping unknown action: {action_name}')
			return None

		# Convert parameters to our format
		converted_params = self._convert_params(action_type, action_params, collected_params, result_location)

		return PlanStep(
			sequence_id=sequence_id,
			action=action_type,
			params=converted_params,
			description=self._generate_step_description(action_type, converted_params),
			original_action=action_name,
			original_params=action_params,
		)

	def _convert_params(
		self,
		action_type: ActionType,
		original_params: dict,
		collected_params: dict | None = None,
		result_location: dict | None = None,
	) -> dict:
		"""Convert browser-use parameters to executor parameters.

		Args:
			action_type: Type of action
			original_params: Original parameters from browser-use
			collected_params: Optional collected parameters from interactive session
			result_location: Optional location of final result (index + description)

		Returns:
			Converted parameters dictionary
		"""
		params = {}
		collected_params = collected_params or {}

		if action_type == ActionType.GOTO:
			params['url'] = original_params.get('url', '')

		elif action_type == ActionType.CLICK:
			# browser-use uses "index" to reference elements
			params['index'] = original_params.get('index', 0)
			# Also store xpath if available for reference
			params['xpath'] = original_params.get('xpath', '')

		elif action_type == ActionType.INPUT:
			params['index'] = original_params.get('index', 0)
			text = original_params.get('text', '')
			params['xpath'] = original_params.get('xpath', '')

			# Check if this text matches a collected parameter value
			param_name = self._find_parameter_by_value(text, collected_params)

			if param_name:
				# Replace value with placeholder
				params['text'] = f'{{param:{param_name}}}'
				params['is_parameterized'] = True
				logger.info(f'Parameterized input: {text} -> {{param:{param_name}}}')
			else:
				# Use original text, check if it should be parameterized by regex
				params['text'] = text
				params['is_parameterized'] = self._should_parameterize(text)

		elif action_type == ActionType.SELECT:
			params['index'] = original_params.get('index', 0)
			params['value'] = original_params.get('value', '')
			params['xpath'] = original_params.get('xpath', '')

		elif action_type == ActionType.SCROLL:
			params['direction'] = original_params.get('direction', 'down')
			params['amount'] = original_params.get('amount', 500)

		elif action_type == ActionType.WAIT:
			params['duration_ms'] = original_params.get('duration', 1000)

		elif action_type == ActionType.EXTRACT:
			# If result_location was marked, use semantic query extraction
			if result_location:
				# Use query-based extraction (browser-use's extract with LLM)
				params['query'] = result_location.get('description', '')
				params['is_final_result'] = True

				# Try to capture the result the Agent already extracted
				if original_params.get('query'):
					params['query'] = original_params['query']

				logger.info(f'EXTRACT configured with query: "{params["query"]}"')
			else:
				# Default: extract whole page using original params
				params['query'] = original_params.get('query', '')
				params['is_final_result'] = False

		elif action_type == ActionType.SCREENSHOT:
			params['full_page'] = original_params.get('full_page', False)

		return params

	def _find_parameter_by_value(self, value: str, collected_params: dict) -> str | None:
		"""Find a collected parameter by matching its value.

		Args:
			value: The value to search for
			collected_params: Collected parameters dict with 'parameters' list

		Returns:
			Parameter name if found, None otherwise
		"""
		if not value or not collected_params:
			return None

		# collected_params has structure: {'parameters': [...], 'count': N}
		parameters_list = collected_params.get('parameters', [])

		for param in parameters_list:
			# param is a dict with keys: name, value, label, etc.
			if str(param.get('value', '')) == str(value):
				return param.get('name')

		return None

	def _should_parameterize(self, text: str) -> bool:
		"""Determine if a text value should be parameterized.

		Args:
			text: Text to analyze

		Returns:
			True if text appears to be user-specific data
		"""
		# Patterns that suggest user-specific data
		patterns = [
			r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone numbers
			r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
			r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b',  # CPF
			r'\b\d{5}-?\d{3}\b',  # CEP
		]

		for pattern in patterns:
			if re.search(pattern, text):
				return True

		return False

	def _identify_parameters(self, steps: list[PlanStep]) -> list[str]:
		"""Identify parameters that need to be provided at execution time.

		Args:
			steps: List of plan steps

		Returns:
			List of parameter names
		"""
		params = set()

		for step in steps:
			if step.action == ActionType.INPUT:
				if step.params.get('is_parameterized'):
					# Generate parameter name from xpath or use generic
					param_name = self._extract_param_name(step.params.get('xpath', ''))
					params.add(param_name)

		return sorted(list(params))

	def _extract_param_name(self, xpath: str) -> str:
		"""Extract a meaningful parameter name from xpath.

		Args:
			xpath: XPath selector

		Returns:
			Parameter name
		"""
		# Try to extract from id or name attributes
		if 'id=' in xpath:
			match = re.search(r"id='([^']+)'", xpath)
			if match:
				return match.group(1)

		if 'name=' in xpath:
			match = re.search(r"name='([^']+)'", xpath)
			if match:
				return match.group(1)

		# Fallback to generic name
		return 'user_input'

	def _generate_step_description(self, action_type: ActionType, params: dict) -> str:
		"""Generate human-readable description for a step.

		Args:
			action_type: Type of action
			params: Step parameters

		Returns:
			Description string
		"""
		if action_type == ActionType.GOTO:
			return f"Navigate to {params.get('url', 'URL')}"

		elif action_type == ActionType.CLICK:
			xpath = params.get('xpath', '')
			index = params.get('index', 0)
			selector = xpath if xpath else f'element #{index}'
			return f"Click {selector}"

		elif action_type == ActionType.INPUT:
			xpath = params.get('xpath', '')
			index = params.get('index', 0)
			selector = xpath if xpath else f'element #{index}'
			text_preview = params.get('text', '')[:30]  # First 30 chars
			return f"Input text into {selector}: '{text_preview}...'"

		elif action_type == ActionType.SELECT:
			xpath = params.get('xpath', '')
			index = params.get('index', 0)
			selector = xpath if xpath else f'element #{index}'
			return f"Select option in {selector}"

		elif action_type == ActionType.SCROLL:
			return f"Scroll {params.get('direction', 'down')}"

		elif action_type == ActionType.WAIT:
			return f"Wait {params.get('duration_ms', 0)}ms"

		elif action_type == ActionType.EXTRACT:
			return 'Extract content from page'

		elif action_type == ActionType.SCREENSHOT:
			return 'Take screenshot'

		return f'Execute {action_type.value}'

	def _generate_plan_name(self, objective: str) -> str:
		"""Generate a plan name from objective.

		Args:
			objective: Objective description

		Returns:
			Sanitized plan name
		"""
		# Take first 50 chars, remove special chars, replace spaces with underscores
		name = objective[:50].lower()
		name = re.sub(r'[^a-z0-9\s-]', '', name)
		name = re.sub(r'\s+', '_', name)
		return name.strip('_')
