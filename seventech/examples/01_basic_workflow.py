"""Basic workflow example: Map → Plan → Execute.

This example demonstrates the complete workflow of:
1. Mapping an objective using the Mapper (with LLM)
2. Converting the mapping into a deterministic plan
3. Executing the plan (without LLM)
"""

import asyncio
import logging

from browser_use.llm.google.chat import ChatGoogle
from dotenv import load_dotenv

from seventech.executor.service import Executor
from seventech.executor.views import ExecutePlanRequest, ExecutorConfig
from seventech.mapper.service import Mapper
from seventech.mapper.views import MapObjectiveRequest, MapperConfig
from seventech.planner.service import Planner
from seventech.storage.service import Storage

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
	"""Run the complete workflow."""

	# ============ STEP 1: MAP OBJECTIVE ============
	logger.info('=== STEP 1: MAPPING OBJECTIVE ===')

	# Initialize Mapper with LLM
	llm = ChatGoogle(model='gemini-2.0-flash-exp')
	mapper = Mapper(llm, MapperConfig(headless=False, max_steps=20))

	# Define objective
	request = MapObjectiveRequest(
		objective='Go to google.com and search for "browser automation"',
		starting_url='https://google.com',
		tags=['google', 'search', 'demo'],
		plan_name='google_search_automation',
	)

	# Map the objective
	mapper_result = await mapper.map_objective(request)

	if not mapper_result.success:
		logger.error(f'Mapping failed: {mapper_result.error_message}')
		return

	logger.info('✓ Mapping completed successfully')

	# ============ STEP 2: CREATE PLAN ============
	logger.info('=== STEP 2: CREATING PLAN ===')

	planner = Planner()
	plan = planner.create_plan(mapper_result, plan_name=request.plan_name)

	logger.info(f'✓ Plan created: {plan.metadata.plan_id}')
	logger.info(f'  Steps: {len(plan.steps)}')
	logger.info(f'  Required params: {plan.metadata.required_params}')

	# ============ STEP 3: SAVE PLAN ============
	logger.info('=== STEP 3: SAVING PLAN ===')

	storage = Storage()
	plan_id = storage.save_plan(plan)

	logger.info(f'✓ Plan saved: {plan_id}')

	# ============ STEP 4: EXECUTE PLAN ============
	logger.info('=== STEP 4: EXECUTING PLAN (NO LLM) ===')

	executor = Executor(ExecutorConfig(headless=True))

	# Execute with parameters (if any required)
	execute_request = ExecutePlanRequest(plan_id=plan_id, params={})

	result = await executor.execute_plan(plan, execute_request)

	logger.info(f'✓ Execution completed: {result.status}')
	logger.info(f'  Steps completed: {result.steps_completed}/{result.total_steps}')
	logger.info(f'  Execution time: {result.execution_time_ms}ms')
	logger.info(f'  Artifacts: {len(result.artifacts)}')

	# Save result
	storage.save_execution_result(result)

	# ============ SUMMARY ============
	logger.info('=== WORKFLOW COMPLETE ===')
	logger.info(f'Plan ID: {plan_id}')
	logger.info(f'Execution ID: {result.execution_id}')
	logger.info('The plan can now be executed repeatedly without LLM!')


if __name__ == '__main__':
	asyncio.run(main())
