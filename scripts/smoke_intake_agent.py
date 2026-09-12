"""Run one explicitly opted-in Relay intake request against Amazon Bedrock."""

import asyncio
import json
import os
import sys
from uuid import uuid4

from app.agents.factory import AgentFactory
from app.core.config import get_settings
from app.services.intake import IntakeAgentService

OPT_IN_VARIABLE = "RELAY_RUN_LIVE_BEDROCK"
EXAMPLE = (
    "Market Square has about 36 prepared chicken meals and 12 bakery items left from "
    "today's event. Everything needs to be picked up by 6:30 PM from the loading bay. "
    "The chicken has been kept cold, but the preparation time is unknown."
)


async def main() -> int:
    if os.getenv(OPT_IN_VARIABLE) != "1":
        print(f"NOT RUN: set {OPT_IN_VARIABLE}=1 to authorize a live Bedrock request.")
        return 2

    settings = get_settings()
    print(
        json.dumps(
            {
                "provider": settings.agent_model_provider,
                "model_id": settings.agent_model_id,
                "region": settings.aws_region,
            },
            indent=2,
        )
    )
    result = await IntakeAgentService(AgentFactory(settings)).interpret(
        EXAMPLE,
        trace_id=f"bedrock-smoke-{uuid4()}",
        actor_identity="local-smoke-test",
    )
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
