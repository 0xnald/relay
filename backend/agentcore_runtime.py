"""AgentCore HTTP wrapper for Relay's narrow intake runtime.

No persistence, tools, MCP clients, or conversational state are exposed here.
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from app.schemas.agentcore import AgentCoreIntakeRequest
from app.services.agentcore_intake import handle_agentcore_intake

app = BedrockAgentCoreApp()


@app.entrypoint
async def invoke(payload: object, context: object) -> dict[str, object]:
    request = AgentCoreIntakeRequest.model_validate(payload)
    session_id = getattr(context, "session_id", None)
    if isinstance(session_id, str):
        request = request.model_copy(update={"session_id": session_id})
    return (await handle_agentcore_intake(request)).model_dump(mode="json")


if __name__ == "__main__":
    app.run()
