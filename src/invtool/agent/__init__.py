"""Agent sub-package: Claude SDK integration (chat loop + deep research skills).

The former top-level `invtool.agent` module now lives in `invtool.agent.chat`.
We re-export its public symbols at the sub-package level so existing
`from invtool.agent import X` calls continue to work unchanged.
"""
from .chat import (
    TOOL_DEFINITIONS,
    set_data_provider,
    check_api_key,
    ai_chat_loop,
    _handle_tool,
    _ensure_provider,
)

__all__ = [
    "TOOL_DEFINITIONS",
    "set_data_provider",
    "check_api_key",
    "ai_chat_loop",
    "_handle_tool",
    "_ensure_provider",
]
