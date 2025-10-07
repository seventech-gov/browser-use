"""Complete API client example - Interactive mapping + Execution via HTTP API.

This example demonstrates how to use the SevenTech API as an external client:
1. Start an interactive mapping session
2. Monitor session status via SSE (Server-Sent Events)
3. Provide input when the mapper requests it
4. Create a plan from the completed session
5. Execute the plan with parameters

This is how external clients/customers would use the SevenTech platform.

BEFORE RUNNING:
    uv run uvicorn seventech.api.server:app --reload
"""

import asyncio
import json
import logging

import httpx
from httpx_sse import aconnect_sse

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = 'http://localhost:8000/api/v1'


async def interactive_mapping_workflow():
	"""Complete workflow: Interactive mapping → Plan creation → Execution."""

	async with httpx.AsyncClient(timeout=600.0) as client:
		# ==================== STEP 1: START MAPPING SESSION ====================
		logger.info('='*60)
		logger.info('STEP 1: Starting interactive mapping session')
		logger.info('='*60)

		mapping_request = {
			'objective': (
				'Ir para https://iportal.rio.rj.gov.br/PF331IPTUATUAL/ '
				'e consultar o valor do IPTU. '
				'Quando encontrar o campo de inscrição imobiliária, '
				'use ask_user_for_input para solicitar ao usuário.'
			),
			'tags': ['iptu', 'rio', 'consulta'],
			'plan_name': 'consulta_iptu_rio',
		}

		response = await client.post(f'{API_BASE_URL}/mapping/start', json=mapping_request)

		if response.status_code != 200:
			logger.error(f'Failed to start mapping: {response.text}')
			return

		start_result = response.json()
		session_id = start_result['session_id']

		logger.info(f'✅ Session started: {session_id}')
		logger.info(f'   SSE URL: {start_result["sse_url"]}')
		logger.info(f'   Status URL: {start_result["status_url"]}')

		# ==================== STEP 2: MONITOR SESSION VIA SSE ====================
		logger.info('\n' + '='*60)
		logger.info('STEP 2: Monitoring session via Server-Sent Events')
		logger.info('='*60)

		# Start SSE monitoring in background
		sse_task = asyncio.create_task(monitor_session_sse(client, session_id))

		# ==================== STEP 3: POLL AND PROVIDE INPUT ====================
		logger.info('\n' + '='*60)
		logger.info('STEP 3: Polling session status and providing input when needed')
		logger.info('='*60)

		# Poll session status until completion
		while True:
			await asyncio.sleep(3)  # Poll every 3 seconds

			# Get session status
			response = await client.get(f'{API_BASE_URL}/mapping/sessions/{session_id}')
			if response.status_code != 200:
				logger.error('Failed to get session status')
				break

			session_state = response.json()
			logger.info(f'Session status: {session_state["status"]}')

			# Check if input is needed
			if session_state['status'] == 'waiting_for_input':
				input_request = session_state.get('current_input_request')
				if input_request:
					logger.info('\n🤔 MAPPER NEEDS INPUT!')
					logger.info(f'   Field: {input_request["field_label"]}')
					logger.info(f'   Prompt: {input_request["prompt"]}')
					if input_request.get('placeholder'):
						logger.info(f'   Example: {input_request["placeholder"]}')

					# Simulate user providing input (in real app, this would be from UI)
					user_value = input(f'\n✏️  Digite o valor para "{input_request["field_label"]}": ')

					# Provide input via API
					input_response = await client.post(
						f'{API_BASE_URL}/mapping/sessions/{session_id}/input',
						json={'value': user_value}
					)

					if input_response.status_code == 200:
						logger.info('✅ Input provided, session continuing...')
					else:
						logger.error(f'Failed to provide input: {input_response.text}')

			# Check if session completed
			elif session_state['status'] in ['completed', 'failed', 'cancelled']:
				logger.info(f'\nSession ended with status: {session_state["status"]}')
				break

		# Wait for SSE task to complete
		sse_task.cancel()

		if session_state['status'] != 'completed':
			logger.error('Mapping session did not complete successfully')
			return

		# ==================== STEP 4: CREATE PLAN ====================
		logger.info('\n' + '='*60)
		logger.info('STEP 4: Creating plan from completed session')
		logger.info('='*60)

		response = await client.post(
			f'{API_BASE_URL}/mapping/sessions/{session_id}/create-plan',
			params={'plan_name': 'consulta_iptu_rio'}
		)

		if response.status_code != 200:
			logger.error(f'Failed to create plan: {response.text}')
			return

		plan = response.json()
		plan_id = plan['metadata']['plan_id']

		logger.info(f'✅ Plan created: {plan_id}')
		logger.info(f'   Name: {plan["metadata"]["name"]}')
		logger.info(f'   Steps: {len(plan["steps"])}')
		logger.info(f'   Required parameters: {plan["metadata"]["required_params"]}')

		# Show collected parameters
		logger.info('\n📊 Collected Parameters:')
		for param in session_state.get('collected_parameters', []):
			logger.info(f'   • {param["label"]}: {param["name"]}')

		# ==================== STEP 5: EXECUTE PLAN ====================
		logger.info('\n' + '='*60)
		logger.info('STEP 5: Executing plan (NO LLM - deterministic!)')
		logger.info('='*60)

		# Prepare parameters for execution
		execution_params = {}
		for param_name in plan['metadata']['required_params']:
			value = input(f'Digite o valor para "{param_name}": ')
			execution_params[param_name] = value

		logger.info(f'Executing plan with params: {execution_params}')

		response = await client.post(
			f'{API_BASE_URL}/execute/{plan_id}',
			json=execution_params
		)

		if response.status_code != 200:
			logger.error(f'Execution failed: {response.text}')
			return

		result = response.json()

		logger.info(f'\n✅ Execution completed!')
		logger.info(f'   Status: {result["status"]}')
		logger.info(f'   Steps completed: {result["steps_completed"]}/{result["total_steps"]}')
		logger.info(f'   Execution time: {result["execution_time_ms"]}ms')
		logger.info(f'   Artifacts: {len(result["artifacts"])}')
		logger.info(f'   Execution ID: {result["execution_id"]}')

		# ==================== STEP 6: RE-EXECUTE PLAN ====================
		logger.info('\n' + '='*60)
		logger.info('STEP 6: Re-executing plan with different parameters')
		logger.info('='*60)

		# Execute again with different parameters (showing reusability)
		new_params = {}
		for param_name in plan['metadata']['required_params']:
			value = input(f'Digite NOVO valor para "{param_name}": ')
			new_params[param_name] = value

		response = await client.post(
			f'{API_BASE_URL}/execute/{plan_id}',
			json=new_params
		)

		if response.status_code == 200:
			result2 = response.json()
			logger.info(f'✅ Second execution completed: {result2["status"]}')
			logger.info(f'   Note: No LLM used! Instant execution!')

		# ==================== CLEANUP ====================
		logger.info('\n' + '='*60)
		logger.info('CLEANUP: Deleting mapping session')
		logger.info('='*60)

		await client.delete(f'{API_BASE_URL}/mapping/sessions/{session_id}')
		logger.info('✅ Session deleted')

		# ==================== SUMMARY ====================
		logger.info('\n' + '='*60)
		logger.info('🎉 WORKFLOW COMPLETE!')
		logger.info('='*60)
		logger.info(f'Plan ID: {plan_id}')
		logger.info(f'You can now execute this plan unlimited times via API!')
		logger.info(f'\nAPI Call:')
		logger.info(f'  POST {API_BASE_URL}/execute/{plan_id}')
		logger.info(f'  Body: {json.dumps(execution_params, indent=2)}')


async def monitor_session_sse(client: httpx.AsyncClient, session_id: str):
	"""Monitor session events via Server-Sent Events."""
	logger.info('📡 Connecting to SSE stream...')

	try:
		async with aconnect_sse(
			client,
			'GET',
			f'{API_BASE_URL}/mapping/sessions/{session_id}/events'
		) as event_source:
			async for sse in event_source.aiter_sse():
				logger.info(f'📨 SSE Event: {sse.event}')
				if sse.data and sse.data != '{}':
					data = json.loads(sse.data)
					logger.info(f'   Status: {data.get("status")}')

				if sse.event == 'close':
					break

	except asyncio.CancelledError:
		logger.info('📡 SSE monitoring stopped')
	except Exception as e:
		logger.error(f'SSE error: {e}')


async def list_available_plans():
	"""List all available plans via API."""
	async with httpx.AsyncClient() as client:
		response = await client.get(f'{API_BASE_URL}/plans')

		if response.status_code == 200:
			plans = response.json()
			logger.info(f'\n📋 Available Plans ({len(plans)}):')
			for plan in plans:
				logger.info(f'   • {plan["metadata"]["name"]} ({plan["metadata"]["plan_id"]})')
				logger.info(f'     Steps: {len(plan["steps"])}, Params: {plan["metadata"]["required_params"]}')


async def execute_existing_plan():
	"""Execute an existing plan by ID."""
	plan_id = input('Enter plan ID: ')
	params = {}

	async with httpx.AsyncClient() as client:
		# Get plan details
		response = await client.get(f'{API_BASE_URL}/plans/{plan_id}')

		if response.status_code == 404:
			logger.error(f'Plan not found: {plan_id}')
			return

		plan = response.json()
		logger.info(f'\nPlan: {plan["metadata"]["name"]}')
		logger.info(f'Required parameters: {plan["metadata"]["required_params"]}')

		# Collect parameters
		for param_name in plan['metadata']['required_params']:
			value = input(f'Enter value for {param_name}: ')
			params[param_name] = value

		# Execute
		logger.info(f'\nExecuting plan {plan_id}...')
		response = await client.post(
			f'{API_BASE_URL}/execute/{plan_id}',
			json=params
		)

		if response.status_code == 200:
			result = response.json()
			logger.info(f'\n✅ Execution: {result["status"]}')
			logger.info(f'   Time: {result["execution_time_ms"]}ms')
			logger.info(f'   Execution ID: {result["execution_id"]}')
		else:
			logger.error(f'Execution failed: {response.text}')


async def main():
	"""Main entry point."""
	logger.info('🚀 SevenTech API Client Example\n')
	logger.info('Make sure the API server is running:')
	logger.info('  uv run uvicorn seventech.api.server:app --reload\n')

	try:
		# Run complete workflow
		await interactive_mapping_workflow()

		# Show available plans
		# await list_available_plans()

		# Execute existing plan
		# await execute_existing_plan()

	except httpx.ConnectError:
		logger.error('❌ Could not connect to API server')
		logger.error('   Start the server with:')
		logger.error('   uv run uvicorn seventech.api.server:app --reload')
	except Exception as e:
		logger.error(f'❌ Error: {e}', exc_info=True)


if __name__ == '__main__':
	asyncio.run(main())
