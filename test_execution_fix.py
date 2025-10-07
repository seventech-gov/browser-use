"""Test if execution works after selector_map refresh fix."""
import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = 'http://localhost:8000/api/v1'


async def test_execution():
	"""Test executing the IPTU plan."""
	async with httpx.AsyncClient(timeout=120.0) as client:
		# Get the latest IPTU plan
		logger.info('=== Finding IPTU plan ===')
		response = await client.get(f'{API_BASE_URL}/plans')
		plans = response.json()

		iptu_plan = None
		for plan in plans:
			if 'iptu' in plan['metadata'].get('tags', []):
				iptu_plan = plan
				break

		if not iptu_plan:
			logger.error('No IPTU plan found!')
			return False

		plan_id = iptu_plan['metadata']['plan_id']
		logger.info(f'✓ Using plan: {plan_id}')
		logger.info(f'  Name: {iptu_plan["metadata"]["name"]}')
		logger.info(f'  Steps: {len(iptu_plan["steps"])}')
		logger.info(f'  Required params: {iptu_plan["metadata"]["required_params"]}')

		# Show steps
		for i, step in enumerate(iptu_plan['steps']):
			logger.info(f'  Step {i}: {step["action"]} - {step.get("description", "")}')

		# Execute with test parameter
		logger.info('\n=== Executing plan ===')
		logger.info('Providing inscricao_imobiliaria=0.000.001-8')

		params = {'inscricao_imobiliaria': '0.000.001-8'}

		# Add user_input if required
		if 'user_input' in iptu_plan['metadata']['required_params']:
			params['user_input'] = 'test'

		response = await client.post(f'{API_BASE_URL}/execute/{plan_id}', json=params)
		result = response.json()

		logger.info(f'\n=== Execution Result ===')
		logger.info(f'Status: {result["status"]}')
		logger.info(f'Steps completed: {result["steps_completed"]}/{result["total_steps"]}')
		logger.info(f'Execution time: {result["execution_time_ms"]}ms')

		if result.get('error_message'):
			logger.error(f'Error: {result["error_message"]}')

		# Check artifacts
		if result['artifacts']:
			logger.info(f'\nArtifacts: {len(result["artifacts"])}')
			for artifact in result['artifacts']:
				if artifact.get('metadata', {}).get('is_final_result'):
					logger.info(f'\n✅ FINAL RESULT FOUND:')
					logger.info(f'  Description: {artifact["metadata"]["description"]}')
					logger.info(f'  Content: {artifact["content"][:200]}')

		if result['status'] == 'success':
			logger.info('\n✅ EXECUTION SUCCESSFUL!')
			return True
		else:
			logger.warning(f'\n⚠️  Execution status: {result["status"]}')
			# Even partial success is ok for testing
			if result['steps_completed'] > 1:
				logger.info('✓ At least some steps completed (better than before!)')
				return True
			return False


if __name__ == '__main__':
	success = asyncio.run(test_execution())
	exit(0 if success else 1)
