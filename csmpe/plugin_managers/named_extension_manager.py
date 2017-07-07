# =============================================================================
# CSMPluginManager
#
# Copyright (c)  2016, Cisco Systems
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

from stevedore.named import NamedExtensionManager
from stevedore.exception import NoMatches

from csmpe.plugin_managers.base import CSMPluginManager, plugin_namespace
from csmpe.plugin_managers.dispatch_extension_manager import DispatchExtensionManager


class CSMPluginNamedExtensionManager(CSMPluginManager):
    """
    This plugin manager executes plugins in the order specified in the plugin context.
    It first uses stevedore's DispatchExtensionManager internally to filter plugins that match
    the family, os, phase and plugin names specified in the plugin context.
    Then it provides the extension names of the filtered plugins to stevedore's NamedExtensionManager,
    in order to execute the filtered plugins in specified order.
    """

    def __init__(self, plugin_ctx=None, load_plugins=True, invoke_on_load=True):
        super(CSMPluginNamedExtensionManager, self).__init__(plugin_ctx)

        self.set_phase_filter(self._ctx.phase)

        # plugin_execution_order is a list of plugin names
        # For MOP jobs, plugin_execution_order is specified in the context to indicate which plugins
        # should execute and the order of execution.
        # For regular jobs, plugin_execution_order is not specified.
        self.plugin_execution_order = self._ctx.plugin_execution_order

        self.set_name_filter(self.plugin_execution_order)

        if load_plugins:
            self.load(invoke_on_load=invoke_on_load)

    def load(self, invoke_on_load=True):

        ext_manager = DispatchExtensionManager(
            plugin_namespace,
            self._check_plugin,
            invoke_on_load=False,
            invoke_args=(self._ctx,),
            propagate_map_exceptions=True,
            on_load_failure_callback=self._on_load_failure
        )
        plugin_name_to_extension_name = self._build_plugin_list(ext_manager)

        plugins_missing = []
        ordered_extension_names = []
        for plugin_name in self.plugin_execution_order:
            if plugin_name not in plugin_name_to_extension_name:
                plugins_missing.append(plugin_name)
            elif not plugins_missing:
                ordered_extension_names.append(plugin_name_to_extension_name[plugin_name])
        if plugins_missing:
            self._ctx.error("Missing the following selected plugin(s): {}".format(", ".join(plugins_missing)))
            return

        self._manager = NamedExtensionManager(
            plugin_namespace,
            ordered_extension_names,
            invoke_on_load=invoke_on_load,
            invoke_args=(self._ctx,),
            name_order=True,
            propagate_map_exceptions=True,
            on_load_failure_callback=self._on_load_failure,
            on_missing_entrypoints_callback=self._on_missing_entrypoints
        )

    def __getitem__(self, item):
        return self._manager.__getitem__(item)

    def _build_plugin_list(self, ext_manager):
        plugin_name_to_extension_name = dict()
        for ext in ext_manager:
            self.plugins[ext.name] = {
                #  'package_name': ext.entry_point.dist.project_name,
                'package_name': ext.entry_point.module_name.split(".")[0],
                'name': ext.plugin.name,
                'description': ext.plugin.__doc__,
                'phases': ext.plugin.phases,
                'platforms': ext.plugin.platforms,
                'os': ext.plugin.os
            }
            if ext.plugin.name in plugin_name_to_extension_name:
                self._ctx.warning("Found more than one plugin with name {} at {}.".format(ext.plugin.name,
                                                                                          ext.entry_point.module_name) +
                                  "This duplicate plugin will not be dispatched. " +
                                  "Please ensure unique plugin name to avoid confusion.")
            else:
                plugin_name_to_extension_name[ext.plugin.name] = ext.name
        return plugin_name_to_extension_name

    def dispatch(self, func):
        results = []
        self._ctx.info("Phase: {}".format(self._phase_list[0] if len(self._phase_list) == 1 else self._phase_list))
        try:
            results += self._manager.map_method(func)
        except NoMatches:
            self._ctx.post_status("No plugins found for phase {}".format(self._phase_list))
            self._ctx.error("No plugins found for phase {}".format(self._phase_list))

        self.finalize()
        return results

    def _on_missing_entrypoints(self, extensions_missing):
        self._ctx.warning("Plugin load error: missing the following extension(s): {}".format(", ".join(extensions_missing)))
