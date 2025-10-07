"""Executor service - executes plans deterministically without LLM."""

import asyncio
import base64
import logging
import time
from pathlib import Path
from typing import Any

from browser_use.browser import BrowserProfile, BrowserSession
from browser_use.browser.events import (
	ClickElementEvent,
	NavigateToUrlEvent,
	ScreenshotEvent,
	ScrollEvent,
	TypeTextEvent,
)

from seventech.executor.views import ExecutePlanRequest, ExecutorConfig
from seventech.shared_views import (
	ActionType,
	Artifact,
	ArtifactType,
	ExecutionResult,
	ExecutionStatus,
	Plan,
)

logger = logging.getLogger(__name__)


class Executor:
	"""Executes plans deterministically without requiring an LLM.

	This component takes a structured plan and executes it step-by-step using
	direct browser automation via browser-use's BrowserSession and low-level APIs.
	NO LLM is involved in execution - everything is deterministic.
	"""

	def __init__(self, config: ExecutorConfig | None = None):
		"""Initialize the Executor.

		Args:
			config: Optional executor configuration
		"""
		self.config = config or ExecutorConfig()
		logger.info('Executor initialized')

	async def execute_plan(self, plan: Plan, request: ExecutePlanRequest) -> ExecutionResult:
		"""Execute a plan with provided parameters.

		Args:
			plan: The plan to execute
			request: Execution request with parameters

		Returns:
			Execution result with artifacts and status
		"""
		start_time = time.time()
		logger.info(f'Starting execution of plan: {plan.metadata.plan_id}')

		# Merge configs
		config = request.config_overrides or self.config

		# Initialize browser session
		profile = BrowserProfile(
			headless=config.headless,
			disable_security=False,
		)

		browser = BrowserSession(browser_profile=profile)

		try:
			# Start browser
			await browser.start()
			logger.info('Browser started successfully')

			# Execute steps
			result = await self._execute_steps(browser, plan, request.params, config)

			# Calculate execution time
			execution_time = int((time.time() - start_time) * 1000)
			result.execution_time_ms = execution_time

			logger.info(f'Plan execution completed: {result.status}')
			return result

		except Exception as e:
			logger.error(f'Plan execution failed: {str(e)}', exc_info=True)

			# Take error screenshot if configured
			artifacts = []
			if config.screenshot_on_error:
				try:
					event = browser.event_bus.dispatch(ScreenshotEvent())
					await event
					screenshot_base64 = await event.event_result(raise_if_any=True, raise_if_none=False)

					if screenshot_base64:
						artifacts.append(
							Artifact(
								type=ArtifactType.SCREENSHOT,
								name='error_screenshot.png',
								content=screenshot_base64,
								metadata={'error': str(e)},
							)
						)
				except Exception as screenshot_error:
					logger.error(f'Failed to take error screenshot: {screenshot_error}')

			execution_time = int((time.time() - start_time) * 1000)

			return ExecutionResult(
				plan_id=plan.metadata.plan_id,
				status=ExecutionStatus.ERROR,
				artifacts=artifacts,
				steps_completed=0,
				total_steps=len(plan.steps),
				error_message=str(e),
				execution_time_ms=execution_time,
			)

		finally:
			# Always stop browser
			try:
				await browser.stop()
				logger.info('Browser stopped')
			except Exception as e:
				logger.error(f'Error stopping browser: {e}')

	async def _execute_steps(
		self, browser: BrowserSession, plan: Plan, params: dict, config: ExecutorConfig
	) -> ExecutionResult:
		"""Execute plan steps sequentially.

		Args:
			browser: Browser session
			plan: Plan to execute
			params: User-provided parameters
			config: Executor configuration

		Returns:
			Execution result
		"""
		artifacts = []
		steps_completed = 0
		total_steps = len(plan.steps)

		for step in plan.steps:
			logger.info(f'Executing step {step.sequence_id + 1}/{total_steps}: {step.description}')

			try:
				# Inject parameters into step params
				injected_params = self._inject_params(step.params, params)

				# Execute step based on action type
				step_artifacts = await self._execute_action(browser, step.action, injected_params, config)

				# Collect artifacts
				artifacts.extend(step_artifacts)

				steps_completed += 1

			except Exception as e:
				logger.error(f'Step {step.sequence_id} failed: {str(e)}')

				# Retry logic
				if config.retry_on_error:
					logger.info('Retrying step once...')
					try:
						await asyncio.sleep(1)  # Brief pause before retry
						injected_params = self._inject_params(step.params, params)
						step_artifacts = await self._execute_action(browser, step.action, injected_params, config)
						artifacts.extend(step_artifacts)
						steps_completed += 1
						logger.info('Step succeeded on retry')
						continue
					except Exception as retry_error:
						logger.error(f'Retry failed: {retry_error}')

				# Step failed permanently
				return ExecutionResult(
					plan_id=plan.metadata.plan_id,
					status=ExecutionStatus.FAILURE,
					artifacts=artifacts,
					steps_completed=steps_completed,
					total_steps=total_steps,
					error_message=f'Step {step.sequence_id} failed: {str(e)}',
				)

		# All steps completed successfully
		return ExecutionResult(
			plan_id=plan.metadata.plan_id,
			status=ExecutionStatus.SUCCESS,
			artifacts=artifacts,
			steps_completed=steps_completed,
			total_steps=total_steps,
		)

	async def _find_element(self, browser: BrowserSession, params: dict) -> Any:
		"""Find element using multi-strategy search with rich context.

		Tries multiple strategies in order:
		1. By index (fastest but fragile)
		2. By element_id (most reliable)
		3. By xpath (structural)
		4. By text content similarity (semantic)
		5. By tag + class combination

		Args:
			browser: Browser session
			params: Action parameters with rich element context

		Returns:
			DOM node

		Raises:
			ValueError: If element cannot be found
		"""
		index = params.get('index', 0)
		xpath = params.get('xpath', '')
		element_id = params.get('element_id', '')
		element_class = params.get('element_class', '')
		tag_name = params.get('tag_name', '')
		expected_text = params.get('expected_text', '')

		# Refresh browser state to update selector_map with current DOM
		logger.debug(f'Refreshing browser state before finding element')
		state = await browser.get_browser_state_summary(include_screenshot=False, cached=False)

		if not state.dom_state or not state.dom_state.selector_map:
			raise ValueError('No DOM state available')

		selector_map = state.dom_state.selector_map

		# Strategy 1: Try by index first (fastest)
		node = await browser.get_element_by_index(index)
		if node is not None:
			logger.info(f'✓ Found element by index {index}')
			return node

		logger.info(f'Element not found by index {index}, trying alternative strategies...')

		# Strategy 2: Try by element_id (most reliable)
		if element_id:
			logger.info(f'Trying by element_id: {element_id}')
			for idx, mapped_node in selector_map.items():
				if hasattr(mapped_node, 'attributes') and mapped_node.attributes:
					if mapped_node.attributes.get('id') == element_id:
						logger.info(f'✓ Found element by ID at index {idx}')
						return mapped_node

		# Strategy 3: Try by xpath
		if xpath:
			logger.info(f'Trying by xpath: {xpath[:100]}...')
			for idx, mapped_node in selector_map.items():
				if hasattr(mapped_node, 'xpath') and mapped_node.xpath == xpath:
					logger.info(f'✓ Found element by xpath at index {idx}')
					return mapped_node

		# Strategy 4: Try by text content similarity (for extract operations)
		if expected_text:
			logger.info(f'Trying by text similarity: {expected_text[:50]}...')
			best_match = None
			best_score = 0

			for idx, mapped_node in selector_map.items():
				# Get node text
				node_text = None
				if hasattr(mapped_node, 'attributes') and mapped_node.attributes:
					node_text = (
						mapped_node.attributes.get('value', '')
						or mapped_node.attributes.get('innerText', '')
						or mapped_node.attributes.get('textContent', '')
					)
				if not node_text and hasattr(mapped_node, 'node_value'):
					node_text = mapped_node.node_value

				if node_text:
					# Simple similarity: check if expected text is substring or vice versa
					if expected_text in node_text or node_text in expected_text:
						score = len(expected_text) / max(len(node_text), 1)
						if score > best_score:
							best_score = score
							best_match = (idx, mapped_node)

			if best_match and best_score > 0.3:  # At least 30% similarity
				idx, node = best_match
				logger.info(f'✓ Found element by text similarity at index {idx} (score: {best_score:.2f})')
				return node

		# Strategy 5: Try by tag + class combination
		if tag_name and element_class:
			logger.info(f'Trying by tag+class: {tag_name}.{element_class}')
			for idx, mapped_node in selector_map.items():
				if hasattr(mapped_node, 'tag_name') and mapped_node.tag_name == tag_name:
					if hasattr(mapped_node, 'attributes') and mapped_node.attributes:
						if mapped_node.attributes.get('class') == element_class:
							logger.info(f'✓ Found element by tag+class at index {idx}')
							return mapped_node

		# All strategies failed
		error_msg = f'Element not found after trying all strategies:\n'
		error_msg += f'  - index: {index}\n'
		if element_id:
			error_msg += f'  - element_id: {element_id}\n'
		if xpath:
			error_msg += f'  - xpath: {xpath[:100]}...\n'
		if expected_text:
			error_msg += f'  - expected_text: {expected_text[:100]}...\n'

		raise ValueError(error_msg)

	def _inject_params(self, step_params: dict, user_params: dict) -> dict:
		"""Inject user parameters into step parameters.

		Args:
			step_params: Original step parameters
			user_params: User-provided parameters

		Returns:
			Parameters with injected values
		"""
		injected = step_params.copy()

		# Replace {param:name} placeholders with actual values
		for key, value in injected.items():
			if isinstance(value, str) and '{param:' in value:
				# Extract parameter name
				import re

				matches = re.findall(r'\{param:(\w+)\}', value)
				for param_name in matches:
					if param_name in user_params:
						value = value.replace(f'{{param:{param_name}}}', str(user_params[param_name]))
				injected[key] = value

		return injected

	async def _execute_action(
		self, browser: BrowserSession, action: ActionType, params: dict, config: ExecutorConfig
	) -> list[Artifact]:
		"""Execute a single action.

		Args:
			browser: Browser session
			action: Action type
			params: Action parameters
			config: Executor configuration

		Returns:
			List of artifacts produced by this action
		"""
		artifacts = []

		try:
			if action == ActionType.GOTO:
				url = params.get('url', '')
				# Use event bus for navigation
				event = browser.event_bus.dispatch(NavigateToUrlEvent(url=url, new_tab=False))
				await event
				await event.event_result(raise_if_any=True, raise_if_none=False)
				await asyncio.sleep(2)  # Wait for page load

			elif action == ActionType.CLICK:
				# Find element (tries index, falls back to xpath)
				node = await self._find_element(browser, params)

				# Use event bus for click
				event = browser.event_bus.dispatch(ClickElementEvent(node=node, while_holding_ctrl=False))
				await event
				await event.event_result(raise_if_any=True, raise_if_none=False)
				await asyncio.sleep(1)  # Wait after click

			elif action == ActionType.INPUT:
				text = params.get('text', '')

				# Find element (tries index, falls back to xpath)
				node = await self._find_element(browser, params)

				# Use event bus for input
				event = browser.event_bus.dispatch(TypeTextEvent(node=node, text=text, clear=True))
				await event
				await event.event_result(raise_if_any=True, raise_if_none=False)
				await asyncio.sleep(0.5)

			elif action == ActionType.SCROLL:
				direction = params.get('direction', 'down')
				amount = params.get('amount', 500)

				# Use event bus for scroll (None node = scroll page)
				event = browser.event_bus.dispatch(ScrollEvent(direction=direction, amount=amount, node=None))
				await event
				await event.event_result(raise_if_any=True, raise_if_none=False)
				await asyncio.sleep(0.5)

			elif action == ActionType.WAIT:
				duration_ms = params.get('duration_ms', 1000)
				await asyncio.sleep(duration_ms / 1000)

			elif action == ActionType.SCREENSHOT:
				# Use event bus for screenshot
				event = browser.event_bus.dispatch(ScreenshotEvent())
				await event
				screenshot_base64 = await event.event_result(raise_if_any=True, raise_if_none=False)

				if screenshot_base64:
					artifacts.append(
						Artifact(
							type=ArtifactType.SCREENSHOT,
							name=f'screenshot_{int(time.time())}.png',
							content=screenshot_base64,  # Already base64 encoded
						)
					)

			elif action == ActionType.EXTRACT:
				query = params.get('query', '')
				is_final_result = params.get('is_final_result', False)

				if query:
					# Semantic extraction using browser-use's extract with LLM
					logger.info(f'Extracting using semantic query: "{query}"')

					try:
						# Import browser-use Tools for extract functionality
						from browser_use.tools.service import Tools

						# Create a default LLM for extraction
						# Using environment variables for API keys
						import os

						from langchain_anthropic import ChatAnthropic  # type: ignore
						from langchain_openai import ChatOpenAI  # type: ignore

						# Try to get LLM from environment
						if os.getenv('ANTHROPIC_API_KEY'):
							llm = ChatAnthropic(model='claude-3-5-sonnet-20241022', timeout=25, stop=None)
						elif os.getenv('OPENAI_API_KEY'):
							llm = ChatOpenAI(model='gpt-4o')
						else:
							raise ValueError('No LLM API key found in environment (ANTHROPIC_API_KEY or OPENAI_API_KEY)')

						# Create Tools instance and FileSystem
						from browser_use.utils import FileSystem

						tools_instance = Tools()
						file_system = FileSystem()

						# Call extract method directly (Tools.extract is a registered action)
						result = await tools_instance.extract(  # type: ignore
							query=query, browser_session=browser, page_extraction_llm=llm, file_system=file_system
						)

						# Extract the content from ActionResult
						# The result comes as: <url>...</url><query>...</query><result>...</result>
						text_content = result.extracted_content if hasattr(result, 'extracted_content') else str(result)

						# Parse the <result> tag to get just the extracted value
						import re

						result_match = re.search(r'<result>\s*(.*?)\s*</result>', text_content, re.DOTALL)
						if result_match:
							text_content = result_match.group(1).strip()
							logger.info(f'Parsed result from extract: {text_content[:200]}...')
						else:
							logger.warning(f'Could not parse <result> tag from extract output')

						logger.info(f'Semantically extracted: {text_content[:200]}...')

						artifact_metadata = {
							'is_final_result': is_final_result,
							'description': query,
							'extraction_method': 'semantic_query',
						}

					except Exception as e:
						logger.error(f'Semantic extraction failed: {e}', exc_info=True)
						# Fallback: extract whole page
						state = await browser.get_browser_state_summary(include_screenshot=False)
						text_content = state.dom_state.llm_representation() if state.dom_state else ''
						artifact_metadata = {
							'is_final_result': is_final_result,
							'description': query,
							'extraction_method': 'fallback_full_page',
							'error': str(e),
						}

				else:
					# Extract whole page
					logger.info('Extracting full page content')
					state = await browser.get_browser_state_summary(include_screenshot=False)
					text_content = state.dom_state.llm_representation() if state.dom_state else ''
					artifact_metadata = {'is_final_result': False, 'extraction_method': 'full_page'}

				artifacts.append(
					Artifact(
						type=ArtifactType.TEXT,
						name=f'extracted_content_{int(time.time())}.txt',
						content=text_content,
						metadata=artifact_metadata,
					)
				)

			# Take screenshot if configured
			if config.save_screenshots and action != ActionType.SCREENSHOT:
				event = browser.event_bus.dispatch(ScreenshotEvent())
				await event
				screenshot_base64 = await event.event_result(raise_if_any=True, raise_if_none=False)

				if screenshot_base64:
					artifacts.append(
						Artifact(
							type=ArtifactType.SCREENSHOT,
							name=f'step_{action.value}_{int(time.time())}.png',
							content=screenshot_base64,
						)
					)

		except Exception as e:
			logger.error(f'Action {action.value} failed: {str(e)}')
			raise

		return artifacts
