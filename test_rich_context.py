"""Test rich context extraction."""
import asyncio
import httpx
import json
import logging

logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = 'http://localhost:8000/api/v1'


async def test_rich_context():
	"""Test if rich context is being captured and used."""
	async with httpx.AsyncClient(timeout=300.0) as client:
		# Start mapping session
		logger.info('=== Starting Mapping Session ===')
		response = await client.post(
			f'{API_BASE_URL}/mapping/start',
			json={
				'objective': 'pegar o valor do iptu no site https://iportal.rio.rj.gov.br/PF331IPTUATUAL/',
				'tags': ['iptu', 'test'],
			},
		)
		session_data = response.json()
		session_id = session_data['session_id']
		logger.info(f'Session ID: {session_id}')

		# Monitor until completion
		async with client.stream('GET', f'{API_BASE_URL}/mapping/sessions/{session_id}/events') as stream_response:
			async for line in stream_response.aiter_lines():
				if line.startswith('data: '):
					data = json.loads(line[6:])
					event_type = data.get('type')

					if event_type == 'input_request':
						# Provide input
						await client.post(
							f'{API_BASE_URL}/mapping/sessions/{session_id}/input', json={'value': '0.000.001-8'}
						)

					elif event_type == 'completed':
						logger.info('Mapping completed!')
						break

					elif event_type == 'error':
						logger.error(f'Error: {data}')
						break

		# Create plan
		logger.info('=== Creating Plan ===')
		response = await client.post(f'{API_BASE_URL}/mapping/sessions/{session_id}/create-plan')
		plan = response.json()

		plan_id = plan['metadata']['plan_id']
		logger.info(f'Plan ID: {plan_id}')

		# Check EXTRACT step
		extract_steps = [s for s in plan['steps'] if s['action'] == 'extract']
		if extract_steps:
			extract_step = extract_steps[0]
			logger.info('=== EXTRACT Step Params ===')
			for key, value in extract_step['params'].items():
				if isinstance(value, str) and len(value) > 100:
					logger.info(f'  {key}: {value[:100]}...')
				else:
					logger.info(f'  {key}: {value}')

			# Check what we have
			has_xpath = bool(extract_step['params'].get('xpath'))
			has_expected_text = bool(extract_step['params'].get('expected_text'))
			has_element_id = bool(extract_step['params'].get('element_id'))

			logger.info(f'\n=== Rich Context Check ===')
			logger.info(f'  xpath: {"✓" if has_xpath else "✗"}')
			logger.info(f'  expected_text: {"✓" if has_expected_text else "✗"}')
			logger.info(f'  element_id: {"✓" if has_element_id else "✗"}')

			if not (has_xpath or has_expected_text or has_element_id):
				logger.warning('\n⚠️  NO RICH CONTEXT CAPTURED!')
				logger.warning('This means element finding will rely only on index, which is fragile')
			else:
				logger.info('\n✓ Rich context available for robust element finding')

		# Execute the plan
		logger.info('\n=== Executing Plan ===')
		response = await client.post(
			f'{API_BASE_URL}/execute/{plan_id}', json={'inscricao_imobiliaria': '0.000.001-8'}
		)
		result = response.json()

		logger.info(f'Status: {result["status"]}')
		logger.info(f'Steps completed: {result["steps_completed"]}/{result["total_steps"]}')

		# Check final artifact
		final_artifacts = [a for a in result['artifacts'] if a.get('metadata', {}).get('is_final_result')]
		if final_artifacts:
			artifact = final_artifacts[0]
			content = artifact['content']
			logger.info(f'\n=== Final Result ===')
			logger.info(f'Content: "{content}"')
			logger.info(f'Length: {len(content)} chars')

			if not content or len(content) < 3:
				logger.error('⚠️  Content is empty or too short!')
			else:
				logger.info('✓ Content extracted successfully')


if __name__ == '__main__':
	asyncio.run(test_rich_context())
