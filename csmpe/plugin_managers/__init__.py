from csmpe.context import PluginContext
from csmpe.plugin_managers.dispatch_extension_manager import CSMPluginDispatchExtensionManager   # NOQA
from csmpe.plugin_managers.named_extension_manager import CSMPluginNamedExtensionManager   # NOQA
__version__ = '1.0.1'


def get_csm_plugin_manager(ctx, load_plugins=True, invoke_on_load=True):
    plugin_context = PluginContext(ctx)
    try:
        if plugin_context.mop_specs:
            return CSMPluginNamedExtensionManager(plugin_context, load_plugins, invoke_on_load)
    except AttributeError:
        pass
    return CSMPluginDispatchExtensionManager(plugin_context, load_plugins, invoke_on_load)

