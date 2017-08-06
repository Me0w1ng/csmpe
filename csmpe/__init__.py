from csmpe.plugin_managers import get_csm_plugin_manager  # NOQA
from csmpe.__main__ import filter_plugins  # NOQA
from plugins.base import CSMPlugin  # NOQA

__version__ = '1.0.3'


def get_available_plugins(platform=None, phase=None, os=None):
    pm = filter_plugins(platform, phase, os)
    plugins = set()
    for details in pm.plugins.values():
        plugins.add(details['name'])
    return sorted(plugins)
