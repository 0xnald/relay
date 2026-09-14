"""Narrow AgentCore-compatible Relay Intake Agent entrypoint.

This module has no database or tool access. AgentCore only receives untrusted text
and returns Relay's validated structured intake result.
"""

from app.services.agentcore_intake import handle_agentcore_intake as handle_intake

__all__ = ["handle_intake"]
