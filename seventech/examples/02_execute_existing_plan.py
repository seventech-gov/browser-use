"""Execute an existing plan example.

This example shows how to execute a previously created plan
without any LLM involvement. This is the production use case
where plans are created once and executed many times.
"""

import asyncio
import logging

from dotenv import load_dotenv

from seventech.executor.service import Executor
from seventech.executor.views import ExecutePlanRequest, ExecutorConfig
from seventech.storage.service import Storage

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def execute_plan_by_id(plan_id: str, params: dict | None = None):
	"""Execute a plan by its ID.

	Args:
		plan_id: ID of the plan to execute
		params: Parameters to inject into the plan
	"""
	logger.info(f'=== EXECUTING PLAN: {plan_id} ===')

	# Initialize services
	storage = Storage()
	executor = Executor(ExecutorConfig(headless=True, save_screenshots=True))

	# Load plan
	plan = storage.load_plan(plan_id)
	logger.info(f'Loaded plan: {plan.metadata.name}')
	logger.info(f'Description: {plan.metadata.description}')
	logger.info(f'Steps: {len(plan.steps)}')
	logger.info(f'Required params: {plan.metadata.required_params}')

	# Execute
	request = ExecutePlanRequest(plan_id=plan_id, params=params or {})

	result = await executor.execute_plan(plan, request)

	# Display results
	logger.info(f'✓ Execution completed: {result.status}')
	logger.info(f'  Steps completed: {result.steps_completed}/{result.total_steps}')
	logger.info(f'  Execution time: {result.execution_time_ms}ms')
	logger.info(f'  Artifacts produced: {len(result.artifacts)}')

	# Save result
	storage.save_execution_result(result)

	# Show artifacts
	for artifact in result.artifacts:
		logger.info(f'  - {artifact.type.value}: {artifact.name}')

	return result


async def list_and_execute():
	"""List available plans and execute one."""
	storage = Storage()

	# List all plans
	plans = storage.list_plans()
	logger.info(f'=== AVAILABLE PLANS ({len(plans)}) ===')

	for plan in plans:
		logger.info(f'  {plan.metadata.plan_id}: {plan.metadata.name}')
		logger.info(f'    Steps: {len(plan.steps)}, Params: {plan.metadata.required_params}')

	if not plans:
		logger.warning('No plans found. Create a plan first using 01_basic_workflow.py')
		return

	# Execute first plan as example
	first_plan = plans[0]
	logger.info(f'\nExecuting first plan: {first_plan.metadata.name}')

	# Example parameters (adjust based on your plan's requirements)
	example_params = {
		# 'username': 'user@example.com',
		# 'password': 'secretpassword',
	}

	await execute_plan_by_id(first_plan.metadata.plan_id, example_params)


async def main():
	"""Main entry point."""
	# Option 1: List plans and execute first one
	await list_and_execute()

	# Option 2: Execute specific plan by ID (uncomment to use)
	# await execute_plan_by_id('your-plan-id-here', {'param1': 'value1'})


if __name__ == '__main__':
	asyncio.run(main())
