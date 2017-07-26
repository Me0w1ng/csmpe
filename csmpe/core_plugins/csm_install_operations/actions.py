"""This is a module providing FSM actions for Install Operations plugins."""
import re


def a_error(plugin_ctx, fsm_ctx):
    """Display the error message."""
    message = fsm_ctx.ctrl.after.strip().splitlines()[-1]
    plugin_ctx.error(message)
    return False


def send_yes(plugin_ctx, fsm_ctx):
    fsm_ctx.ctrl.send('Y')
    return True


def a_get_opid(plugin_ctx, fsm_ctx):
    m = re.search('Install operation (\d+)', fsm_ctx.ctrl.before)
    if m:
        op_id = m.group(1)
        plugin_ctx.op_id = op_id
        plugin_ctx.info('Install Operation ID = {}'.format(op_id))
        return True
    else:
        plugin_ctx.warning('fsm_ctx.ctrl.before = {}'.format(fsm_ctx.ctrl.before))
        return False


def a_no_package(plugin_ctx, fsm_ctx):
        plugin_ctx.warning('Cannot proceed with the remove operation because there are no packages that can be removed. '
                           'Packages can only be removed if they are not part of the active software and '
                           'not part of the committed software.')
        return False


def a_install_in_progress(plugin_ctx, fsm_ctx):
        plugin_ctx.warning('Another install command is currently in operation.')
        return False
