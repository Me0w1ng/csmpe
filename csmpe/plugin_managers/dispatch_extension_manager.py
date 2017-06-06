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

from stevedore.dispatch import DispatchExtensionManager
from stevedore.exception import NoMatches

from csmpe.plugin_managers.base import CSMPluginManager, plugin_namespace

auto_pre_phases = ["Add", "Activate", "Deactivate"]


class CSMPluginDispatchExtensionManager(CSMPluginManager):
    """
    This plugin manager uses stevedore's DispatchExtensionManager internally to dispatch
     all plugins that match the family, os and phase specified in the plugin context.
     The execution of the plugins are in no particular order.
    """

    def __init__(self, plugin_ctx=None, invoke_on_load=True):
        super(CSMPluginDispatchExtensionManager, self).__init__(plugin_ctx)

        self.load(invoke_on_load=invoke_on_load)

    def load(self, invoke_on_load=True):
        self._manager = DispatchExtensionManager(
            plugin_namespace,
            self._check_plugin,
            invoke_on_load=invoke_on_load,
            invoke_args=(self._ctx,),
            propagate_map_exceptions=True,
            on_load_failure_callback=self._on_load_failure,
        )
        self._build_plugin_list()

    def __getitem__(self, item):
        return self._manager.__getitem__(item)

    def _build_plugin_list(self):
        self.plugins = {}
        for ext in self._manager:
            self.plugins[ext.name] = {
                #  'package_name': ext.entry_point.dist.project_name,
                'package_name': ext.entry_point.module_name.split(".")[0],
                'name': ext.plugin.name,
                'description': ext.plugin.__doc__,
                'phases': ext.plugin.phases,
                'platforms': ext.plugin.platforms,
                'os': ext.plugin.os
            }

    def dispatch(self, func):
        results = []
        current_phase = self._ctx.phase
        if self._ctx.phase in auto_pre_phases:
            phase = "Pre-{}".format(self._ctx.phase)
            self.set_phase_filter(phase)
            self._ctx.info("Phase: {}".format(self._phase))
            try:
                results = self._manager.map_method(self._filter_func, func)
            except NoMatches:
                self._ctx.warning("No {} plugins found".format(phase))
            self._ctx.current_plugin = None

        self.set_phase_filter(current_phase)
        self._ctx.info("Phase: {}".format(self._phase))
        try:
            results += self._manager.map_method(self._filter_func, func)
        except NoMatches:
            self._ctx.post_status("No plugins found for phase {}".format(self._phase))
            self._ctx.error("No plugins found for phase {}".format(self._phase))

        self.finalize()
        return results
