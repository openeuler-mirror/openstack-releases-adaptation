"""state - 跨环境状态同步模块"""

from .store import get_state, update_state, StateStore

__all__ = ["StateStore", "get_state", "update_state"]
