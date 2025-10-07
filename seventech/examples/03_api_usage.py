"""API usage example.

This example demonstrates how to use the SevenTech API
to create and execute automation plans via HTTP endpoints.

Before running this example:
1. Start the API server: python -m uvicorn seventech.api.server:app --reload
2. The server will run at http://localhost:8000
"""

import asyncio
import logging

import httpx

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = 'http://localhost:8000/api/v1'


async def example_workflow():
	"""Complete API workflow example."""

	async with httpx.AsyncClient(timeout=300.0) as client:
		# ============ STEP 1: MAP & CREATE PLAN ============
		logger.info('=== STEP 1: MAPPING & CREATING PLAN ===')

		map_request = {
			'objective': 'Go to wikipedia.org and search for "Python programming"',
			'starting_url': 'https://wikipedia.org',
			'tags': ['wikipedia', 'search'],
			'plan_name': 'wikipedia_search',
		}

		response = await client.post(f'{API_BASE_URL}/workflow/map-plan-save', json=map_request)

		if response.status_code != 200:
			logger.error(f'Failed to create plan: {response.text}')
			return

		workflow_result = response.json()
		plan_id = workflow_result['plan_id']

		logger.info(f'✓ Plan created: {plan_id}')

		# ============ STEP 2: LIST PLANS ============
		logger.info('=== STEP 2: LISTING PLANS ===')

		response = await client.get(f'{API_BASE_URL}/plans')
		plans = response.json()

		logger.info(f'Total plans: {len(plans)}')
		for plan in plans:
			logger.info(f'  - {plan["metadata"]["name"]}: {plan["metadata"]["plan_id"]}')

		# ============ STEP 3: GET SPECIFIC PLAN ============
		logger.info('=== STEP 3: RETRIEVING PLAN DETAILS ===')

		response = await client.get(f'{API_BASE_URL}/plans/{plan_id}')
		plan_details = response.json()

		logger.info(f'Plan: {plan_details["metadata"]["name"]}')
		logger.info(f'Steps: {len(plan_details["steps"])}')
		logger.info(f'Required params: {plan_details["metadata"]["required_params"]}')

		# ============ STEP 4: EXECUTE PLAN ============
		logger.info('=== STEP 4: EXECUTING PLAN (NO LLM) ===')

		# Parameters to inject (if plan requires any)
		execution_params = {
			# Example: 'search_term': 'Python programming'
		}

		response = await client.post(f'{API_BASE_URL}/execute/{plan_id}', json=execution_params)

		if response.status_code != 200:
			logger.error(f'Execution failed: {response.text}')
			return

		result = response.json()

		logger.info(f'✓ Execution completed: {result["status"]}')
		logger.info(f'  Steps: {result["steps_completed"]}/{result["total_steps"]}')
		logger.info(f'  Time: {result["execution_time_ms"]}ms')
		logger.info(f'  Execution ID: {result["execution_id"]}')

		# ============ STEP 5: LIST EXECUTIONS ============
		logger.info('=== STEP 5: LISTING EXECUTION HISTORY ===')

		response = await client.get(f'{API_BASE_URL}/executions?plan_id={plan_id}')
		executions = response.json()

		logger.info(f'Total executions for this plan: {len(executions)}')
		for execution in executions:
			logger.info(
				f'  - {execution["execution_id"]}: {execution["status"]} ({execution["execution_time_ms"]}ms)'
			)

		# ============ STEP 6: SEARCH PLANS ============
		logger.info('=== STEP 6: SEARCHING PLANS ===')

		response = await client.get(f'{API_BASE_URL}/plans/search?query=wikipedia')
		search_results = response.json()

		logger.info(f'Plans matching "wikipedia": {len(search_results)}')

		logger.info('=== WORKFLOW COMPLETE ===')


async def execute_existing_plan_via_api(plan_id: str, params: dict | None = None):
	"""Execute an existing plan via API.

	Args:
		plan_id: ID of the plan to execute
		params: Parameters to inject
	"""
	async with httpx.AsyncClient(timeout=60.0) as client:
		response = await client.post(f'{API_BASE_URL}/execute/{plan_id}', json=params or {})

		if response.status_code == 404:
			logger.error(f'Plan not found: {plan_id}')
			return None

		if response.status_code != 200:
			logger.error(f'Execution failed: {response.text}')
			return None

		result = response.json()
		logger.info(f'Execution {result["execution_id"]}: {result["status"]}')

		return result


async def main():
	"""Main entry point."""
	logger.info('SevenTech API Usage Example')
	logger.info('Make sure the API server is running at http://localhost:8000')
	logger.info('')

	try:
		# Run complete workflow
		await example_workflow()

		# Example: Execute specific plan (uncomment to use)
		# await execute_existing_plan_via_api('your-plan-id-here', {'param': 'value'})

	except httpx.ConnectError:
		logger.error('Could not connect to API server.')
		logger.error('Start the server with: python -m uvicorn seventech.api.server:app --reload')


if __name__ == '__main__':
	asyncio.run(main())
