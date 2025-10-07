"""Data models for the Executor component."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutorConfig(BaseModel):
	"""Configuration for the Executor."""

	model_config = ConfigDict(extra='forbid')

	headless: bool = Field(default=True, description='Run browser in headless mode')
	timeout_seconds: int = Field(default=60, description='Overall execution timeout')
	step_timeout_ms: int = Field(default=10000, description='Timeout per step in milliseconds')
	save_screenshots: bool = Field(default=True, description='Save screenshots during execution')
	screenshot_on_error: bool = Field(default=True, description='Take screenshot when error occurs')
	retry_on_error: bool = Field(default=True, description='Retry failed steps once')


class ExecutePlanRequest(BaseModel):
	"""Request to execute a plan."""

	model_config = ConfigDict(extra='forbid')

	plan_id: str = Field(description='ID of the plan to execute')
	params: dict[str, Any] = Field(default_factory=dict, description='Parameters to inject into the plan')
	config_overrides: ExecutorConfig | None = Field(default=None, description='Override default executor config')
