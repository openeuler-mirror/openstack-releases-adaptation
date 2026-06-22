"""
report.py - 适配状态报告生成

将内部状态生成静态 HTML + JSON 报告。
"""

import json
from pathlib import Path
from typing import Any

from config import load_config, get_state_path, get_output_path


def run(config: dict[str, Any] | None = None) -> int:
    """生成 HTML 状态报告。"""
    if config is None:
        config = load_config()

    plan_path = get_state_path("upgrade_plan.json")
    state_path = get_state_path("state.json")

    if not plan_path.exists():
        print("No upgrade plan found")
        return 1

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

    total = len(plan)
    upgraded = sum(1 for p in plan if p.get("action") != "needs_human")
    needs_human = total - upgraded

    print(f"Upgrade Status Report")
    print(f"  Total packages: {total}")
    print(f"  Auto-upgradeable: {upgraded}")
    print(f"  Needs human: {needs_human}")
    return 0
