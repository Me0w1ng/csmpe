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

import pkginfo
from stevedore.named import NamedExtensionManager
from stevedore.exception import NoMatches

from csmpe.managers.base import CSMPluginManager, plugin_namespace
from csmpe.managers.dispatch_extension_manager import DispatchExtensionManager


class CSMPluginNamedExtensionManager(CSMPluginManager):

    def __init__(self, plugin_ctx=None, invoke_on_load=True):
        super(CSMPluginNamedExtensionManager, self).__init__(plugin_ctx, invoke_on_load)
        self._phase = self._ctx.phase

        self.load(invoke_on_load=invoke_on_load)

    def load(self, invoke_on_load=True):

        ext_manager = DispatchExtensionManager(
            plugin_namespace,
            self._check_plugin,
            invoke_on_load=False,
            invoke_args=(self._ctx,),
            propagate_map_exceptions=True,
            on_load_failure_callback=self._on_load_failure,
        )
        module_name_to_extension_name = self._build_plugin_list(ext_manager)

        modules_missing = set()
        ordered_extension_names = []
        for module_name in self.plugin_execution_order:
            if module_name not in module_name_to_extension_name:
                modules_missing.add(module_name)
            elif not modules_missing:
                ordered_extension_names.append(module_name_to_extension_name[module_name])
        if modules_missing:
            self._ctx.error("Abort. The following selected plugins are missing: {}".format(modules_missing))
            return

        self._manager = NamedExtensionManager(
            plugin_namespace,
            ordered_extension_names,
            invoke_on_load=invoke_on_load,
            invoke_args=(self._ctx,),
            name_order=True,
            propagate_map_exceptions=True,
            on_load_failure_callback=self._on_load_failure
        )

    def __getitem__(self, item):
        return self._manager.__getitem__(item)

    def _build_plugin_list(self, ext_manager):
        self.plugins = {}
        module_name_to_extension_name = dict()
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
            module_name_to_extension_name[ext.entry_point.module_name] = ext.name
        return module_name_to_extension_name

    def dispatch(self, func):

        results = []
        self._ctx.info("Phase: {}".format(self._phase))
        try:
            results += self._manager.map_method(func)
        except NoMatches as e:
            self._ctx.warning(e)
            self._ctx.post_status("No plugins found for phase {}".format(self._phase))
            self._ctx.error("No plugins found for phase {}".format(self._phase))
        except Exception as e2:
            self._ctx.error(e2)

        self.finalize()
        return results
