"""fetcher - OpenStack 上游数据采集模块"""

from .openstack import run as fetch_releases
from .requirements import run as fetch_requirements

__all__ = ["fetch_releases", "fetch_requirements"]
