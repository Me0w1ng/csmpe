from csmpe.plugin_managers import get_csm_plugin_manager  # NOQA
from csmpe.__main__ import filter_plugins  # NOQA
from plugins.base import CSMPlugin  # NOQA

__version__ = '1.0.2'


def get_available_plugins(platform=None, phase=None, os=None):
    pm = filter_plugins(platform, phase, os)
    plugin_to_data = dict()
    for details in pm.plugins.values():
        plugin_to_data[details['name']] = details['csm_data']
    return plugin_to_data
