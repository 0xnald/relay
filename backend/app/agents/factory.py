from collections.abc import Sequence

from pydantic import BaseModel
from strands import Agent
from strands.models.model import Model

from app.agents.model import create_agent_model
from app.agents.prompts import COORDINATION_PROMPT, EXCEPTION_PROMPT, INTAKE_PROMPT
from app.core.config import Settings
from app.observability.agents import AgentTelemetry, SafeAgentHooks


class AgentFactory:
    def __init__(
        self,
        settings: Settings,
        *,
        model: Model | None = None,
        telemetry: AgentTelemetry | None = None,
    ) -> None:
        self._settings = settings
        self._model = model
        self._telemetry = telemetry

    @property
    def model_provider(self) -> str:
        return self._settings.agent_model_provider

    @property
    def model_id(self) -> str:
        return self._settings.agent_model_id

    def _model_for_agent(self) -> Model:
        return self._model or create_agent_model(self._settings)

    def create_intake_agent(
        self, output_model: type[BaseModel], *, telemetry: AgentTelemetry | None = None
    ) -> Agent:
        return Agent(
            model=self._model_for_agent(),
            name="relay-intake",
            description="Extracts structured donation intake facts.",
            system_prompt=INTAKE_PROMPT,
            structured_output_model=output_model,
            hooks=[SafeAgentHooks(telemetry or self._telemetry)],
            callback_handler=None,
        )

    def create_coordination_agent(
        self,
        *,
        tools: Sequence[object],
        output_model: type[BaseModel],
        telemetry: AgentTelemetry | None = None,
    ) -> Agent:
        return Agent(
            model=self._model_for_agent(),
            name="relay-coordination",
            description="Proposes bounded rescue coordination actions.",
            system_prompt=COORDINATION_PROMPT,
            tools=list(tools),
            structured_output_model=output_model,
            hooks=[SafeAgentHooks(telemetry or self._telemetry)],
            callback_handler=None,
        )

    def create_exception_agent(
        self, output_model: type[BaseModel], *, telemetry: AgentTelemetry | None = None
    ) -> Agent:
        return Agent(
            model=self._model_for_agent(),
            name="relay-exception",
            description="Selects among deterministic permitted recovery strategies.",
            system_prompt=EXCEPTION_PROMPT,
            structured_output_model=output_model,
            hooks=[SafeAgentHooks(telemetry or self._telemetry)],
            callback_handler=None,
        )
