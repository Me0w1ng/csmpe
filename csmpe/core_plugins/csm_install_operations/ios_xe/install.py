# =============================================================================
#
# Copyright (c) 2016, Cisco Systems
# All rights reserved.
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
import re
import time
from functools import partial
from csmpe.core_plugins.csm_node_status_check.ios_xe.plugin_lib import parse_show_platform
from utils import install_add_remove


def send_newline(fsm_ctx):
    fsm_ctx.ctrl.sendline('\r\n')
    fsm_ctx.ctrl.sendline('\r\n')
    fsm_ctx.ctrl.sendline('\r\n')
    return True


def issu_error_state(plugin_ctx, fsm_ctx):
    plugin_ctx.warning("Error in ISSU. Please see session.log for details")
    return False


def issu_connection_closed(plugin_ctx, fsm_ctx):
    plugin_ctx.warning("Unexpected connection closed by foreign host during ISSU")
    # sleep until both standby and active RSP's are upgraded
    time.sleep(3600)
    return True


def validate_node_state(inventory):
    valid_state = [
        'ok',
        'ok, active',
        'ok, standby',
        'ps, fail',
        'out of service',
        'N/A'
    ]
    for key, value in inventory.items():
        if value['state'] not in valid_state:
            break
    else:
        return True
    return False


def wait_for_reload(ctx):
    """
     Wait for system to come up with max timeout as 25 Minutes

    """
    begin = time.time()
    ctx.disconnect()
    ctx.post_status("Waiting for device boot to reconnect")
    ctx.info("Waiting for device boot to reconnect")
    time.sleep(1500)   # 25 * 60 = 1500
    ctx.reconnect(force_discovery=True)
    ctx.info("Boot process finished")
    ctx.info("Device connected successfully")

    timeout = 3600
    poll_time = 30
    time_waited = 0

    ctx.info("Waiting for all nodes to come up")
    ctx.post_status("Waiting for all nodes to come up")
    time.sleep(30)

    output = None

    ncnt = 0
    while 1:

        ncnt += 1
        if ncnt > 20:
            break

        # Wait till all nodes are in XR run state
        time_waited += poll_time
        if time_waited >= timeout:
            break

        time.sleep(poll_time)

        # show platform can take more than 1 minute after router reload. Issue No. 47
        output = ctx.send('show platform', timeout=600)

        ctx.info("show platform = {}".format(output))

        inventory = parse_show_platform(ctx, output)
        if validate_node_state(inventory):
            ctx.info("All nodes in desired state")
            elapsed = time.time() - begin
            ctx.info("Overall outage time: {} minute(s) {:.0f} second(s)".format(elapsed // 60, elapsed % 60))
            return True

    # Some nodes did not come to run state
    ctx.error("Not all nodes have came up: {}".format(output))
    # this will never be executed
    return False


def install_activate_write_memory(ctx, cmd):
    """

    PAN-5201-ASR903#write memory
    Building configuration...
    [OK]
    PAN-5201-ASR903#

    PAN-5201-ASR903#write memory
    Warning: Attempting to overwrite an NVRAM configuration previously written
    by a different version of the system image.
    Overwrite the previous NVRAM configuration?[confirm]

    """

    # Seeing this message without the reboot prompt indicates a non-reload situation
    build_config = re.compile("\[OK\]")
    overwrite_warning = re.compile("Overwrite the previous NVRAM configuration\?\[confirm\]")

    events = [overwrite_warning, build_config]
    transitions = [
        (overwrite_warning, [0], 1, send_newline, 1200),
        (build_config, [0, 1], -1, None, 1200),
    ]

    if not ctx.run_fsm("write memory", cmd, events, transitions, timeout=1200):
        ctx.error("Failed: {}".format(cmd))


def expand_subpkgs_exec(ctx, folder, pkg):
    """
    Expand the consolidated file into the image folder

    :param: ctx
    :param: folder
    :param: pkg ie bootflash:asr900*.bin
    :return: True or False
    """
    pkg_conf = folder + '/packages.conf'
    pkg_conf2 = pkg_conf + '-'

    output = ctx.send('dir ' + pkg_conf)
    if 'No such file or directory' not in output:
        ctx.send('del /force ' + pkg_conf2)
        cmd = 'copy ' + pkg_conf + ' ' + pkg_conf2
        install_add_remove(ctx, cmd)
        ctx.send('del /force ' + pkg_conf)

    ctx.info("Expanding subpackages into {}".format(folder))

    cmd = 'request platform software package expand file ' + pkg + ' to ' + folder
    output = ctx.send(cmd, timeout=600)
    m = re.search('SUCCESS: Finished expanding all-in-one software package', output)
    if not m:
        ctx.warning("Error: {}".format(cmd))
        return False

    return True


def expand_subpkgs(ctx, rsp_count, folder, pkg):
    """
    Expand the consolidated file into the image folder

    :param: ctx
    :param: rsp_count
    :param: pkg
    :return: True or False
    """

    package = 'bootflash:' + pkg
    result = expand_subpkgs_exec(ctx, folder, package)
    if not result:
        ctx.error('Expanding {} into {} has encountered '
                  'an error'.format(package, folder))
        return False

    if rsp_count == 2:
        cmd = 'copy bootflash:' + pkg + ' ' + 'stby-bootflash:' + pkg
        install_add_remove(ctx, cmd)

        package = 'stby-' + package
        folder = 'stby-' + folder
        result = expand_subpkgs_exec(ctx, folder, package)
        if not result:
            ctx.error('Expanding {} into {} has encountered '
                      'an error'.format(package, folder))
            return False

    return True


def install_activate_reload(ctx):
    """
    Reload the router

    :param ctx
    :return: nothing
    """
    message = "Waiting the {} operation to continue".format('reload')
    ctx.info(message)
    ctx.post_status(message)

    if not ctx.reload(reload_timeout=1200, no_reload_cmd=True):
        ctx.error("Encountered error when attempting to reload device.")

    success = wait_for_reload(ctx)

    if not success:
        ctx.error("Reload or boot failure")
        return

    ctx.info("Operation reload finished successfully")
    return


def install_activate_issu(ctx, cmd):
    """
    Start the issu

    :param ctx
    :param cmd
    :param hostname
    :return: nothing
    """

    # Seeing a message without STAGE 4 is an error
    phase_one = re.compile("Starting disk space verification")
    stage_one = re.compile("STAGE 1: Installing software on standby RP")
    stage_two = re.compile("STAGE 2: Restarting standby RP")
    stage_three = re.compile("STAGE 3: Installing sipspa package on local RP")
    stage_four = re.compile("STAGE 4: Installing software on active RP")
    load_on_reboot = re.compile("SUCCESS: Software provisioned.  New software will load on reboot")
    missing_conf = re.compile("SYSTEM IS NOT BOOTED VIA PACKAGE FILE")
    failed = re.compile("FAILED:")
    connection_closed = re.compile("Connection closed by foreign host")
    #            0          1          2          3             4            5
    events = [phase_one, stage_one, stage_two, stage_three, stage_four, load_on_reboot,
              missing_conf, failed, connection_closed]
    #            6            7            8
    transitions = [
        (phase_one, [0], 1, None, 1800),
        (stage_one, [0, 1], 2, None, 1800),
        (stage_two, [2], 3, None, 1800),
        (stage_three, [3], 4, None, 1800),
        (stage_four, [4], 5, None, 1800),
        (load_on_reboot, [5], -1, None, 1800),
        (missing_conf, [0, 1, 2, 3, 4, 5], -1, partial(issu_error_state, ctx), 60),
        (failed, [0, 1, 2, 3, 4, 5], -1, partial(issu_error_state, ctx), 60),
        (connection_closed, [1, 2, 3, 4], -1, partial(issu_connection_closed, ctx), 4200)
    ]

    if not ctx.run_fsm("ISSU", cmd, events, transitions, timeout=4200):
        ctx.error("Failed: {}".format(cmd))

    time.sleep(300)

    success = wait_for_reload(ctx)

    if not success:
        ctx.error("Reload or boot failure")
        return

    ctx.info("Operation reload finished successfully")
    return
