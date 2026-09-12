from strands.models import BedrockModel
from strands.models.model import Model

from app.core.config import Settings

STRANDS_VERSION = "1.55.1"


def create_agent_model(settings: Settings) -> Model:
    """Create Relay's production Strands model through the normal AWS credential chain."""
    if settings.agent_model_provider != "bedrock":
        raise ValueError(f"Unsupported agent model provider: {settings.agent_model_provider}")
    return BedrockModel(
        model_id=settings.agent_model_id,
        region_name=settings.aws_region,
        temperature=0.0,
        streaming=True,
    )
