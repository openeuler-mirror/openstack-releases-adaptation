"""
compare.py - 版本差异分析与决策引擎

比较 OpenStack 上游版本与 openEuler 现有版本，输出升级决策清单。
"""

import json
from pathlib import Path
from typing import Any

from packaging import version

from config import load_config, get_data_path, get_output_path, get_state_path


def load_upstream(output_filename: str) -> dict[str, dict[str, str]]:
    """加载上游版本数据 (openstack_release.yaml)。"""
    import yaml
    path = get_output_path(output_filename)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_inventory() -> dict[str, dict[str, Any]]:
    """加载 openEuler 版本数据 (Version.json)。"""
    path = get_data_path("Version.json")
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_versions(config: dict[str, Any] | None = None) -> list[dict]:
    """
    对比上游与 openEuler 版本，生成升级决策清单。

    Returns:
        决策列表 [{"pkg": ..., "upstream": ..., "oe_version": ..., "branch": ..., "action": ...}]
    """
    if config is None:
        config = load_config()

    current = config["openstack"]["current"]
    release_key = current.split()[-1] if " " in current else current
    upstream = load_upstream(config["openstack"]["output"])
    inventory = load_inventory()

    release_upstream = upstream.get(release_key, {})
    decisions = []

    for repo_name, repo_info in inventory.items():
        versions = repo_info.get("Version", {})
        for branch, oe_ver in versions.items():
            if oe_ver == "No Spec":
                continue
            pkg_name = repo_name.replace("-", "_").lower()

            if pkg_name in release_upstream:
                upstream_ver = release_upstream[pkg_name]
                try:
                    if version.parse(upstream_ver) > version.parse(oe_ver):
                        decisions.append({
                            "pkg": repo_name,
                            "branch": branch,
                            "upstream": upstream_ver,
                            "oe_version": oe_ver,
                            "action": "upgrade",
                            "needs_human": False
                        })
                    elif version.parse(upstream_ver) == version.parse(oe_ver):
                        continue
                except version.InvalidVersion:
                    decisions.append({
                        "pkg": repo_name,
                        "branch": branch,
                        "upstream": upstream_ver,
                        "oe_version": oe_ver,
                        "action": "needs_human",
                        "needs_human": True
                    })

    return sorted(decisions, key=lambda x: x["pkg"])


def run(config: dict[str, Any] | None = None) -> int:
    """执行版本对比并保存决策清单。"""
    decisions = compare_versions(config)
    output_path = get_state_path("upgrade_plan.json")
    output_path.write_text(json.dumps(decisions, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Upgrade plan: {len(decisions)} packages need update")
    for d in decisions:
        flag = " [NEEDS HUMAN]" if d["needs_human"] else ""
        print(f"  {d['pkg']} ({d['branch']}): {d['oe_version']} → {d['upstream']}{flag}")
    print(f"\nSaved to: {output_path}")
    return 0
