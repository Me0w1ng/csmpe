from csmpe.context import PluginContext
from csmpe.plugin_managers.dispatch_extension_manager import CSMPluginDispatchExtensionManager   # NOQA
from csmpe.plugin_managers.named_extension_manager import CSMPluginNamedExtensionManager   # NOQA

__version__ = '1.0.1'


def get_csm_plugin_manager(ctx, load_plugins=True, invoke_on_load=True):
    plugin_context = PluginContext(ctx)
    if plugin_context.plugin_execution_order:
        return CSMPluginNamedExtensionManager(plugin_context, load_plugins, invoke_on_load)
    return CSMPluginDispatchExtensionManager(plugin_context, load_plugins, invoke_on_load)
