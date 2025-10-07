"""Test interactive mapping with extract."""
import asyncio
import httpx
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = 'http://localhost:8000/api/v1'


async def test_interactive_mapping():
	"""Test the full interactive mapping flow."""
	async with httpx.AsyncClient(timeout=300.0) as client:
		# Start mapping session
		logger.info('=== Starting Mapping Session ===')
		response = await client.post(
			f'{API_BASE_URL}/mapping/start',
			json={
				'objective': 'pegar o valor do iptu no site https://iportal.rio.rj.gov.br/PF331IPTUATUAL/',
				'tags': ['iptu', 'rio'],
			},
		)
		session_data = response.json()
		session_id = session_data['session_id']
		logger.info(f'✓ Session started: {session_id}')

		# Monitor session via SSE
		logger.info('\n=== Monitoring Session Events ===')
		input_requests = []

		async with client.stream('GET', f'{API_BASE_URL}/mapping/sessions/{session_id}/events') as stream_response:
			async for line in stream_response.aiter_lines():
				if line.startswith('data: '):
					data = json.loads(line[6:])
					event_type = data.get('type')

					logger.info(f'Event: {event_type}')

					if event_type == 'input_request':
						# Agent is asking for input
						input_req = data['data']
						logger.info(f'  ↳ Input needed: {input_req["field_label"]}')
						logger.info(f'    Prompt: {input_req["prompt"]}')

						# Provide test value
						test_value = '0.000.001-8'
						logger.info(f'  → Providing value: {test_value}')

						await client.post(
							f'{API_BASE_URL}/mapping/sessions/{session_id}/input', json={'value': test_value}
						)

					elif event_type == 'action':
						action_data = data['data']
						logger.info(f'  ↳ Action: {action_data.get("action")} - {action_data.get("description", "")}')

					elif event_type == 'completed':
						logger.info('✓ Mapping completed!')
						result = data['data']
						logger.info(f'  Success: {result.get("success")}')
						logger.info(f'  Steps: {result.get("steps_completed")}')

						# Check if result_location was marked
						result_location = result.get('metadata', {}).get('result_location')
						if result_location:
							logger.info(f'  ✓ Result location marked: {result_location}')
						else:
							logger.warning('  ⚠ No result location marked!')

						break

					elif event_type == 'error':
						logger.error(f'  ✗ Error: {data.get("data", {}).get("error")}')
						break

		# Create plan from mapping
		logger.info('\n=== Creating Plan ===')
		response = await client.post(f'{API_BASE_URL}/mapping/sessions/{session_id}/create-plan')
		plan = response.json()

		logger.info(f'✓ Plan created: {plan["metadata"]["plan_id"]}')
		logger.info(f'  Name: {plan["metadata"]["name"]}')
		logger.info(f'  Steps: {len(plan["steps"])}')
		logger.info(f'  Expected output: {plan["metadata"].get("expected_output")}')

		# Check for EXTRACT step
		extract_steps = [s for s in plan['steps'] if s['action'] == 'extract']
		if extract_steps:
			logger.info(f'\n✅ EXTRACT STEP FOUND!')
			for step in extract_steps:
				logger.info(f'  Step {step["sequence_id"]}: {step["description"]}')
				logger.info(f'  Params: {step["params"]}')
		else:
			logger.warning('\n⚠️  NO EXTRACT STEP - Agent did not call extract()!')

		# List all steps
		logger.info('\n=== All Plan Steps ===')
		for step in plan['steps']:
			logger.info(f'{step["sequence_id"]}: {step["action"]} - {step["description"]}')

		return len(extract_steps) > 0


if __name__ == '__main__':
	has_extract = asyncio.run(test_interactive_mapping())
	exit(0 if has_extract else 1)
