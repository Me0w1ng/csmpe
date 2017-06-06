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

install_phases = ['Pre-Upgrade', 'Pre-Add', 'Add', 'Pre-Activate', 'Activate', 'Pre-Deactivate',
                  'Deactivate', 'Pre-Remove', 'Remove', 'Remove All Inactive', 'Commit', 'Get-Inventory',
                  'Migration-Audit', 'Pre-Migrate', 'Migrate', 'Post-Migrate', 'Post-Upgrade', 'FPD-Upgrade']


@six.add_metaclass(abc.ABCMeta)
class CSMPluginManager(object):

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
            self._platform = self._ctx.family
        except AttributeError:
            self._platform = None
        try:
            self._os = self._ctx.os_type
        except AttributeError:
            self._os = None

        self._phase = None
        self._name = None
        # plugin_execution_order is a list of plugin names
        # For MOP jobs, plugin_execution_order is specified in the context to indicate which plugins
        # should execute and the order of execution.
        # For regular jobs, plugin_execution_order is not specified.
        self.plugin_execution_order = self._ctx.plugin_execution_order

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
        if self._platform and bool(ext.plugin.platforms) and self._platform not in ext.plugin.platforms:
            return False
        if self._phase and self._phase not in ext.plugin.phases:
            return False
        if self._name and ext.plugin.name not in self._name:
            return False
        # if detected os is set and plugin os set is not empty and detected os is not in plugin os then
        # plugin does not match
        if self._os and bool(ext.plugin.os) and self._os not in ext.plugin.os:
            return False
        if self.plugin_execution_order and ext.plugin.name not in self.plugin_execution_order:
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
        self._platform = platform

    def set_phase_filter(self, phase):
        self._phase = phase

    def set_os_filter(self, os):
        self._os = os

    def set_name_filter(self, name):
        if isinstance(name, str) or isinstance(name, unicode):
            self._name = {name}
        elif isinstance(name, list):
            self._name = set(name)
        elif isinstance(name, set):
            self._name = name
        else:
            self._name = None
