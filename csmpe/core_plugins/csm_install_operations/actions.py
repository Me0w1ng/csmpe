"""This is a module providing FSM actions for Install Operations plugins."""
import re


def a_error(plugin_ctx, ctx):
    """Display the error message."""
    message = ctx.ctrl.after.strip().splitlines()[-1]
    plugin_ctx.error(message)
    return False


def a_remote_host_address(plugin_ctx, fsm_ctx):
    """send remote host address or name."""
    address = plugin_ctx.src_address
    fsm_ctx.ctrl.sendline(address)
    return True


def a_source_username(plugin_ctx, fsm_ctx):
    """send source username."""
    src_username = plugin_ctx.src_username
    fsm_ctx.ctrl.sendline(src_username)
    return True


def a_source_password(plugin_ctx, fsm_ctx):
    """send source password."""
    src_password = plugin_ctx.src_password
    fsm_ctx.ctrl.send_command(src_password, password=True)
    return True


def a_source_filename(plugin_ctx, fsm_ctx):
    """send source filename."""
    src_file = plugin_ctx.src_file
    fsm_ctx.ctrl.sendline(src_file)
    return True


def a_destination(plugin_ctx, fsm_ctx):
    """send destination filename."""
    destination_file = plugin_ctx.destination_file
    fsm_ctx.ctrl.sendline(destination_file)
    return True


def a_send_newline(fsm_ctx):
    """Display the error message."""
    fsm_ctx.sendline('\r\n')
    return True


def a_bytes_copied(plugin_ctx, fsm_ctx):
    """Capture number of bytes copied."""
    m = re.search("\d+ bytes copied in .* secs", fsm_ctx.ctrl.before)
    if m:
        plugin_ctx.info('{}'.format(m.group(0)))
    else:
        plugin_ctx.info('{}'.format(fsm_ctx.ctrl.before))

    return True
