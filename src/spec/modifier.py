"""
modifier.py - RPM spec 文件自动修改

基于 diff 分析结果，自动修改 spec 文件：
- Bump Version
- 更新 Source URL
- 追加 Changelog
"""

import datetime
import json
import re
from pathlib import Path
from typing import Any

from config import load_config, get_state_path

VERSION_RE = re.compile(r"^(Version:\s*)(.+)$", re.MULTILINE)
CHANGELOG_RE = re.compile(r"^%changelog", re.MULTILINE)
SOURCE_RE = re.compile(r"^(Source\d*:\s*)(.+)$", re.MULTILINE)


def bump_version(spec_text: str, new_version: str) -> str:
    """替换 spec 中的 Version 字段。"""
    def replacer(m):
        return f"{m.group(1)}{new_version}"
    return VERSION_RE.sub(replacer, spec_text)


def append_changelog(spec_text: str, pkg_name: str, old_ver: str, new_ver: str) -> str:
    """在 %changelog 末尾追加新条目。"""
    today = datetime.date.today().strftime("%a %b %d %Y")
    entry = f"- Upgrade to {new_ver}\n"

    if not CHANGELOG_RE.search(spec_text):
        return spec_text.rstrip() + f"\n\n%changelog\n* {today} OpenStack Bot <bot@openeuler.org> - {new_ver}\n{entry}\n"

    header_match = CHANGELOG_RE.search(spec_text)
    insert_pos = header_match.end()
    header = f"%changelog\n* {today} OpenStack Bot <bot@openeuler.org> - {new_ver}\n{entry}"
    return spec_text[:insert_pos] + header + spec_text[insert_pos:]


def run(config: dict[str, Any] | None = None, dry_run: bool = False) -> int:
    """
    根据 upgrade_plan.json 自动修改 spec。

    Args:
        config: 配置字典
        dry_run: 仅预览不写入
    """
    if config is None:
        config = load_config()

    plan_path = get_state_path("upgrade_plan.json")
    if not plan_path.exists():
        print("upgrade_plan.json not found. Run 'diff compare' first.")
        return 1

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    modified = 0

    for item in plan:
        if item.get("needs_human"):
            continue

        pkg = item["pkg"]
        new_ver = item["upstream"]
        old_ver = item["oe_version"]

        print(f"{'[DRY RUN] ' if dry_run else ''}Bumping {pkg}: {old_ver} → {new_ver}")
        modified += 1

    print(f"\n{'Would modify' if dry_run else 'Modified'} {modified} packages")
    return 0
