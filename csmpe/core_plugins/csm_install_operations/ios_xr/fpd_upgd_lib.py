# coding=utf-8
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

plugin_ctx = None


def send_yes(fsm_ctx):
    fsm_ctx.ctrl.sendline('yes')
    return True


def send_newline(fsm_ctx):
    fsm_ctx.ctrl.sendline()
    return True


def fpd_package_installed(ctx):
    """
    :param ctx
    :return: True or False
    """

    active_packages = ctx.send("show install active summary")

    match = re.search("fpd", active_packages)

    if not match:
        return False
    else:
        return True


def fpd_needs_upgd(ctx, location, fpd_type):
    """
    :param ctx
    :param location
    :return: True or False

    Platform: ASR9000
    RP/0/RSP0/CPU0:cxr1#admin show hw-module fpd location 0/1/CPU0

    ===================================== ==========================================
                                          Existing Field Programmable Devices
                                          ==========================================
                                            HW                       Current SW Upg/
    Location     Card Type                Version Type Subtype Inst   Version   Dng?
    ============ ======================== ======= ==== ======= ==== =========== ====
    0/1/CPU0     A9K-MOD400-SE              1.0   lc   cbc     0      39.07     No
                                                  lc   rommon  0       8.43     No
                                                  lc   fpga2   0       1.91     Yes
                                                  lc   fsbl    0       1.96     Yes
                                                  lc   lnxfw   0       1.96     Yes
                                                  lc   fpga10  0       1.19     No
    --------------------------------------------------------------------------------
    NOTES:
    1.  One or more FPD needs an upgrade.  This can be accomplished
        using the "admin> upgrade hw-module fpd <fpd> location <loc>" CLI.
    """

    need_upgd = False
    sl = ['Subtype', 'Inst', 'Dng']
    dl = {}
    check = False
    cmd = 'admin show hw-module fpd location ' + location

    output = ctx.send(cmd)
    lines = output.split('\n')
    lines = [x for x in lines if x]
    for line in lines:

        if '------------------------------------' in line or 'NOTES:' in line:
            break

        if line[0:8] == 'Location':
            for s in sl:
                n = line.find(s)
                if n != -1:
                    dl[str(s)] = n
                else:
                    ctx.error("unrecognized show hw-module fpd header {}".format(line))
                    return False
            continue

        if check:
            type = line[dl['Subtype']:dl['Inst']].strip()
            if type == fpd_type or fpd_type == 'all':
                if 'Yes' in line[dl['Dng']:]:
                    need_upgd = True
                    break
                else:
                    continue
            else:
                continue

        if line[0].isdigit():
            check = True
            type = line[dl['Subtype']:dl['Inst']].strip()
            if type == fpd_type or fpd_type == 'all':
                if 'Yes' in line[dl['Dng']:]:
                    need_upgd = True
                    break
                else:
                    continue
            else:
                continue

    return need_upgd


def fpd_locations(ctx):
    """
    :param ctx
    :return: A list of all locations

    Platform: ASR9000
    RP/0/RSP0/CPU0:cxr1#admin show hw-module fpd location all

    ===================================== ==========================================
                                          Existing Field Programmable Devices
                                          ==========================================
                                            HW                       Current SW Upg/
    Location     Card Type                Version Type Subtype Inst   Version   Dng?
    ============ ======================== ======= ==== ======= ==== =========== ====
    0/RSP0/CPU0  A9K-RSP440-TR              1.0   lc   cbc     0      16.116    No
                                                  lc   fpga2   0       1.10     No
                                                  lc   fpga3   0       4.09     No
                                                  lc   fpga1   0       0.11     No
                                                  lc   rommon  0       0.76     No
    --------------------------------------------------------------------------------
    0/FT0/SP     ASR-9904-FAN               1.0   ft   cbc     7      31.05     No
    --------------------------------------------------------------------------------
    0/BPID0/SP   ASR-9904-BPID2             1.0   bp   cbc     11      7.105    No
    --------------------------------------------------------------------------------
    0/PS0/M0/SP  PWR-3KW-AC-V2              1.0   pm   fpga14  13      3.18^    No
                                                  pm   fpga15  13      3.06^    No
                                                  pm   fpga16  13      3.12^    No
    --------------------------------------------------------------------------------
    0/PS0/M3/SP  PWR-3KW-AC-V2              1.0   pm   fpga14  16      3.18^    No
                                                  pm   fpga15  16      3.06^    No
                                                  pm   fpga16  16      3.12^    No
    --------------------------------------------------------------------------------
    0/RSP1/CPU0  A9K-RSP440-TR              1.0   lc   cbc     0      16.116    No
                                                  lc   fpga3   0       4.09     No
                                                  lc   fpga2   0       1.10     No
                                                  lc   fpga1   0       0.11     No
                                                  lc   rommon  0       0.76     No
    --------------------------------------------------------------------------------
    0/0/CPU0     A9K-MOD80-SE               1.0   lc   cbc     0      20.118    No
                                                  lc   fpga4   0       1.05     No
                                                  lc   fpga2   0       1.04     No
                                                  lc   rommon  0       3.03     No
    --------------------------------------------------------------------------------
    0/0/0        A9K-MPA-20X1GE             1.102 spa  fpga3   0       1.00     Yes
    --------------------------------------------------------------------------------
    0/1/CPU0     A9K-MOD400-SE              1.0   lc   cbc     0      39.07     No
                                                  lc   rommon  0       8.43     No
                                                  lc   fpga2   0       1.91     Yes
                                                  lc   fsbl    0       1.96     Yes
                                                  lc   lnxfw   0       1.96     Yes
                                                  lc   fpga10  0       1.19     No
    --------------------------------------------------------------------------------
    0/1/0        A9K-MPA-20X10GE            1.0   spa  fpga5   0       1.14     Yes
    --------------------------------------------------------------------------------
    NOTES:
    1.  One or more FPD needs an upgrade.  This can be accomplished
        using the "admin> upgrade hw-module fpd <fpd> location <loc>" CLI.
    2.  ^ One or more FPD will be intentionally skipped from upgrade using CLI with option "all" or during "Auto fpd".
          It can be upgraded only using the "admin> upgrade hw-module fpd <fpd> location <loc>" CLI with exact location.
    """

    sl = ['Location', 'Card Type']
    dl = {}
    locations = []

    output = ctx.send("admin show hw-module fpd location all")
    lines = output.split('\n')
    lines = [x for x in lines if x]
    for line in lines:
        if line[0:8] == 'Location':
            for s in sl:
                n = line.find(s)
                if n != -1:
                    dl[str(s)] = n
                else:
                    ctx.error("unrecognized admin show hw-module fpd location header {}".format(line))
                    return False

        if line[0].isdigit():
            location = line[dl['Location']:dl['Card Type']].strip()
            locations.append(location)

        if 'NOTES:' in line:
            break

    return locations


def hw_fpd_upgd(ctx, location, type):
    """
    :param ctx
    :param location
    :return: True or False

    Platform: ASR9000
    RP/0/RSP0/CPU0:vkg1#admin upgrade hw-module fpd all location 0/RSP0/CPU0
    Wed Jul  1 01:57:15.137 UTC

    ***** UPGRADE WARNING MESSAGE: *****
      *  This upgrade operation has a maximum timout of 160 minutes.  *
      *  If you are executing the cmd for one specific location and  *
      *  card in that location reloads or goes down for some reason  *
      *  you can press CTRL-C to get back the RP's prompt.           *
      *  If you are executing the cmd for _all_ locations and a node *
      *  reloads or is down please allow other nodes to finish the   *
      *  upgrade process before pressing CTRL-C.                     *

    % RELOAD REMINDER:
      - The upgrade operation of the target module will not interrupt its normal
        operation. However, for the changes to take effect, the target module
        will need to be manually reloaded after the upgrade operation. This can
        be accomplished with the use of "hw-module <target> reload" command.
      - If automatic reload operation is desired after the upgrade, please use
        the "reload" option at the end of the upgrade command.
      - The output of "show hw-module fpd location" command will not display
        correct version information after the upgrade if the target module is
        not reloaded.
    NOTE: Chassis CLI will not be accessible while upgrade is in progress.
    Continue? [confirm]


    FPD upgrade in progress on some hardware, reload/configuration change
    on those is not recommended as it might cause HW programming failure
    and result in RMA of the hardware.


    Starting the upgrade/download of following FPDs:
    =========== ==== ======= ======= =========== =========
                                       Current    Upg/Dng
    Location    Type Subtype Upg/Dng   Version    Version
    =========== ==== ======= ======= =========== =========
    0/RSP0/CPU0 lc   fpga2   upg         1.06        1.09
                lc   fpga    upg         0.10        0.11
                lc   rommon  upg         0.71        0.75
    ------------------------------------------------------
    FPD upgrade in progress. Max timeout remaining 89 min.
    FPD upgrade in progress. Max timeout remaining 88 min.
    FPD upgrade in progress. Max timeout remaining 87 min.
    FPD upgrade in progress. Max timeout remaining 86 min.
    FPD upgrade in progress. Max timeout remaining 85 min.
    FPD upgrade in progress. Max timeout remaining 84 min.
    FPD upgrade in progress. Max timeout remaining 83 min.
    FPD upgrade in progress. Max timeout remaining 82 min.
    FPD upgrade in progress. Max timeout remaining 81 min.
    FPD upgrade in progress. Max timeout remaining 80 min.
    Successfully upgraded     fpga2 for        A9K-RSP440-TR on location 0/RSP0/CPU0 from  1.06 to  1.09
    Successfully upgraded      fpga for        A9K-RSP440-TR on location 0/RSP0/CPU0 from  0.10 to  0.11
    Successfully upgraded    rommon for        A9K-RSP440-TR on location 0/RSP0/CPU0 from  0.71 to  0.75


    FPD upgrade has ended.

    RP/0/RSP0/CPU0:RO#admin upgrade hw-module fpd all location 0/RSP0/CPU0
    Fri Jun 30 16:16:27.326 PST

    ***** UPGRADE WARNING MESSAGE: *****
      *  This upgrade operation has a maximum timout of 90 minutes.  *
      *  If you are executing the cmd for one specific location and  *
      *  card in that location reloads or goes down for some reason  *
      *  you can press CTRL-C to get back the RP's prompt.           *
      *  If you are executing the cmd for _all_ locations and a node *
      *  reloads or is down please allow other nodes to finish the   *
      *  upgrade process before pressing CTRL-C.                     *

    % RELOAD REMINDER:
      - The upgrade operation of the target module will not interrupt its normal
        operation. However, for the changes to take effect, the target module
        will need to be manually reloaded after the upgrade operation. This can
        be accomplished with the use of "hw-module <target> reload" command.
      - If automatic reload operation is desired after the upgrade, please use
        the "reload" option at the end of the upgrade command.
      - The output of "show hw-module fpd location" command will not display
        correct version information after the upgrade if the target module is
        not reloaded.
    NOTE: Chassis CLI will not be accessible while upgrade is in progress.
    Continue ? [no]: yes



    FPD upgrade in progress on some hardware, reload/configuration change
    on those is not recommended as it might cause HW programming failure
    and result in RMA of the hardware.


    Starting the upgrade/download of following FPDs:
    =========== ==== ======= ======= =========== =========
                                       Current    Upg/Dng
    Location    Type Subtype Upg/Dng   Version    Version
    =========== ==== ======= ======= =========== =========
    0/RSP0/CPU0 lc   fpga2   upg         1.09        1.10
                lc   rommon  upg         0.75        0.76
    ------------------------------------------------------
    FPD upgrade in progress. Max timeout remaining 89 min.
    FPD upgrade in progress. Max timeout remaining 88 min.
    Successfully upgraded     fpga2 for        A9K-RSP440-SE on location 0/RSP0/CPU0 from  1.09 to  1.10
    Successfully upgraded    rommon for        A9K-RSP440-SE on location 0/RSP0/CPU0 from  0.75 to  0.76


    FPD upgrade has ended.
    """
    global plugin_ctx
    plugin_ctx = ctx

    cmd = 'admin upgrade hw-module fpd ' + type + ' location ' + location

    # There can be two different prompts
    CONTINUE_YES = re.compile("Continue\? \[confirm\]")
    CONTINUE_UPGD = re.compile("Continue \? \[no\]:")
    END_UPGD = re.compile("FPD upgrade has ended.")
    COMPLETE_UPGD = re.compile("FPD upgrade completed. Auto-reload triggered")
    HOST_PROMPT = re.compile(ctx.prompt)

    events = [CONTINUE_YES, CONTINUE_UPGD, END_UPGD, COMPLETE_UPGD, HOST_PROMPT]
    transitions = [
        (CONTINUE_YES, [0], 1, send_newline, 9600),
        (CONTINUE_UPGD, [0, 1], 2, send_yes, 9600),
        (END_UPGD, [1, 2], 3, None, 9600),
        (COMPLETE_UPGD, [1, 2], 3, None, 9600),
        (HOST_PROMPT, [3], -1, None, 9600)
    ]

    if not ctx.run_fsm("Upgrade hw-module fpd", cmd, events, transitions, timeout=9600):
        ctx.warning("Failed: {}".format(cmd))
        return False

    return True


def fpd_check_status(ctx, location, type):
    """
    :param ctx
    :param locations
    :return: True or False

    Platform: asr9000
    RP/0/RSP0/CPU0:cxr1#admin show hw-module fpd location all
    Fri Jun 30 17:57:53.343 UTC

    ===================================== ==========================================
                                          Existing Field Programmable Devices
                                          ==========================================
                                            HW                       Current SW Upg/
    Location     Card Type                Version Type Subtype Inst   Version   Dng?
    ============ ======================== ======= ==== ======= ==== =========== ====
    0/RSP0/CPU0  A9K-RSP440-TR              1.0   lc   cbc     0      16.116    No
                                                  lc   fpga1   0       0.11     No
                                                  lc   fpga3   0       4.09     No
                                                  lc   fpga2   0       1.10     No
                                                  lc   rommon  0       0.76     No
    --------------------------------------------------------------------------------
    0/FT0/SP     ASR-9904-FAN               1.0   ft   cbc     7      31.05     No
    --------------------------------------------------------------------------------
    0/BPID0/SP   ASR-9904-BPID2             1.0   bp   cbc     11      7.105    No
    --------------------------------------------------------------------------------
    0/PS0/M0/SP  PWR-3KW-AC-V2              1.0   pm   fpga14  13      3.18^    No
                                                  pm   fpga15  13      3.06^    No
                                                  pm   fpga16  13      3.12^    No
    --------------------------------------------------------------------------------
    0/PS0/M3/SP  PWR-3KW-AC-V2              1.0   pm   fpga14  16      3.18^    No
                                                  pm   fpga15  16      3.06^    No
                                                  pm   fpga16  16      3.12^    No
    --------------------------------------------------------------------------------
    0/RSP1/CPU0  A9K-RSP440-TR              1.0   lc   cbc     0      16.116    No
                                                  lc   fpga1   0       0.11     No
                                                  lc   fpga2   0       1.10     No
                                                  lc   fpga3   0       4.09     No
                                                  lc   rommon  0       0.76     No
    --------------------------------------------------------------------------------
    0/0/CPU0     A9K-MOD80-SE               1.0   lc   cbc     0      20.118    No
                                                  lc   fpga2   0       1.04     No
                                                  lc   fpga4   0       1.05     No
                                                  lc   rommon  0       3.03     No
    --------------------------------------------------------------------------------
    0/0/0        A9K-MPA-20X1GE             1.102 spa  fpga3   0       1.01     No
    --------------------------------------------------------------------------------
    0/1/CPU0     A9K-MOD400-SE              1.0   lc   cbc     0      39.07     No
                                                  lc   rommon  0       8.43     No
                                                  lc   fpga2   0       1.93     No
                                                  lc   fsbl    0       1.100    No
                                                  lc   lnxfw   0       1.100    No
                                                  lc   fpga10  0       1.19     No
    --------------------------------------------------------------------------------
    0/1/0        A9K-MPA-20X10GE            1.0   spa  fpga5   0       1.16     No
    --------------------------------------------------------------------------------
    NOTES:
    1.  ^ One or more FPD will be intentionally skipped from upgrade using CLI with option "all" or during "Auto fpd".
          It can be upgraded only using the "admin> upgrade hw-module fpd <fpd> location <loc>" CLI with exact location.
    """

    upgd_result = True
    if fpd_needs_upgd(ctx, location, type):
        upgd_result = False
        cmd = 'admin show hw-module fpd location ' + location
        output = ctx.send(cmd)
        ctx.warning("FPD Upgrade result for {}".format(cmd))
        ctx.warning("{}".format(output))

    return upgd_result


def hw_fpd_reload(ctx, location):
    """
    :param ctx
    :param location:
    :return: True or False

    Platform: ASR9000
    RP/0/RSP0/CPU0:RP2#admin reload location all
    Mon Jun 29 20:59:37.902 PST
    Some active software packages are not yet committed. Proceed?[confirm]

    Preparing system for backup. This may take a few minutes especially for large configurations.
            Status report: node0_RSP0_CPU0: START TO BACKUP
            Status report: node0_RSP0_CPU0: BACKUP HAS COMPLETED SUCCESSFULLY
    [Done]
    Proceed with reload? [confirm]RP/0/RSP0/CPU0::This node received reload command. Reloading in 5 secs
    """
    global plugin_ctx
    plugin_ctx = ctx

    cmd = 'admin reload location ' + location
    fsm_name = 'Reload location ' + location

    # Seeing this message without the reboot prompt indicates a non-reload situation
    PROCEED_RELOAD = re.compile("software packages are not yet committed. Proceed\?\[confirm\]")
    DONE = re.compile(re.escape("[Done]"))
    PROCEED = re.compile(re.escape("Proceed with reload? [confirm]"))

    events = [PROCEED_RELOAD, DONE, PROCEED]
    transitions = [
        (PROCEED_RELOAD, [0], 1, send_newline, 300),
        (DONE, [0, 1], 2, None, 300),
        (PROCEED, [0, 1, 2], -1, send_newline, 300)
    ]

    if not ctx.run_fsm(fsm_name, cmd, events, transitions, timeout=300):
        ctx.warning("Failed: {}".format(cmd))
        return False

    return True


def active_rsp_location(ctx):
    """
    :param ctx
    :return: the location of the active RSP / RP
    """

    location = ''
    cmd = 'show platform | include Active'
    output = ctx.send(cmd)

    lines = output.split('\n')
    lines = [x for x in lines if x]
    for line in lines:
        if line[0].isdigit():
            location = line[0:16].strip()

    return location


def cbc_pwr_only(ctx):
    """
    :param ctx
    :return: True or False

    Platform: ASR9000
    RP/0/RSP0/CPU0:cxr1#admin show hw-module fpd location all

    ===================================== ==========================================
                                          Existing Field Programmable Devices
                                          ==========================================
                                            HW                       Current SW Upg/
    Location     Card Type                Version Type Subtype Inst   Version   Dng?
    ============ ======================== ======= ==== ======= ==== =========== ====
    0/RSP0/CPU0  A9K-RSP440-TR              1.0   lc   cbc     0      16.116    No
                                                  lc   fpga2   0       1.10     No
                                                  lc   fpga3   0       4.09     No
                                                  lc   fpga1   0       0.11     No
                                                  lc   rommon  0       0.76     No
    --------------------------------------------------------------------------------
    0/FT0/SP     ASR-9904-FAN               1.0   ft   cbc     7      31.05     No
    --------------------------------------------------------------------------------
    0/BPID0/SP   ASR-9904-BPID2             1.0   bp   cbc     11      7.105    No
    --------------------------------------------------------------------------------
    0/PS0/M0/SP  PWR-3KW-AC-V2              1.0   pm   fpga14  13      3.18^    No
                                                  pm   fpga15  13      3.06^    No
                                                  pm   fpga16  13      3.12^    No
    --------------------------------------------------------------------------------
    0/PS0/M3/SP  PWR-3KW-AC-V2              1.0   pm   fpga14  16      3.18^    No
                                                  pm   fpga15  16      3.06^    No
                                                  pm   fpga16  16      3.12^    No
    --------------------------------------------------------------------------------
    0/RSP1/CPU0  A9K-RSP440-TR              1.0   lc   cbc     0      16.116    No
                                                  lc   fpga3   0       4.09     No
                                                  lc   fpga2   0       1.10     No
                                                  lc   fpga1   0       0.11     No
                                                  lc   rommon  0       0.76     No
    --------------------------------------------------------------------------------
    0/0/CPU0     A9K-MOD80-SE               1.0   lc   cbc     0      20.118    No
                                                  lc   fpga4   0       1.05     No
                                                  lc   fpga2   0       1.04     No
                                                  lc   rommon  0       3.03     No
    --------------------------------------------------------------------------------
    0/0/0        A9K-MPA-20X1GE             1.102 spa  fpga3   0       1.00     Yes
    --------------------------------------------------------------------------------
    0/1/CPU0     A9K-MOD400-SE              1.0   lc   cbc     0      39.07     No
                                                  lc   rommon  0       8.43     No
                                                  lc   fpga2   0       1.91     Yes
                                                  lc   fsbl    0       1.96     Yes
                                                  lc   lnxfw   0       1.96     Yes
                                                  lc   fpga10  0       1.19     No
    --------------------------------------------------------------------------------
    0/1/0        A9K-MPA-20X10GE            1.0   spa  fpga5   0       1.14     Yes
    --------------------------------------------------------------------------------
    NOTES:
    1.  One or more FPD needs an upgrade.  This can be accomplished
        using the "admin> upgrade hw-module fpd <fpd> location <loc>" CLI.
    2.  ^ One or more FPD will be intentionally skipped from upgrade using CLI with option "all" or during "Auto fpd".
          It can be upgraded only using the "admin> upgrade hw-module fpd <fpd> location <loc>" CLI with exact location.
    """

    avoid_reload = True
    sl = ['Type', 'Subtype', 'Inst', 'Dng']
    dl = {}
    check = False
    cmd = 'admin show hw-module fpd location all'

    output = ctx.send(cmd)
    lines = output.split('\n')
    lines = [x for x in lines if x]
    for line in lines:

        if '------------------------------------' in line:
            continue

        if 'NOTES:' in line:
            break

        if line[0:8] == 'Location':
            for s in sl:
                n = line.find(s)
                if n != -1:
                    dl[str(s)] = n
                else:
                    ctx.warning("unrecognized show hw-module fpd header {}".format(line))
                    return False
            continue

        if check:
            subtype = line[dl['Subtype']:dl['Inst']].strip()
            type = line[dl['Type']:dl['Subtype']].strip()
            if 'pm' in type:
                continue
            if 'Yes' in line[dl['Dng']:] and 'cbc' not in subtype:
                avoid_reload = False
                break
            else:
                continue

        if line[0].isdigit():
            check = True
            subtype = line[dl['Subtype']:dl['Inst']].strip()
            type = line[dl['Type']:dl['Subtype']].strip()
            if 'pm' in type:
                continue
            if 'Yes' in line[dl['Dng']:] and 'cbc' not in subtype:
                avoid_reload = False
                break
            else:
                continue

    return avoid_reload
