"""Agent sub-package: Claude SDK integration.

Split into three modules:
  tools.py     — TOOL_DEFINITIONS (pure data)
  handlers.py  — _handle_tool and the DataProvider registration
  loop.py      — AGENT_SYSTEM_PROMPT and the interactive chat loop

Public symbols are re-exported here so existing callers keep working unchanged:
  from invtool.agent import TOOL_DEFINITIONS, ai_chat_loop, check_api_key,
                             set_data_provider, _handle_tool, _ensure_provider
"""
from .handlers import _ensure_provider, _handle_tool, set_data_provider
from .loop import ai_chat_loop, check_api_key
from .tools import TOOL_DEFINITIONS

__all__ = [
    "TOOL_DEFINITIONS",
    "set_data_provider",
    "check_api_key",
    "ai_chat_loop",
    "_handle_tool",
    "_ensure_provider",
]
