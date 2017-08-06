# =============================================================================
#
# Copyright (c) 2016, Cisco Systems
# All rights reserved.
#
# # Author: Klaudiusz Staniek
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.
# =============================================================================

import abc
import six
import pkginfo

plugin_namespace = "csm.plugin"

install_phases = ['Pre-Check', 'Pre-Add', 'Add', 'Pre-Activate', 'Activate', 'Pre-Deactivate',
                  'Deactivate', 'Pre-Remove', 'Remove', 'Remove All Inactive', 'Commit', 'Get-Inventory',
                  'Migration-Audit', 'Pre-Migrate', 'Migrate', 'Post-Migrate', 'Post-Check', 'FPD-Upgrade']


@six.add_metaclass(abc.ABCMeta)
class CSMPluginManager(object):
    """
    Abstract plugin manager defined to load and dispatch plugins.
    """

    def __init__(self, plugin_ctx=None):
        """ This is the constructor of an abstract plugin manager. The constructor can be overridden by the subclass
        manager implementations.

        :param ctx: The plugin context object :class:`csmpe.PluginContext`
        :return: None
        """
        self._ctx = plugin_ctx
        # The context contains device information after discovery phase
        # There is no need to load plugins which does not match the family and os
        try:
            self._platform_list = [self._ctx.family]
        except AttributeError:
            self._platform_list = None
        try:
            self._os_list = [self._ctx.os_type]
        except AttributeError:
            self._os_list = None

        self._phase_list = None
        self._name_set = None

        # plugins contains info of loaded plugins. This should be built after loading the plugins.
        self.plugins = {}

    @abc.abstractmethod
    def load(self, invoke_on_load=True):
        """
        Create the manager instance and load plugins
        :param invoke_on_load: Boolean indicating whether or not to invoke plugins once loaded.
        :return: None
        """

    @abc.abstractmethod
    def dispatch(self, func):
        """
        This method is a entry point for Plugin Engine to be called.
        Must be implemented by the subclass manager implementation.
        It dispatches the loaded plugins.

        :param: func: string - function name in plugin class that starts the plugin execution
        :return: None
        """

    def finalize(self):
        self._ctx.current_plugin = None
        self._ctx.success = True
        self._ctx.info("CSM Plugin Manager Finished")
        self._ctx.finalize()

    def _filter_func(self, ext, *args, **kwargs):
        """Filters extension"""
        if self._platform_list and bool(ext.plugin.platforms) and not self.is_every_list_item_in_set(self._platform_list, ext.plugin.platforms):
            return False
        if self._phase_list and not self.is_every_list_item_in_set(self._phase_list, ext.plugin.phases):
            return False
        if self._name_set and ext.plugin.name not in self._name_set:
            return False
        # if detected os is set and plugin os set is not empty and detected os is not in plugin os then
        # plugin does not match
        if self._os_list and bool(ext.plugin.os) and not self.is_every_list_item_in_set(self._os_list, ext.plugin.os):
            return False
        return True

    def is_every_list_item_in_set(self, item_list, set):
        for item in item_list:
            if item not in set:
                return False
        return True

    def _on_load_failure(self, manager, entry_point, exc):
        self._ctx.warning("Plugin load error: {}".format(entry_point))
        self._ctx.warning("Exception: {}".format(exc))

    def _check_plugin(self, ext, *args, **kwargs):
        attributes = ['name', 'phases', 'platforms', 'os']
        plugin = ext.plugin
        for attribute in attributes:
            if not hasattr(plugin, attribute):
                self._ctx.warning("Attribute '{}' missing in plugin class: {}".format(
                    attribute, ext.entry_point.module_name))
                return False
        return self._filter_func(ext)

    def get_package_metadata(self, name):
        try:
            meta = pkginfo.Installed(name)
        except ValueError as e:
            print(e)
            return None
        return meta

    def _get_package_names(self):
        return self.get_package_metadata().keys()

    def set_platform_filter(self, platform):
        self._platform_list = self.make_list(platform)

    def set_phase_filter(self, phase):
        self._phase_list = self.make_list(phase)

    def set_os_filter(self, os):
        self._os_list = self.make_list(os)

    def set_name_filter(self, name):
        if isinstance(name, str) or isinstance(name, unicode):
            self._name_set = {name}
        elif isinstance(name, list):
            self._name_set = set([plugin_specs["plugin"] for plugin_specs in name])
        elif isinstance(name, set):
            self._name_set = name
        else:
            self._name_set = None

    def make_list(self, arg):
        if isinstance(arg, str) or isinstance(arg, unicode):
            return [arg]
        elif isinstance(arg, list):
            return arg
        elif isinstance(arg, set):
            return list(arg)
        return None
