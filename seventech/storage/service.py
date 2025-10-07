"""Storage service - manages persistence of plans and execution results."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from seventech.shared_views import ExecutionResult, Plan

logger = logging.getLogger(__name__)


class Storage:
	"""Handles storage and retrieval of plans and execution results.

	Uses JSON files for simple, portable storage. Can be extended to use
	databases for production scenarios.
	"""

	def __init__(self, storage_dir: Path | str = 'seventech/plans'):
		"""Initialize the Storage.

		Args:
			storage_dir: Directory to store plans and results
		"""
		self.storage_dir = Path(storage_dir)
		self.plans_dir = self.storage_dir / 'plans'
		self.results_dir = self.storage_dir / 'results'

		# Create directories if they don't exist
		self.plans_dir.mkdir(parents=True, exist_ok=True)
		self.results_dir.mkdir(parents=True, exist_ok=True)

		logger.info(f'Storage initialized at {self.storage_dir}')

	def save_plan(self, plan: Plan) -> str:
		"""Save a plan to storage.

		Args:
			plan: Plan to save

		Returns:
			Plan ID

		Raises:
			IOError: If save operation fails
		"""
		plan_id = plan.metadata.plan_id
		plan_path = self.plans_dir / f'{plan_id}.json'

		try:
			# Update timestamp
			plan.metadata.updated_at = datetime.now(timezone.utc).isoformat()

			# Save to JSON
			with open(plan_path, 'w') as f:
				json.dump(plan.model_dump(), f, indent=2)

			logger.info(f'Plan saved: {plan_id} at {plan_path}')
			return plan_id

		except Exception as e:
			logger.error(f'Failed to save plan {plan_id}: {str(e)}')
			raise IOError(f'Failed to save plan: {str(e)}') from e

	def load_plan(self, plan_id: str) -> Plan:
		"""Load a plan from storage.

		Args:
			plan_id: ID of the plan to load

		Returns:
			The loaded plan

		Raises:
			FileNotFoundError: If plan doesn't exist
			ValueError: If plan data is invalid
		"""
		plan_path = self.plans_dir / f'{plan_id}.json'

		if not plan_path.exists():
			raise FileNotFoundError(f'Plan not found: {plan_id}')

		try:
			with open(plan_path, 'r') as f:
				plan_data = json.load(f)

			plan = Plan.model_validate(plan_data)
			logger.info(f'Plan loaded: {plan_id}')
			return plan

		except Exception as e:
			logger.error(f'Failed to load plan {plan_id}: {str(e)}')
			raise ValueError(f'Invalid plan data: {str(e)}') from e

	def list_plans(self, tags: list[str] | None = None) -> list[Plan]:
		"""List all plans, optionally filtered by tags.

		Args:
			tags: Optional list of tags to filter by

		Returns:
			List of plans
		"""
		plans = []

		for plan_path in self.plans_dir.glob('*.json'):
			try:
				plan = self.load_plan(plan_path.stem)

				# Filter by tags if provided
				if tags:
					if not any(tag in plan.metadata.tags for tag in tags):
						continue

				plans.append(plan)

			except Exception as e:
				logger.warning(f'Failed to load plan from {plan_path}: {e}')
				continue

		logger.info(f'Listed {len(plans)} plans')
		return plans

	def search_plans(self, query: str) -> list[Plan]:
		"""Search plans by name or description.

		Args:
			query: Search query

		Returns:
			List of matching plans
		"""
		query_lower = query.lower()
		plans = self.list_plans()

		matching_plans = [
			plan
			for plan in plans
			if query_lower in plan.metadata.name.lower() or query_lower in plan.metadata.description.lower()
		]

		logger.info(f'Found {len(matching_plans)} plans matching "{query}"')
		return matching_plans

	def delete_plan(self, plan_id: str) -> bool:
		"""Delete a plan from storage.

		Args:
			plan_id: ID of the plan to delete

		Returns:
			True if deleted successfully
		"""
		plan_path = self.plans_dir / f'{plan_id}.json'

		if not plan_path.exists():
			logger.warning(f'Plan not found for deletion: {plan_id}')
			return False

		try:
			plan_path.unlink()
			logger.info(f'Plan deleted: {plan_id}')
			return True

		except Exception as e:
			logger.error(f'Failed to delete plan {plan_id}: {e}')
			return False

	def save_execution_result(self, result: ExecutionResult) -> str:
		"""Save an execution result.

		Args:
			result: Execution result to save

		Returns:
			Execution ID
		"""
		execution_id = result.execution_id
		result_path = self.results_dir / f'{execution_id}.json'

		try:
			with open(result_path, 'w') as f:
				json.dump(result.model_dump(), f, indent=2)

			logger.info(f'Execution result saved: {execution_id}')
			return execution_id

		except Exception as e:
			logger.error(f'Failed to save execution result {execution_id}: {e}')
			raise IOError(f'Failed to save execution result: {str(e)}') from e

	def load_execution_result(self, execution_id: str) -> ExecutionResult:
		"""Load an execution result.

		Args:
			execution_id: ID of the execution

		Returns:
			Execution result

		Raises:
			FileNotFoundError: If result doesn't exist
		"""
		result_path = self.results_dir / f'{execution_id}.json'

		if not result_path.exists():
			raise FileNotFoundError(f'Execution result not found: {execution_id}')

		try:
			with open(result_path, 'r') as f:
				result_data = json.load(f)

			result = ExecutionResult.model_validate(result_data)
			logger.info(f'Execution result loaded: {execution_id}')
			return result

		except Exception as e:
			logger.error(f'Failed to load execution result {execution_id}: {e}')
			raise ValueError(f'Invalid execution result data: {str(e)}') from e

	def list_execution_results(self, plan_id: str | None = None) -> list[ExecutionResult]:
		"""List execution results, optionally filtered by plan ID.

		Args:
			plan_id: Optional plan ID to filter by

		Returns:
			List of execution results
		"""
		results = []

		for result_path in self.results_dir.glob('*.json'):
			try:
				result = self.load_execution_result(result_path.stem)

				# Filter by plan_id if provided
				if plan_id and result.plan_id != plan_id:
					continue

				results.append(result)

			except Exception as e:
				logger.warning(f'Failed to load result from {result_path}: {e}')
				continue

		logger.info(f'Listed {len(results)} execution results')
		return results
