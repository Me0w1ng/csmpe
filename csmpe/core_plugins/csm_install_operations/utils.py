import sys
import importlib


class ServerType:
    TFTP_SERVER = 'TFTP'
    FTP_SERVER = 'FTP'
    SFTP_SERVER = 'SFTP'
    LOCAL_SERVER = 'LOCAL'


def import_module(module, path=None):
    if path is not None:
        sys.path.append(path)
    try:
        return importlib.import_module(module)
    except:
        return None


def concatenate_dirs(dir1, dir2):
    """
    Appends dir2 to dir1. It is possible that either/both dir1 or/and dir2 is/are None
    """
    result_dir = dir1 if dir1 is not None and len(dir1) > 0 else ''
    if dir2 is not None and len(dir2) > 0:
        if len(result_dir) == 0:
            result_dir = dir2
        else:
            result_dir += '/' + dir2

    return result_dir


def is_empty(obj):
    """
    These conditions are considered empty
       s = [], s = None, s = '', s = '    ', s = 'None'
    """
    if isinstance(obj, str):
        obj = obj.replace('None', '').strip()

    if obj:
        return False

    return True


def update_device_info_udi(ctx):
    # _update_device_info() and _update_udi() are removed in condoor-ng
    # ctx._connection._update_device_info()
    # ctx._connection._update_udi()
    ctx._csm.save_data("device_info", ctx._connection.device_info)
    ctx._csm.save_data("udi", ctx._connection.udi)


def get_cmd_for_install_activate_deactivate(ctx, func_get_pkg_list,
                                            cmd_with_package_names, cmd_with_operation_id):
    try:
        has_tar = False
        for package in ctx.software_packages:
            if "tar" in package:
                has_tar = True
                break
        if has_tar:
            operation_id = ctx.get_operation_id(ctx.software_packages)
        else:
            operation_id = None
    except AttributeError:
        ctx.error("No package is selected.")
        return

    if operation_id is None or operation_id == -1:
        if has_tar:
            ctx.error("No install add operation of the exact selected packages has been completed successfully.")
            return
        tobe_activated_deactivated = func_get_pkg_list()
        if not tobe_activated_deactivated:
            return None
        return cmd_with_package_names.format(tobe_activated_deactivated)
    else:
        ctx.info("Using the operation ID: {}".format(operation_id))
        return cmd_with_operation_id.format(operation_id)
