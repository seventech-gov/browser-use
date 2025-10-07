"""Data models for the Mapper component."""

from pydantic import BaseModel, ConfigDict, Field


class MapperConfig(BaseModel):
	"""Configuration for the Mapper."""

	model_config = ConfigDict(extra='forbid')

	headless: bool = Field(default=False, description='Run browser in headless mode')
	max_steps: int = Field(default=100, description='Maximum steps for agent to take')
	timeout_seconds: int = Field(default=300, description='Timeout for mapping operation')
	save_screenshots: bool = Field(default=True, description='Save screenshots during mapping')
	save_conversation: bool = Field(default=True, description='Save LLM conversation history')


class MapObjectiveRequest(BaseModel):
	"""Request to map a new objective."""

	model_config = ConfigDict(extra='forbid')

	objective: str = Field(description='Natural language description of the objective')
	starting_url: str | None = Field(default=None, description='Optional starting URL')
	tags: list[str] = Field(default_factory=list, description='Tags for categorization')
	plan_name: str | None = Field(default=None, description='Optional name for the plan')
