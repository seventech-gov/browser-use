"""Parameter collector for tracking dynamic inputs during interactive mapping."""

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from uuid_extensions import uuid7str

logger = logging.getLogger(__name__)


class CollectedParameter(BaseModel):
	"""A parameter collected during interactive mapping."""

	model_config = ConfigDict(extra='forbid')

	param_id: str = Field(default_factory=uuid7str, description='Unique parameter identifier')
	name: str = Field(description='Parameter name (e.g., "inscricao_imobiliaria")')
	label: str = Field(description='Human-readable label (e.g., "Inscrição Imobiliária")')
	value: Any = Field(description='Value provided by user during mapping')
	xpath: str | None = Field(default=None, description='XPath where this parameter was used')
	description: str = Field(default='', description='Description of what this parameter is for')
	required: bool = Field(default=True, description='Whether this parameter is required')
	example: str | None = Field(default=None, description='Example value for documentation')
	collected_at_step: int | None = Field(default=None, description='Step number when collected')


class ParameterCollector:
	"""Collects and tracks parameters during interactive mapping sessions.

	During mapping, when the Agent needs user input (like CPF, inscrição, etc.),
	this collector records that parameter for later use in the plan.
	"""

	def __init__(self):
		"""Initialize the parameter collector."""
		self.parameters: dict[str, CollectedParameter] = {}
		self.collection_count = 0
		logger.info('ParameterCollector initialized')

	def collect(
		self,
		name: str,
		value: Any,
		label: str | None = None,
		xpath: str | None = None,
		description: str = '',
		example: str | None = None,
		step_number: int | None = None,
	) -> CollectedParameter:
		"""Record a parameter that was collected from user.

		Args:
			name: Parameter name (sanitized, e.g., "inscricao_imobiliaria")
			value: The value provided by user
			label: Human-readable label (e.g., "Inscrição Imobiliária")
			xpath: XPath selector where this parameter will be used
			description: Description of what this parameter is for
			example: Example value for documentation
			step_number: Step number when this was collected

		Returns:
			The collected parameter
		"""
		# Use label as name if not provided
		if not label:
			label = name.replace('_', ' ').title()

		# Check if parameter already exists - warn but update it
		if name in self.parameters:
			logger.warning(f'Parameter {name} already collected, updating with new value: {value}')

		param = CollectedParameter(
			name=name,
			label=label,
			value=value,
			xpath=xpath,
			description=description,
			example=example or str(value),
			collected_at_step=step_number,
		)

		self.parameters[name] = param
		self.collection_count += 1

		logger.info(f'Collected parameter: {name} = {value} (step {step_number})')

		return param

	def get_parameter(self, name: str) -> CollectedParameter | None:
		"""Get a collected parameter by name.

		Args:
			name: Parameter name

		Returns:
			The parameter or None if not found
		"""
		return self.parameters.get(name)

	def has_parameter(self, name: str) -> bool:
		"""Check if a parameter has been collected.

		Args:
			name: Parameter name

		Returns:
			True if parameter exists
		"""
		return name in self.parameters

	def list_parameters(self) -> list[CollectedParameter]:
		"""Get all collected parameters.

		Returns:
			List of collected parameters
		"""
		return list(self.parameters.values())

	def get_parameter_names(self) -> list[str]:
		"""Get names of all collected parameters.

		Returns:
			List of parameter names
		"""
		return list(self.parameters.keys())

	def clear(self):
		"""Clear all collected parameters."""
		self.parameters.clear()
		self.collection_count = 0
		logger.info('ParameterCollector cleared')

	def to_dict(self) -> dict[str, Any]:
		"""Export collected parameters to dictionary.

		Returns:
			Dictionary representation
		"""
		return {
			'parameters': [p.model_dump() for p in self.parameters.values()],
			'count': self.collection_count,
		}

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> 'ParameterCollector':
		"""Create collector from dictionary.

		Args:
			data: Dictionary with parameters

		Returns:
			ParameterCollector instance
		"""
		collector = cls()
		for param_data in data.get('parameters', []):
			param = CollectedParameter.model_validate(param_data)
			collector.parameters[param.name] = param
		collector.collection_count = data.get('count', len(collector.parameters))
		return collector
