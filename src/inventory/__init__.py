"""inventory - openEuler 现状采集模块"""

from .repo import run as scan_repos
from .spec import run as scan_versions

__all__ = ["scan_repos", "scan_versions"]
