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
import re
import time
import itertools
from condoor import ConnectionError, CommandError
from csmpe.core_plugins.csm_node_status_check.ios_xr.plugin_lib import parse_show_platform

install_error_pattern = re.compile("Error:    (.*)$", re.MULTILINE)

plugin_ctx = None


def send_yes(fsm_ctx):
    plugin_ctx.send('Y')
    return True


def log_install_errors(ctx, output):
    errors = re.findall(install_error_pattern, output)
    for line in errors:
        ctx.warning(line)


def watch_operation(ctx, op_id=0):
    """
    Function to keep watch on progress of operation
    and report KB downloaded.

    """
    no_install = r"There are no install requests in operation"
    op_progress = r"The operation is (\d+)% complete"
    op_download = r"(.*)KB downloaded: Download in progress"
    success = "Install operation {} completed successfully".format(op_id)

    cmd_show_install_request = "admin show install request"

    ctx.info("Watching the operation {} to complete".format(op_id))

    propeller = itertools.cycle(["|", "/", "-", "\\", "|", "/", "-", "\\"])

    output = None
    last_status = None
    finish = False
    time_tried = 0
    op_id = str(op_id)
    while not finish:
        try:
            try:
                # this is to catch the successful operation as soon as possible
                ctx.send("", wait_for_string=success, timeout=20)
                finish = True
            except ctx.CommandTimeoutError:
                pass

            message = ""
            # on CRS, it is observed that during Add, any command typed hangs for a while
            output = ctx.send(cmd_show_install_request, timeout=300)
            if op_id in output:
                # FIXME reconsider the logic here
                result = re.search(op_progress, output)
                if result:
                    status = result.group(0)
                    message = "{} {}".format(propeller.next(), status)

                result = re.search(op_download, output)
                if result:
                    status = result.group(0)
                    message += "\r\n<br>{}".format(status)

                if message != last_status:
                    ctx.post_status(message)
                    last_status = message
        except (ConnectionError, ctx.CommandTimeoutError) as e:
            if time_tried > 2:
                raise e

            time_tried += 1
            ctx.disconnect()
            time.sleep(60)
            ctx.reconnect()

        # ctx.send returns with an empty output from 'show install request'. go back to loop
        if output is None:
            continue

        # ctx.send returns and no active install action in progress. terminate the loop
        if no_install in output:
            break

    return output


def validate_node_state(inventory):
    valid_state = [
        'IOS XR RUN',
        'PRESENT',
        'READY',
        'FAILED',
        'OK',
        'DISABLED',
        'UNPOWERED',
        'ADMIN DOWN',
        'PWD',
        'NOT ALLOW ONLIN',  # This is not spelling error
    ]

    for key, value in inventory.items():
        if 'CPU' in key:
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
    if not ctx.is_console:
        # wait a little bit before disconnect so that newline character can reach the router
        # XR ddts CSCvb67386 workaround - reload is aborted after a confirmation is received from
        # the router if disconnect too soon (less than 6 seconds)
        time.sleep(10)
        ctx.disconnect()
        ctx.post_status("Waiting for device boot to reconnect")
        ctx.info("Waiting for device boot to reconnect")
        time.sleep(60)
        ctx.reconnect(max_timeout=3600, force_discovery=True)  # 60 * 60 = 3600
    else:
        ctx.info("Keeping console connected")
        ctx.post_status("Boot process started")
        ctx.info("Boot process started")
        if not ctx.reload(reload_timeout=1500, no_reload_cmd=True):
            ctx.error("Encountered error when attempting to reload device.")
        ctx.info("Boot process finished")

    ctx.info("Device connected successfully")

    timeout = 3600
    poll_time = 30
    time_waited = 0
    xr_run = "IOS XR RUN"

    cmd = "admin show platform"
    ctx.info("Waiting for all nodes to come up")
    ctx.post_status("Waiting for all nodes to come up")
    time.sleep(100)

    output = None

    while 1:
        # Wait till all nodes are in XR run state
        time_waited += poll_time
        if time_waited >= timeout:
            break

        time.sleep(poll_time)

        # show platform can take more than 1 minute after router reload. Issue No. 47
        output = ctx.send(cmd, timeout=600)
        if xr_run in output:
            inventory = parse_show_platform(ctx, output)
            if validate_node_state(inventory):
                ctx.info("All nodes in operational state")
                elapsed = time.time() - begin
                ctx.info("Overall outage time: {} minute(s) {:.0f} second(s)".format(elapsed // 60, elapsed % 60))
                return True

    # Some nodes did not come to run state
    ctx.error("Not all nodes have came up: {}".format(output))
    # this will never be executed
    return False


def watch_install(ctx, cmd, op_id=0):
    success_oper = r'Install operation (\d+) completed successfully'
    completed_with_failure = 'Install operation (\d+) completed with failure'
    failed_oper = r'Install operation (\d+) failed'
    failed_incr = r'incremental.*parallel'
    # restart = r'Parallel Process Restart'
    install_method = r'Install [M|m]ethod: (.*)'
    op_success = "The install operation will continue asynchronously"

    watch_operation(ctx, op_id)

    output = ctx.send("admin show install log {} detail".format(op_id))
    if re.search(failed_oper, output):
        if re.search(failed_incr, output):
            ctx.info("Retrying with parallel reload option")
            cmd += " parallel-reload"
            output = ctx.send(cmd)
            if op_success in output:
                result = re.search('Install operation (\d+) \'', output)
                if result:
                    op_id = result.group(1)
                    watch_operation(ctx, op_id)
                    output = ctx.send("admin show install log {} detail".format(op_id))
                else:
                    log_install_errors(ctx, output)
                    ctx.error("Operation ID not found")
                    return
        else:
            log_install_errors(ctx, output)
            ctx.error(output)
            return

    """
    Command example:

    admin show install log 151 detail

Install operation 151 started by user 'root' via CLI at 04:42:17 PST Sun Sep 20 1987.
(admin) install activate disk0:asr9k-mini-px-6.1.3 disk0:asr9k-services-px-6.1.3 disk0:asr9k-doc-px-6.1.3 disk0:asr9k-video-px-6.1.3 disk0:asr9k-fpd-px-6.1.3 disk0:asr9k-mpls-px-6.1.3 disk0:asr9k-mcast-px-6.1.3 disk0:asr9k-px-5.3.3.CSCux41951-1.0.0 disk0:asr9k-mgbl-px-6.1.3 disk0:asr9k-optic-px-6.1.3 disk0:asr9k-k9sec-px-6.1.3 disk0:asr9k-9000v-nV-px-6.1.3 disk0:asr9k-bng-px-6.1.3 disk0:asr9k-li-px-6.1.3 disk0:asr9k-services-infra-6.1.3 disk0:asr9k-px-5.3.3.CSCux68183-1.0.0 prompt-level none
Install operation 151 completed successfully at 04:46:35 PST Sun Sep 20 1987.

Install logs:
    Install operation 151 '(admin) install activate disk0:asr9k-mini-px-6.1.3 disk0:asr9k-services-px-6.1.3 disk0:asr9k-doc-px-6.1.3 disk0:asr9k-video-px-6.1.3 disk0:asr9k-fpd-px-6.1.3 disk0:asr9k-mpls-px-6.1.3 disk0:asr9k-mcast-px-6.1.3 disk0:asr9k-px-5.3.3.CSCux41951-1.0.0 disk0:asr9k-mgbl-px-6.1.3 disk0:asr9k-optic-px-6.1.3 disk0:asr9k-k9sec-px-6.1.3 disk0:asr9k-9000v-nV-px-6.1.3 disk0:asr9k-bng-px-6.1.3 disk0:asr9k-li-px-6.1.3 disk0:asr9k-services-infra-6.1.3 disk0:asr9k-px-5.3.3.CSCux68183-1.0.0
    prompt-level none' started by user 'root' via CLI at 04:42:17 PST Sun Sep 20 1987.
    Info:     After this install operation, some SMU package(s) are fully/partially superceded. The fully superseded SMUs can found using CLI: 'show install superceded'. If found those can be deactivated using CLI: 'install deactivate superceded'.
    Warning:  There is no valid license for the following package:
    Warning:
    Warning:      disk0:asr9k-li-6.1.3
    Warning:
    Info:     The following sequence of sub-operations has been determined to minimize any impact:
    Info:
    Info:     Sub-operation 1:
    Info:         Install Method: Parallel Process Restart
    Info:         asr9k-px-5.3.3.CSCux41951-1.0.0
    Info:
    Info:     Sub-operation 2:
    Info:         Install Method: Parallel Process Restart
    Info:         asr9k-px-5.3.3.CSCux68183-1.0.0
    Info:
    Info:     Sub-operation 3:
    Info:         Install Method: Parallel Roeload
    Info:         asr9k-services-infra-6.1.3
    Info:         asr9k-li-px-6.1.3
    Info:         asr9k-bng-px-6.1.3
    Info:         asr9k-9000v-nV-px-6.1.3
    Info:         asr9k-k9sec-px-6.1.3
    Info:         asr9k-optic-px-6.1.3
    Info:         asr9k-mgbl-px-6.1.3
    Info:         asr9k-mcast-px-6.1.3
    Info:         asr9k-mpls-px-6.1.3
    Info:         asr9k-fpd-px-6.1.3
    Info:         asr9k-video-px-6.1.3
    Info:         asr9k-doc-px-6.1.3
    Info:         asr9k-services-px-6.1.3
    Info:         asr9k-mini-px-6.1.3
    Info:
    'prompt-level none' specified. Proceeding with operation.
    Info:     This operation will reload the following nodes in parallel:
    Info:         0/RSP0/CPU0 (RP) (SDR: Owner)
    Info:         0/RSP1/CPU0 (RP) (SDR: Owner)
    Info:         0/0/CPU0 (LC) (SDR: Owner)
    Info:         0/1/CPU0 (LC) (SDR: Owner)
    Info:         0/3/CPU0 (LC) (SDR: Owner)
    Info:         0/5/CPU0 (LC) (SDR: Owner)
    Info:         0/6/CPU0 (LC) (SDR: Owner)
    Install operation 151: load phase started at 04:43:32 PST Sun Sep 20 1987.
    Install operation 151: load phase started at 04:44:45 PST Sun Sep 20 1987.
    Install operation 151: load phase started at 04:45:59 PST Sun Sep 20 1987.
    Info:     The changes made to software configurations will not be persistent across system reloads. Use the command '(admin) install commit' to make changes persistent.
    Info:     Please verify that the system is consistent following the software change using the following commands:
    Info:         show system verify
    Info:         install verify packages
    Install operation 151 completed successfully at 04:46:35 PST Sun Sep 20 1987.

Summary:
    Sub-operation 1:
    Started at: 04:43:32 PST Sun Sep 20 1987
    Install method: Parallel Process Restart
    Summary of changes on nodes 0/RSP0/CPU0, 0/RSP1/CPU0:
        Activated:    asr9k-fwding-5.3.3.CSCux41951-1.0.0
        Impacted:     iosxr-mcast-5.3.3
        No processes affected

    Summary of changes on node 0/0/CPU0:
        Activated:    asr9k-fwding-5.3.3.CSCux41951-1.0.0
        Impacted:     asr9k-fwding-5.3.3
                      asr9k-li-5.3.3
            1 asr9k-li processes affected (0 updated, 0 added, 0 removed, 1 impacted)
            1 asr9k-fwding processes affected (0 updated, 0 added, 0 removed, 1 impacted)

    Summary of changes on node 0/1/CPU0:
        Activated:    asr9k-fwding-5.3.3.CSCux41951-1.0.0
        Impacted:     asr9k-fwding-5.3.3
                      asr9k-li-5.3.3
            1 asr9k-li processes affected (0 updated, 0 added, 0 removed, 1 impacted)
            1 asr9k-fwding processes affected (0 updated, 0 added, 0 removed, 1 impacted)

    Summary of changes on nodes 0/3/CPU0, 0/5/CPU0:
        Activated:    asr9k-fwding-5.3.3.CSCux41951-1.0.0
        Impacted:     asr9k-fwding-5.3.3
                      asr9k-li-5.3.3
            1 asr9k-li processes affected (0 updated, 0 added, 0 removed, 1 impacted)
            1 asr9k-fwding processes affected (0 updated, 0 added, 0 removed, 1 impacted)

    Summary of changes on node 0/6/CPU0:
        Activated:    asr9k-fwding-5.3.3.CSCux41951-1.0.0
        Impacted:     asr9k-fwding-5.3.3
                      asr9k-li-5.3.3
            1 asr9k-li processes affected (0 updated, 0 added, 0 removed, 1 impacted)
            1 asr9k-fwding processes affected (0 updated, 0 added, 0 removed, 1 impacted)

    Sub-operation 2:
    Started at: 04:44:45 PST Sun Sep 20 1987
    Install method: Parallel Process Restart
    Summary of changes on nodes 0/RSP0/CPU0, 0/RSP1/CPU0:
        Activated:    iosxr-ce-5.3.3.CSCux68183-1.0.0
            1 iosxr-ce-5.3.3.CSCux68183 processes affected (1 updated, 0 added, 0 removed, 0 impacted)

[snip]
    Sub-operation 3:
    Started at: 04:45:58 PST Sun Sep 20 1987
    Install method: Parallel Reoload
    Summary of changes on nodes 0/RSP0/CPU0, 0/RSP1/CPU0:
        Activated:    asr9K-doc-supp-6.1.3
                      asr9k-9000v-nV-supp-6.1.3
[snip]
    """
    # it produces a list of all captured groups matching the pattern, i.e.:
    # ['Parallel Process Restart', 'Parallel Process Restart', 'Parallel Reload', 'Parallel Process Restart' ....]
    result = re.findall(install_method, output)
    if result:
        if "Parallel Reload" in result:
            ctx.info("Parallel Reload Pending")
            if re.search(completed_with_failure, output):
                ctx.info("Install completed with failure, going for reload")
            elif re.search(success_oper, output):
                ctx.info("Install completed successfully, going for reload")
            return wait_for_reload(ctx)
        elif "Parallel Process Restart" in result:
            ctx.info("Parallel Process Restart Pending")
            ctx.info("Install completed successfully, going for process restart")
            return True
        else:
            ctx.warning("No Install Method detected.")

    log_install_errors(ctx, output)
    return False


def install_add_remove(ctx, cmd, has_tar=False):
    message = "Waiting the operation to continue asynchronously"
    ctx.info(message)
    ctx.post_status(message)

    output = ctx.send(cmd, timeout=7200)
    result = re.search('Install operation (\d+) \'', output)
    if result:
        op_id = result.group(1)
    else:
        log_install_errors(ctx, output)
        ctx.error("Operation failed")
        return  # for sake of clarity

    op_success = "The install operation will continue asynchronously"
    failed_oper = r'Install operation {} failed'.format(op_id)
    if op_success in output:
        watch_operation(ctx, op_id=op_id)
        output = ctx.send("admin show install log {} detail".format(op_id))
        if re.search(failed_oper, output):
            log_install_errors(ctx, output)
            ctx.error("Operation {} failed".format(op_id))
            return  # for same of clarity

        ctx.info("Operation {} finished successfully".format(op_id))
        if has_tar is True:
            ctx.set_operation_id(ctx.software_packages, op_id)
            ctx.info("The operation {} stored".format(op_id))

        return  # for sake of clarity
    else:
        log_install_errors(ctx, output)
        ctx.error("Operation {} failed".format(op_id))


def install_activate_deactivate(ctx, cmd):
    message = "Waiting the operation to continue asynchronously"
    ctx.info(message)
    ctx.post_status(message)

    op_success = "The install operation will continue asynchronously"
    output = ctx.send(cmd, timeout=7200)
    result = re.search('Install operation (\d+) \'', output)
    if result:
        op_id = result.group(1)
    else:
        log_install_errors(ctx, output)
        ctx.error("Operation failed")
        return

    if op_success in output:
        success = watch_install(ctx, cmd, op_id)
        if not success:
            ctx.error("Reload or boot failure")
            return

        ctx.info("Operation {} finished successfully".format(op_id))
        return
    else:
        log_install_errors(ctx, output)
        ctx.error("Operation {} failed".format(op_id))
        return


def install_remove_all(ctx, cmd, hostname):
    """
    Success Condition:
    RP/0/RSP0/CPU0:RO#admin install remove inactive async

    Install operation 36 '(admin) install remove inactive' started by user 'root' via CLI at 01:14:44 PST Wed Feb 25 1987.
    / 1% complete: The operation can no longer be aborted (ctrl-c for options)
    Info:     This operation will remove the following package:
    Info:         disk0:asr9k-px-5.3.3.CSCuz14049-1.0.0
    - 1% complete: The operation can no longer be aborted (ctrl-c for options)
    \ 1% complete: The operation can no longer be aborted (ctrl-c for options)
    Info:     After this install remove the following install rollback point will no longer be reachable, as the required packages will not be present:
    Info:         15
    | 1% complete: The operation can no longer be aborted (ctrl-c for options)
    Proceed with removing these packages? [confirm]
    / 1% complete: The operation can no longer be aborted (ctrl-c for options)
    The install operation will continue asynchronously.
    RP/0/RSP0/CPU0:RO#Install operation 36 completed successfully at 01:14:51 PST Wed Feb 25 1987.

    Failed Conditions:
    RP/0/RSP0/CPU0:RO(admin)#install remove inactive
    Install operation 588 '(admin) install remove inactive' started by user 'lab'
    via CLI at 00:42:48 PST Tue Feb 24 1987.
    Error:    Cannot proceed with the remove operation because there are no
    Error:    packages that can be removed. Packages can only be removed if they
    Error:    are not part of the active software and not part of the committed
    Error:    software.
    Error:    Suggested steps to resolve this:
    Error:     - check the set of active packages using '(admin) show install
    Error:       active'.
    Error:     - check the committed software using '(admin) show install
    Error:       committed'.
    Error:     - check the set of inactive packages using '(admin) show install
    Error:       inactive'.
    Install operation 588 failed at 00:42:48 PST Tue Feb 24 1987.

    RP/0/RSP0/CPU0:RO(admin)#install remove inactive async
    Error:    Cannot proceed with the operation as another install command is
    Error:    currently in operation.
    Error:    Suggested steps to resolve this:
    Error:     - use 'show install request' to see the state of the current install
    Error:       operation.
    Error:     - re-issue the command when the current operation has completed.
    """

    global plugin_ctx
    plugin_ctx = ctx

    # no op_id is returned from XR for install remove inactive
    # need to figure out the last op_id first

    cmd_show_install_log_reverse = \
        'admin show install log reverse | utility egrep "Install operation [0-9]+ started"'
    output = ctx.send(cmd_show_install_log_reverse, timeout=300)

    if 'No log information' in output:
        op_id = 0
    else:
        result = re.search('Install operation (\d+) started', output)
        if result:
            op_id = int(result.group(1))
        else:
            log_install_errors(ctx, output)
            ctx.error("Operation ID not found by admin show install log reverse")
            return

    # Expected Operation ID
    op_id += 1

    operr = "Install operation {} failed at".format(op_id)
    Error1 = re.compile("Error:     - re-issue the command when the current operation has completed.")
    Error2 = re.compile(operr)
    Proceed_removing = re.compile("\[confirm\]")
    Host_prompt = re.compile(hostname)

    events = [Host_prompt, Error1, Error2, Proceed_removing]
    transitions = [
        (Error1, [0], -1, CommandError("Another install command is currently in operation", hostname), 1800),
        (Error2, [0], -1, CommandError("No packages can be removed", hostname), 1800),
        (Proceed_removing, [0], 2, send_yes, 1800),
        (Host_prompt, [2], -1, None, 1800),
    ]

    if not ctx.run_fsm("Remove Inactive All", cmd, events, transitions, timeout=1800):
        ctx.error("Failed: {}".format(cmd))

    message = "Waiting the operation to continue asynchronously"
    ctx.info(message)
    ctx.post_status(message)

    last_status = None
    no_install = r"There are no install requests in operation"
    op_progress = r"The operation is (\d+)% complete"
    cmd_show_install_request = "admin show install request"
    op_success = "Install operation {} completed successfully".format(op_id)
    propeller = itertools.cycle(["|", "/", "-", "\\", "|", "/", "-", "\\"])

    finish = False
    time_tried = 0
    op_id = str(op_id)
    while not finish:
        try:
            try:
                # this is to catch the successful operation as soon as possible
                ctx.send("", wait_for_string=op_success, timeout=20)
                finish = True
            except ctx.CommandTimeoutError:
                pass

            message = ""
            # on CRS, it is observed that during Add, any command typed hangs for a while
            output = ctx.send(cmd_show_install_request, timeout=300)
            if op_id in output:
                result = re.search(op_progress, output)
                if result:
                    status = result.group(0)
                    message = "{} {}".format(propeller.next(), status)

                if message != last_status:
                    ctx.post_status(message)
                    last_status = message
        except (ConnectionError, ctx.CommandTimeoutError) as e:
            if time_tried > 120:
                raise e

            time_tried += 1
            time.sleep(30)

        if no_install in output:
            break

    cmd_show_install_log = "admin show install log {} detail".format(op_id)
    output = ctx.send(cmd_show_install_log, timeout=300)
    ctx.info(output)

    if op_success in output:
        message = "Remove All Inactive Package(s) Successfully"
        ctx.info(message)
        ctx.post_status(message)
    else:
        ctx.error("Remove All Inactive Package(s) failed")


def build_satellite_list(satellite_ids):
    """
    :param satellite_ids: a string of satellite IDs with comma delimiter and range
    For example, satellite_ids = '100-102,105,106-109,110,160-164,319-320'
    :return: a list of satellite IDs in string
    """

    L = []
    input_list = satellite_ids.split(',')
    for item in input_list:
        if '-' in item:
            m = re.search('(\w+)-(\w+)', item)
            arg1 = int(m.group(1))
            arg2 = int(m.group(2)) + 1
            ilist = range(arg1, arg2)
            slist = []
            for i in ilist:
                slist.append(str(i))
            L = L + slist
        else:
            L.append(item)

    return L


def build_new_argument(L):
    """
    :param L: a list of satellite id in string
    :return: a string of satellite id that includes comma delimiter and range
    """

    LI = [int(x) for x in L]
    LI.sort()

    lrange = len(LI) - 1

    if lrange == 0:
        arg = str(LI[0])
    else:
        # walk thru the list to construct the new string argument
        arg = str(LI[0])
        id = 1
        nexts = ''
        while id < lrange:
            if LI[id - 1] + 1 == LI[id]:
                if nexts != '-':
                    nexts = '-'
            else:
                if nexts == '-':
                    arg = arg + '-' + str(LI[id - 1]) + ',' + str(LI[id])
                    nexts = ''
                else:
                    arg = arg + ',' + str(LI[id])
            id += 1

        id = lrange
        if LI[id - 1] + 1 == LI[id]:
            if nexts == '-':
                arg = arg + '-' + str(LI[id])
            else:
                arg = arg + ',' + str(LI[id])
        else:
            if nexts == '-':
                arg = arg + '-' + str(LI[id - 1]) + ',' + str(LI[id])
                nexts = ''
            else:
                arg = arg + ',' + str(LI[id])

    return arg


def install_satellite_transfer(ctx, satellite_ids):
    """
    RP/0/RP0/CPU0:AGN_PE_11_9k#install nv satellite 160,163 transfer
    Install Op 2: install nv satellite 160,163 transfer
        2 configured satellites have been specified for the transfer operation.
        2 satellites have successfully initiated the transfer operation.

    RP/0/RP0/CPU0:AGN_PE_11_9k#show nv satellite status satellite 161
    Satellite 161
    -------------
      Status: Connected (Transferring new image)
      Redundancy: Active (Group: 100)
      Type: ncs5002
      Displayed device name: Sat161
      MAC address: c472.95a6.87a5
      IPv4 address: 10.0.161.1 (auto, VRF: **nVSatellite)
      Serial Number: FOC1928R0XP
      Remote version: Compatible (older version)
        IOFPGA: 0.17
        MB_MIFPGA: 0.16
        DB_MIFPGA: 0.16
        BIOS: 1.11
        XR: 6.2.25.03I (Available: 6.2.25.05I)
      Received candidate fabric ports:
        nVFabric-TenGigE0/0/78-79 (permanent)
        nVFabric-HundredGigE0/1/0-3 (permanent)
      Configured satellite fabric links:
        HundredGigE0/18/0/5
        -------------------
          Status: Satellite Ready
          Remote ports: TenGigE0/0/0-70

    RP/0/RP0/CPU0:AGN_PE_11_9k#show nv satellite status satellite 161
    Satellite 161
    -------------
      Status: Connected (New image transferred)
      Redundancy: Active (Group: 100)
      Type: ncs5002
      Displayed device name: Sat161
      MAC address: c472.95a6.87a5
      IPv4 address: 10.0.161.1 (auto, VRF: **nVSatellite)
      Serial Number: FOC1928R0XP
      Remote version: Compatible (older version)
        IOFPGA: 0.17
        MB_MIFPGA: 0.16
        DB_MIFPGA: 0.16
        BIOS: 1.11
        XR: 6.2.25.03I (Available: 6.2.25.05I)
      Received candidate fabric ports:
        nVFabric-TenGigE0/0/78-79 (permanent)
        nVFabric-HundredGigE0/1/0-3 (permanent)
      Configured satellite fabric links:
        HundredGigE0/18/0/5
        -------------------
          Status: Satellite Ready
          Remote ports: TenGigE0/0/0-70
    """

    global plugin_ctx
    plugin_ctx = ctx

    # satellite_ids = '100-102,105,106-109,110,160-164,319-320'
    L = build_satellite_list(satellite_ids)
    ctx.info("Checking satellite status: {}".format(','.join(L)))

    # filter invalid cases
    command_success = True
    for id in range(len(L)):
        show_cmd = 'show nv satellite status satellite ' + L[id]
        output = ctx.send(show_cmd)

        if 'No information for satellite' in output:
            ctx.warning("There is no information for Satellite ID {}.".format(L[id]))
            ctx.warning("{}".format(output))
            L[id] = None
            command_success = False

        if 'Status: Connected' not in output:
            ctx.warning("Satellite ID {} Status is not Connected.".format(L[id]))
            ctx.warning("{}".format(output))
            L[id] = None
            command_success = False

        if 'Status: Connected (New image transferred)' in output:
            ctx.info("Satellite ID {} Status: Connected (New image transferred)".format(L[id]))
            L[id] = None

        if 'Remote version: Compatible (latest version)' in output:
            ctx.info("Satellite ID {} Remote version: Compatible (latest version)".format(L[id]))
            L[id] = None

    L = [x for x in L if x is not None]

    if not L:
        if command_success:
            ctx.info("Satellite-Transfer: all satellites are up to date. No action is required.")
            return True
        else:
            ctx.warning("Satellite-Transfer: one or more satellites are not ready")
            return False

    # construct the new argument
    ctx.info("Satellite-Transfer satellites {}".format(','.join(L)))
    arg = build_new_argument(L)

    cmd = 'install nv satellite ' + arg + ' transfer'
    Warning = re.compile("Do you wish to continue\? \[confirm\(y/n\)\]")
    Host_prompt = re.compile(ctx._connection.hostname)

    events = [Host_prompt, Warning]
    transitions = [
        (Warning, [0], -1, send_yes, 30),
        (Host_prompt, [0], -1, None, 30),
    ]

    if not ctx.run_fsm("Satellite-Transfer ", cmd, events, transitions, timeout=30):
        ctx.warning("Failed: {}".format(cmd))
        return False

    ctx.info("Waiting for Satellite-Transfer to complete")
    ctx.post_status("Waiting for Satellite-Transfer to complete")

    timeout = 3600
    poll_time = 180
    time_waited = 3
    begin = time.time()
    time.sleep(time_waited)

    header = "Transferring Satellite Image <br>" + \
             "<pre>" + \
             "Sat-ID  Type       Status\n" + \
             "------  --------   ----------------\n"

    while 1:
        # Waiting for transfer to complete for all satellites
        if time_waited >= timeout:
            break

        status = header
        show_cmd = 'show nv satellite status brief'
        output = ctx.send(show_cmd)
        lines = output.split('\n')
        lines = [x for x in lines if x]

        for line in lines:

            if not line[0].isdigit():
                continue

            sl = line.split()
            elements = len(sl)
            if elements > 5:
                i = 5
                while i < elements:
                    sl[4] = sl[4] + ' ' + sl[i]
                    i += 1

            for id in range(len(L)):
                if L[id] == sl[0]:
                    if 'Transferred' in sl[4]:
                        L[id] = None
                    else:
                        length = len(sl[0])
                        space = 8 - length
                        sat_id = sl[0] + ' ' * space
                        length = len(sl[1])
                        space = 11 - length
                        type = sl[1] + ' ' * space
                        status = status + sat_id + type + sl[4] + '\n'

                    break

        L = [x for x in L if x is not None]

        if not L:
            elapsed = time.time() - begin
            ctx.info("Satellite-Transfer time: {} minute(s) {:.0f} "
                     "second(s)".format(elapsed // 60, elapsed % 60))
            if command_success:
                ctx.info("Satellite-Transfer completed for all the satellites")
                ctx.post_status("Satellite-Transfer completed for all the satellites")
                return True
            else:
                ctx.warning("Satellite-Transfer completed but some satellites were not ready.")
                ctx.post_status("Satellite-Transfer completed but some satellites were not ready.")
                return True
        else:
            status += "</pre>"
            ctx.post_status(status)
            time_waited += poll_time
            time.sleep(poll_time)

    # Some transfer did not ccomplete
    ctx.warning("Satellite-Transfer did not complete for satellites {}.:".format(','.join(L)))
    return False


def install_satellite_activate(ctx, satellite_ids):
    """
    RP/0/RP0/CPU0:AGN_PE_11_9k#install nv satellite 160,161 activate
    The operation will cause an image to be transferred where required, and then activate new versions on the \
    requested satellites.
    WARNING: This may take the requested satellites out of service.
    Do you wish to continue? [confirm(y/n)] y
    Install Op 4: install nv satellite 160-161 activate
      2 configured satellites have been specified for the activate operation.
      2 satellites have successfully initiated the activate operation.

    RP/0/RP0/CPU0:AGN_PE_11_9k#show nv satellite status satellite 161
    Satellite 161
    -------------
      Status: Connected (Installing new image)
      Redundancy: Active (Group: 100)
      Type: ncs5002
      Displayed device name: Sat161
      MAC address: c472.95a6.87a5
      IPv4 address: 10.0.161.1 (auto, VRF: **nVSatellite)
      Serial Number: FOC1928R0XP
      Remote version: Compatible (older version)
        IOFPGA: 0.17
        MB_MIFPGA: 0.16
        DB_MIFPGA: 0.16
        BIOS: 1.11
        XR: 6.2.25.03I (Available: 6.2.25.05I)
      Received candidate fabric ports:
        nVFabric-TenGigE0/0/78-79 (permanent)
        nVFabric-HundredGigE0/1/0-3 (permanent)
      Configured satellite fabric links:
        HundredGigE0/18/0/5
        -------------------
          Status: Satellite Ready
          Remote ports: TenGigE0/0/0-70

    RP/0/RP0/CPU0:AGN_PE_11_9k#show nv satellite status satellite 161
    Satellite 161
    -------------
      Status: Discovery Stalled; Conflict: interface is down
      Type: ncs5002
      Displayed device name: Sat161
      IPv4 address: 10.0.161.1 (auto, VRF: **nVSatellite)
      Serial Number: FOC1928R0XP
      Configured satellite fabric links:
        HundredGigE0/18/0/5
        -------------------
          Status: Discovery Stalled; Conflict: interface is down
          Remote ports: TenGigE0/0/0-70

    RP/0/RP0/CPU0:AGN_PE_11_9k#show nv satellite status satellite 161
    Satellite 161
    -------------
      Status: Connected (Stable)
      Redundancy: Active (Group: 100) (Recovery Delay remaining: 4m 23s)
      Type: ncs5002
      Displayed device name: Sat161
      MAC address: c472.95a6.87a5
      IPv4 address: 10.0.161.1 (auto, VRF: **nVSatellite)
      Serial Number: FOC1928R0XP
      Remote version: Compatible (latest version)
        IOFPGA: 0.17
        MB_MIFPGA: 0.16
        DB_MIFPGA: 0.16
        BIOS: 1.11
        XR: 6.2.25.05I (Latest)
      Received candidate fabric ports:
        nVFabric-TenGigE0/0/78-79 (permanent)
        nVFabric-HundredGigE0/1/0-3 (permanent)
      Configured satellite fabric links:
        HundredGigE0/18/0/5
        -------------------
          Status: Satellite Ready
          Remote ports: TenGigE0/0/0-70
    """

    global plugin_ctx
    plugin_ctx = ctx

    # satellite_ids = '100-102,105,106-109,110,160-164,319-320'
    L = build_satellite_list(satellite_ids)
    ctx.info("Checking satellite status: {}".format(','.join(L)))

    # filter invalid cases
    command_success = True
    for id in range(len(L)):
        show_cmd = 'show nv satellite status satellite ' + L[id]
        output = ctx.send(show_cmd)

        if 'No information for satellite' in output:
            ctx.warning("There is no information for Satellite ID {}.".format(L[id]))
            ctx.warning("{}".format(output))
            L[id] = None
            command_success = False

        if 'Status: Connected' not in output:
            ctx.warning("Satellite ID {} Status is not Connected.".format(L[id]))
            ctx.warning("{}".format(output))
            L[id] = None
            command_success = False

        if 'Remote version: Compatible (latest version)' in output:
            ctx.info("Satellite ID {} Remote version: Compatible (latest version)".format(L[id]))
            L[id] = None

    L = [x for x in L if x is not None]

    if not L:
        if command_success:
            ctx.info("Satellite-Activate: all satellites are up to date. No action is required.")
            return True
        else:
            ctx.warning("Satellite-Activate: one or more satellites are not ready")
            return False

    # construct the new argument
    ctx.info("Satellite-Activate satellites {}".format(','.join(L)))
    arg = build_new_argument(L)

    cmd = 'install nv satellite ' + arg + ' activate'
    Warning = re.compile("Do you wish to continue\? \[confirm\(y/n\)\]")
    Host_prompt = re.compile(ctx._connection.hostname)

    events = [Host_prompt, Warning]
    transitions = [
        (Warning, [0], -1, send_yes, 30),
        (Host_prompt, [0], -1, None, 30),
    ]

    if not ctx.run_fsm("Satellite-Activate", cmd, events, transitions, timeout=30):
        ctx.warning("Failed: {}".format(cmd))
        return False

    ctx.info("Waiting for Satellite-Activate to complete")
    ctx.post_status("Waiting for Satellite-Activate to complete")

    timeout = 5400
    poll_time = 180
    time_waited = 3
    begin = time.time()
    time.sleep(time_waited)

    header = "Activating Satellite Image <br>" + \
             "<pre>" + \
             "Sat-ID  Type       Status\n" + \
             "------  --------   ----------------\n"

    while 1:
        # Waiting for transfer to complete for all satellites
        if time_waited >= timeout:
            break

        status = header
        show_cmd = 'show nv satellite status brief'
        output = ctx.send(show_cmd)
        lines = output.split('\n')
        lines = [x for x in lines if x]

        for line in lines:

            if not line[0].isdigit():
                continue

            sl = line.split()
            elements = len(sl)
            if elements > 5:
                i = 5
                while i < elements:
                    sl[4] = sl[4] + ' ' + sl[i]
                    i += 1

            for id in range(len(L)):
                if L[id] == sl[0]:
                    if sl[4] == 'Connected' or sl[4] == 'Connected (Act)' or sl[4] == 'Connected (Stby)':
                        L[id] = None
                    else:
                        length = len(sl[0])
                        space = 8 - length
                        sat_id = sl[0] + ' ' * space
                        length = len(sl[1])
                        space = 11 - length
                        type = sl[1] + ' ' * space
                        status = status + sat_id + type + sl[4] + '\n'

                    break

        L = [x for x in L if x is not None]

        if not L:
            elapsed = time.time() - begin
            ctx.info("Satellite-Activate time: {} minute(s) {:.0f} "
                     "second(s)".format(elapsed // 60, elapsed % 60))
            if command_success:
                ctx.info("Satellite-Activate completed for all the satellites")
                ctx.post_status("Satellite-Activate completed for all the satellites")
                return True
            else:
                ctx.warning("Satellite-Activate completed but some satellites were not ready.")
                ctx.post_status("Satellite-Activate completed but some satellites were not ready.")
                return True
        else:
            status += "</pre>"
            ctx.post_status(status)
            time_waited += poll_time
            time.sleep(poll_time)

    # Some transfer did not ccomplete
    ctx.warning("Satellite-Activate did not complete for satellites {}.".format(','.join(L)))
    return False


def parse_pkg_list(output):
    """
    :param output: show install active/inactive summary
    :return: a list of active/inactive packages
    """

    pkg_list = []
    flag = False

    lines = output.split('\n')
    lines = [x for x in lines if x]

    for line in lines:
        if 'ctive Packages:' in line:
            flag = True
            continue

        if flag:
            if line[2].isalnum():
                break
            else:
                pkg = line.strip()
                pkg_list.append(pkg)

    return pkg_list


def report_changed_pkg(p, q):
    """
    :param p: a list of packages
    :param q: a list of packages
    :return: a list of packages in q but not in p
    """

    changed = list(set(q) - set(p))
    changed_list = [re.sub(r'^.*:', '', pkg) for pkg in changed]
    changed_list.sort()

    return changed_list
