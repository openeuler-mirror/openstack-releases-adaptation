"""
store.py - 状态管理

保存"做到哪一步了"，保证幂等性，防止重复构建/PR。
支持 YAML/JSON 存储，可 Git 追踪。
"""

import json
from pathlib import Path
from typing import Any

from config import get_state_path


class StateStore:
    """轻量状态存储，支持包级别的阶段追踪。"""

    def __init__(self, release: str, state_file: str = "state.json"):
        self.path = get_state_path(state_file)
        self.release = release
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {"release": self.release, "packages": {}}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_pkg(self, pkg: str) -> dict[str, str]:
        return self.data["packages"].get(pkg, {})

    def update_pkg(self, pkg: str, stage: str, status: str) -> None:
        if pkg not in self.data["packages"]:
            self.data["packages"][pkg] = {}
        self.data["packages"][pkg][stage] = status
        self.save()

    def get_packages_by_stage(self, stage: str, status: str) -> list[str]:
        return [pkg for pkg, stages in self.data["packages"].items()
                if stages.get(stage) == status]

    def get_all_pending(self, stage: str) -> list[str]:
        return [pkg for pkg, stages in self.data["packages"].items()
                if stages.get(stage) is None]


def get_state(state_file: str = "state.json") -> StateStore:
    """获取状态存储实例。"""
    return StateStore(release="current", state_file=state_file)


def update_state(pkg: str, stage: str, status: str, state_file: str = "state.json") -> None:
    """快捷更新状态。"""
    store = StateStore(release="current", state_file=state_file)
    store.update_pkg(pkg, stage, status)
