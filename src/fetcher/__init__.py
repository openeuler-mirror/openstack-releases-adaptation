"""fetcher - OpenStack 上游数据采集模块"""

from .openstack import run as fetch_releases
from .constraints import run as fetch_constraints

__all__ = ["fetch_releases", "fetch_constraints"]
