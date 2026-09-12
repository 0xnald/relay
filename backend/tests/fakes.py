import json
from collections import deque
from collections.abc import AsyncGenerator, AsyncIterable, Iterable
from typing import Any, TypeVar

from pydantic import BaseModel
from strands.models.model import Model

T = TypeVar("T", bound=BaseModel)


class FakeStrandsModel(Model):
    """Deterministic Strands Model seam; production still uses BedrockModel."""

    def __init__(self, outputs: Iterable[BaseModel | dict[str, Any] | Exception]) -> None:
        self.outputs = deque(outputs)
        self.config: dict[str, Any] = {"model_id": "relay-test-model"}

    def update_config(self, **model_config: Any) -> None:
        self.config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return self.config.copy()

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Any,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        del prompt, system_prompt, kwargs
        output = self.outputs.popleft()
        if isinstance(output, Exception):
            raise output
        yield {"output": output_model.model_validate(output)}

    async def stream(self, *args: Any, **kwargs: Any) -> AsyncIterable[Any]:
        output = self.outputs.popleft()
        if isinstance(output, Exception):
            raise output
        tool_specs = args[1] if len(args) > 1 else kwargs.get("tool_specs")
        if tool_specs is None:
            raise AssertionError("Structured output tool was not registered")
        output_spec = tool_specs[-1]
        tool_name = output_spec["name"]
        payload = output.model_dump(mode="json") if isinstance(output, BaseModel) else output
        yield {"messageStart": {"role": "assistant"}}
        yield {
            "contentBlockStart": {
                "contentBlockIndex": 0,
                "start": {"toolUse": {"toolUseId": "structured-output-1", "name": tool_name}},
            }
        }
        yield {
            "contentBlockDelta": {
                "contentBlockIndex": 0,
                "delta": {"toolUse": {"input": json.dumps(payload)}},
            }
        }
        yield {"contentBlockStop": {"contentBlockIndex": 0}}
        yield {"messageStop": {"stopReason": "tool_use"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
                "metrics": {"latencyMs": 1},
            }
        }
