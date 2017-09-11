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

import time
import re

plugin_ctx = None


def send_yes(fsm_ctx):
    fsm_ctx.ctrl.sendline('yes')
    return True


def fpd_needs_upgd(ctx, fpd_location, fpd_type):

    """
    :param ctx
    :return: True or False

    Platform: NCS5500
    RP/0/RP0/CPU0:freta1.55#show hw-module fpd
                                                                       FPD Versions
                                                                   =================
    Location   Card type        HWver FPD device       ATR Status   Running Programd
    ------------------------------------------------------------------------------
    0/0       NC55-18H18F       1.0   MIFPGA               CURRENT    0.03    0.03
    0/0       NC55-18H18F       1.0   Bootloader           CURRENT    1.11    1.11
    0/0       NC55-18H18F       1.0   IOFPGA               CURRENT    0.20    0.20
    0/1       NC55-24X100G-SE   1.0   MIFPGA               CURRENT    0.03    0.03
    0/1       NC55-24X100G-SE   1.0   Bootloader           NEED UPGD  1.09    1.09
    0/1       NC55-24X100G-SE   1.0   IOFPGA               NEED UPGD  0.08    0.08
    0/7       NC55-36X100G-S    1.0   MIFPGA               CURRENT    0.06    0.06
    0/7       NC55-36X100G-S    1.0   Bootloader           CURRENT    1.11    1.11
    0/7       NC55-36X100G-S    1.0   IOFPGA               CURRENT    0.09    0.09
    0/RP0     NC55-RP           1.1   Bootloader           NEED UPGD  9.21    9.21
    0/RP0     NC55-RP           1.1   IOFPGA               NEED UPGD  0.08    0.08
    0/RP1     NC55-RP           1.1   Bootloader           NEED UPGD  9.21    9.21
    0/RP1     NC55-RP           1.1   IOFPGA               NEED UPGD  0.08    0.08
    0/FC0     NC55-5508-FC      1.0   Bootloader           CURRENT    1.70    1.70
    0/FC0     NC55-5508-FC      1.0   IOFPGA               NEED UPGD  0.15    0.15
    0/FC1     NC55-5508-FC      1.0   Bootloader           NEED UPGD  1.65    1.65
    0/FC1     NC55-5508-FC      1.0   IOFPGA               NEED UPGD  0.13    0.13
    0/FC3     NC55-5508-FC      1.0   Bootloader           NEED UPGD  1.65    1.65
    0/FC3     NC55-5508-FC      1.0   IOFPGA               NEED UPGD  0.13    0.13
    0/FC5     NC55-5508-FC      1.0   Bootloader           NEED UPGD  1.65    1.65
    0/FC5     NC55-5508-FC      1.0   IOFPGA               NEED UPGD  0.13    0.13
    0/SC0     NC55-SC           1.4   Bootloader           NEED UPGD  1.65    1.65
    0/SC0     NC55-SC           1.4   IOFPGA               NEED UPGD  0.07    0.07
    0/SC1     NC55-SC           1.4   Bootloader           NEED UPGD  1.65    1.65
    0/SC1     NC55-SC           1.4   IOFPGA               NEED UPGD  0.07    0.07
    """

    need_upgd = []
    sl = ['Card', 'FPD', 'ATR', 'Status', 'Running']
    dl = {}

    output = ctx.send("show hw-module fpd", timeout=600)
    lines = output.split('\n')
    lines = [x for x in lines if x]
    for line in lines:
        line = line.strip()

        if line[0:8] == 'Location':
            for s in sl:
                n = line.find(s)
                if n != -1:
                    if s == 'Card':
                        n -= 1
                    dl[str(s)] = n
                else:
                    ctx.error("unrecognized show hw-module fpd header {}".format(line))
                    return False

        if line[0].isdigit():
            status = line[dl['Status']:dl['Running']].strip()
            location = line[0:dl['Card']].strip()
            type = line[dl['FPD']:dl['ATR']].strip()
            if fpd_location == 'all' and fpd_type == 'all':
                if 'NEED UPGD'in status:
                    need_upgd.append(location)
            elif fpd_location and not fpd_type:
                if location == fpd_location:
                    if 'NEED UPGD'in status:
                        need_upgd.append(location)
                else:
                    continue
            elif not fpd_location and fpd_type:
                if type == fpd_type:
                    if 'NEED UPGD' in status:
                        need_upgd.append(location)
                else:
                    continue
            else:
                if location == fpd_location and type == fpd_type:
                    if 'NEED UPGD' in status:
                        need_upgd.append(location)
                        break
                else:
                    continue

    need_upgd = list(set(need_upgd))
    return need_upgd


def fpd_is_current(ctx, fpd_location, fpd_type):
    """
    :param ctx
    :return: True or False

    Platform: NCS5500
    RP/0/RP0/CPU0:freta1.55#show hw-module fpd
                                                                   FPD Versions
                                                                   =================
    Location   Card type        HWver FPD device       ATR Status   Running Programd
    ------------------------------------------------------------------------------
    0/0       NC55-18H18F       1.0   MIFPGA               CURRENT    0.03    0.03
    0/0       NC55-18H18F       1.0   Bootloader           CURRENT    1.11    1.11
    0/0       NC55-18H18F       1.0   IOFPGA               CURRENT    0.20    0.20
    0/1       NC55-24X100G-SE   1.0   MIFPGA               CURRENT    0.03    0.03
    0/1       NC55-24X100G-SE   1.0   Bootloader           CURRENT    1.11    1.11
    0/1       NC55-24X100G-SE   1.0   IOFPGA               CURRENT    0.12    0.12
    0/7       NC55-36X100G-S    1.0   MIFPGA               CURRENT    0.06    0.06
    0/7       NC55-36X100G-S    1.0   Bootloader           CURRENT    1.11    1.11
    0/7       NC55-36X100G-S    1.0   IOFPGA               CURRENT    0.09    0.09
    0/RP0     NC55-RP           1.1   Bootloader           RLOAD REQ  9.21    9.23
    0/RP0     NC55-RP           1.1   IOFPGA               RLOAD REQ  0.08    0.09
    0/RP1     NC55-RP           1.1   Bootloader           RLOAD REQ  9.21    9.23
    0/RP1     NC55-RP           1.1   IOFPGA               RLOAD REQ  0.08    0.09
    0/FC0     NC55-5508-FC      1.0   Bootloader           CURRENT    1.70    1.70
    0/FC0     NC55-5508-FC      1.0   IOFPGA               RLOAD REQ  0.15    0.16
    0/FC1     NC55-5508-FC      1.0   Bootloader           RLOAD REQ  1.65    1.70
    0/FC1     NC55-5508-FC      1.0   IOFPGA               RLOAD REQ  0.13    0.16
    0/FC3     NC55-5508-FC      1.0   Bootloader           RLOAD REQ  1.65    1.70
    0/FC3     NC55-5508-FC      1.0   IOFPGA               RLOAD REQ  0.13    0.16
    0/FC5     NC55-5508-FC      1.0   Bootloader           RLOAD REQ  1.65    1.70
    0/FC5     NC55-5508-FC      1.0   IOFPGA               RLOAD REQ  0.13    0.16
    0/SC0     NC55-SC           1.4   Bootloader           RLOAD REQ  1.65    1.70
    0/SC0     NC55-SC           1.4   IOFPGA               RLOAD REQ  0.07    0.08
    0/SC1     NC55-SC           1.4   Bootloader           RLOAD REQ  1.65    1.70
    0/SC1     NC55-SC           1.4   IOFPGA               RLOAD REQ  0.07    0.08
    """

    is_current = True
    sl = ['Card', 'FPD', 'ATR', 'Status', 'Running']
    dl = {}

    output = ctx.send("show hw-module fpd", timeout=600)
    lines = output.split('\n')
    lines = [x for x in lines if x]
    for line in lines:
        line = line.strip()

        if line[0:8] == 'Location':
            for s in sl:
                n = line.find(s)
                if n != -1:
                    if s == 'Card':
                        n -= 1
                    dl[str(s)] = n
                else:
                    ctx.error("unrecognized show hw-module fpd header {}".format(line))
                    return False

        if line[0].isdigit():
            status = line[dl['Status']:dl['Running']].strip()
            location = line[0:dl['Card']].strip()
            type = line[dl['FPD']:dl['ATR']].strip()
            if 'N/A' in status:
                continue
            if fpd_location == 'all' and fpd_type == 'all':
                if 'CURRENT' not in status:
                    is_current = False
                    break
            elif fpd_location and not fpd_type:
                if location == fpd_location:
                    if 'CURRENT' not in status:
                        is_current = False
                        break
                else:
                    continue
            elif not fpd_location and fpd_type:
                if type == fpd_type:
                    if 'CURRENT' not in status:
                        is_current = False
                        break
                else:
                    continue
            else:
                if location == fpd_location and type == fpd_type:
                    if 'CURRENT' not in status:
                        is_current = False
                        break
                else:
                    continue

    return is_current


def fpd_needs_reload(ctx, fpd_location, fpd_type):
    """
    :param ctx
    :return: True or False

    Platform: NCS5500
    RP/0/RP0/CPU0:freta1.55#show hw-module fpd
                                                                   FPD Versions
                                                                   =================
    Location   Card type        HWver FPD device       ATR Status   Running Programd
    ------------------------------------------------------------------------------
    0/0       NC55-18H18F       1.0   MIFPGA               CURRENT    0.03    0.03
    0/0       NC55-18H18F       1.0   Bootloader           CURRENT    1.11    1.11
    0/0       NC55-18H18F       1.0   IOFPGA               CURRENT    0.20    0.20
    0/1       NC55-24X100G-SE   1.0   MIFPGA               CURRENT    0.03    0.03
    0/1       NC55-24X100G-SE   1.0   Bootloader           CURRENT    1.11    1.11
    0/1       NC55-24X100G-SE   1.0   IOFPGA               CURRENT    0.12    0.12
    0/7       NC55-36X100G-S    1.0   MIFPGA               CURRENT    0.06    0.06
    0/7       NC55-36X100G-S    1.0   Bootloader           CURRENT    1.11    1.11
    0/7       NC55-36X100G-S    1.0   IOFPGA               CURRENT    0.09    0.09
    0/RP0     NC55-RP           1.1   Bootloader           RLOAD REQ  9.21    9.23
    0/RP0     NC55-RP           1.1   IOFPGA               RLOAD REQ  0.08    0.09
    0/RP1     NC55-RP           1.1   Bootloader           RLOAD REQ  9.21    9.23
    0/RP1     NC55-RP           1.1   IOFPGA               RLOAD REQ  0.08    0.09
    0/FC0     NC55-5508-FC      1.0   Bootloader           CURRENT    1.70    1.70
    0/FC0     NC55-5508-FC      1.0   IOFPGA               RLOAD REQ  0.15    0.16
    0/FC1     NC55-5508-FC      1.0   Bootloader           RLOAD REQ  1.65    1.70
    0/FC1     NC55-5508-FC      1.0   IOFPGA               RLOAD REQ  0.13    0.16
    0/FC3     NC55-5508-FC      1.0   Bootloader           RLOAD REQ  1.65    1.70
    0/FC3     NC55-5508-FC      1.0   IOFPGA               RLOAD REQ  0.13    0.16
    0/FC5     NC55-5508-FC      1.0   Bootloader           RLOAD REQ  1.65    1.70
    0/FC5     NC55-5508-FC      1.0   IOFPGA               RLOAD REQ  0.13    0.16
    0/SC0     NC55-SC           1.4   Bootloader           RLOAD REQ  1.65    1.70
    0/SC0     NC55-SC           1.4   IOFPGA               RLOAD REQ  0.07    0.08
    0/SC1     NC55-SC           1.4   Bootloader           RLOAD REQ  1.65    1.70
    0/SC1     NC55-SC           1.4   IOFPGA               RLOAD REQ  0.07    0.08

    Platform: NCS1K
    RP/0/RP0/CPU0:PROD_19#show hw fpd
    Fri Jul 14 02:56:06.415 IST
                                                                   FPD Versions
                                                                   =================
    Location   Card type        HWver FPD device       ATR Status   Running Programd
    ------------------------------------------------------------------------------
    0/0       NCS1002-K9        1.2   CDSP_PORT_05         CURRENT    3.76    3.76
    0/0       NCS1002-K9        1.2   CDSP_PORT_06         CURRENT    3.76    3.76
    0/0       NCS1002-K9        1.2   CDSP_PORT_12         CURRENT    3.76    3.76
    0/0       NCS1002-K9        1.2   CDSP_PORT_13         CURRENT    3.76    3.76
    0/0       NCS1002-K9        1.2   CDSP_PORT_19         CURRENT    3.76    3.76
    0/0       NCS1002-K9        1.2   CDSP_PORT_20         CURRENT    3.76    3.76
    0/0       NCS1002-K9        1.2   CDSP_PORT_26         CURRENT    3.76    3.76
    0/0       NCS1002-K9        1.2   CDSP_PORT_27         CURRENT    3.76    3.76
    0/0       NCS1002-K9              CFP2_PORT_05         NOT READY
    0/0       NCS1002-K9        2.1   CFP2_PORT_06         CURRENT    5.23    5.23
    0/0       NCS1002-K9              CFP2_PORT_12         NOT READY
    0/0       NCS1002-K9        2.1   CFP2_PORT_13         CURRENT    5.23    5.23
    0/0       NCS1002-K9              CFP2_PORT_19         NOT READY
    0/0       NCS1002-K9              CFP2_PORT_20         NOT READY
    0/0       NCS1002-K9              CFP2_PORT_26         NOT READY
    0/0       NCS1002-K9        2.1   CFP2_PORT_27         CURRENT    5.23    5.23
    0/0       NCS1002-K9        0.1   CTRL_BKP_LOW     B   CURRENT            2.23
    0/0       NCS1002-K9        0.1   CTRL_BKP_UP      B   CURRENT            2.23
    0/0       NCS1002-K9        0.1   CTRL_FPGA_LOW        CURRENT    2.23    2.23
    0/0       NCS1002-K9        0.1   CTRL_FPGA_UP         CURRENT    2.23    2.23
    0/RP0     NCS1K-CNTLR       0.1   BIOS_Backup      BS  RLOAD REQ         13.70
    0/RP0     NCS1K-CNTLR       0.1   BIOS_Primary      S  RLOAD REQ 13.40   13.70
    0/RP0     NCS1K-CNTLR       0.1   Daisy_Duke_BKP   BS  CURRENT            0.15
    0/RP0     NCS1K-CNTLR       0.1   Daisy_Duke_FPGA   S  RLOAD REQ  0.15    0.17
    0/PM0     NCS1K-2KW-AC      0.0   PO-PriMCU            CURRENT
    0/PM1     NCS1K-2KW-AC      0.0   PO-PriMCU            CURRENT    4.00    4.00

    Platform: ASR9K-X64
    RP/0/RSP0/CPU0:vkg3#show hw-module fpd
                                                                       FPD Versions
                                                                    ===============
    Location  Card type         HWver FPD device       ATR Status   Run    Programd
    -------------------------------------------------------------------------------
    0/0       A99-8X100GE-SE    1.0   CBC                  CURRENT   38.23   38.23
    0/0       A99-8X100GE-SE    1.0   Dalla                CURRENT    1.09    1.09
    0/0       A99-8X100GE-SE    1.0   IPU-FPGA             CURRENT    1.91    1.91
    0/0       A99-8X100GE-SE    1.0   IPU-FSBL             CURRENT    1.96    1.96
    0/0       A99-8X100GE-SE    1.0   IPU-Linux            CURRENT    1.96    1.96
    0/0       A99-8X100GE-SE    1.0   Meldun-0             CURRENT    1.07    1.07
    0/0       A99-8X100GE-SE    1.0   Meldun-1             CURRENT    1.07    1.07
    0/0       A99-8X100GE-SE    1.0   Primary-BIOS         CURRENT    8.43    8.43
    0/RP0     A99-RP2-SE        1.0   Alpha-FPGA           CURRENT    0.16    0.16
    0/RP0     A99-RP2-SE        1.0   CBC-0                CURRENT   35.12   35.12
    0/RP0     A99-RP2-SE        1.0   CBC-1                CURRENT   35.12   35.12
    0/RP0     A99-RP2-SE        1.0   Cha-FPGA             CURRENT    0.05    0.05
    0/RP0     A99-RP2-SE        1.0   IPU-FPGA             CURRENT    0.52    0.52
    0/RP0     A99-RP2-SE        1.0   IPU-FSBL             CURRENT    1.96    1.96
    0/RP0     A99-RP2-SE        1.0   IPU-Linux            CURRENT    1.96    1.96
    0/RP0     A99-RP2-SE        1.0   Omega-FPGA           CURRENT    0.15    0.15
    0/RP0     A99-RP2-SE        1.0   Optimus-FPGA         CURRENT    0.12    0.12
    0/RP0     A99-RP2-SE        1.0   Primary-BIOS         CURRENT   14.28   14.28
    0/RP1     A99-RP2-SE        1.0   Alpha-FPGA           CURRENT    0.16    0.16
    0/RP1     A99-RP2-SE        1.0   CBC-0                CURRENT   35.12   35.12
    0/RP1     A99-RP2-SE        1.0   CBC-1                CURRENT   35.12   35.12
    0/RP1     A99-RP2-SE        1.0   Cha-FPGA             CURRENT    0.05    0.05
    0/RP1     A99-RP2-SE        1.0   IPU-FPGA             CURRENT    0.52    0.52
    0/RP1     A99-RP2-SE        1.0   IPU-FSBL             CURRENT    1.96    1.96
    0/RP1     A99-RP2-SE        1.0   IPU-Linux            CURRENT    1.96    1.96
    0/RP1     A99-RP2-SE        1.0   Omega-FPGA           CURRENT    0.15    0.15
    0/RP1     A99-RP2-SE        1.0   Optimus-FPGA         CURRENT    0.12    0.12
    0/RP1     A99-RP2-SE        1.0   Primary-BIOS         CURRENT   14.28   14.28
    0/FC0     A99-SFC2          1.0   CBC                  CURRENT   37.20   37.20
    0/FC0     A99-SFC2          1.0   IPU-FPGA             CURRENT    0.33    0.33
    0/FC0     A99-SFC2          1.0   IPU-FSBL             CURRENT    1.79    1.79
    0/FC0     A99-SFC2          1.0   IPU-Linux            CURRENT    1.79    1.79
    0/FC1     A99-SFC2          1.0   CBC                  CURRENT   37.20   37.20
    0/FC1     A99-SFC2          1.0   IPU-FPGA             CURRENT    0.33    0.33
    0/FC1     A99-SFC2          1.0   IPU-FSBL             CURRENT    1.79    1.79
    0/FC1     A99-SFC2          1.0   IPU-Linux            CURRENT    1.79    1.79
    0/FC2     A99-SFC2          1.0   CBC                  CURRENT   37.20   37.20
    0/FC2     A99-SFC2          1.0   IPU-FPGA             CURRENT    0.33    0.33
    0/FC2     A99-SFC2          1.0   IPU-FSBL             CURRENT    1.79    1.79
    0/FC2     A99-SFC2          1.0   IPU-Linux            CURRENT    1.79    1.79
    0/FC3     A99-SFC2          1.0   CBC                  CURRENT   37.20   37.20
    0/FC3     A99-SFC2          1.0   IPU-FPGA             CURRENT    0.33    0.33
    0/FC3     A99-SFC2          1.0   IPU-FSBL             CURRENT    1.79    1.79
    0/FC3     A99-SFC2          1.0   IPU-Linux            CURRENT    1.79    1.79
    0/FC4     A99-SFC2          1.0   CBC                  CURRENT   37.20   37.20
    0/FC4     A99-SFC2          1.0   IPU-FPGA             CURRENT    0.33    0.33
    0/FC4     A99-SFC2          1.0   IPU-FSBL             CURRENT    1.79    1.79
    0/FC4     A99-SFC2          1.0   IPU-Linux            CURRENT    1.79    1.79
    0/FT0     ASR-9912-FAN      1.0   CBC                  CURRENT   31.05   31.05
    0/FT1     ASR-9912-FAN      1.0   CBC                  CURRENT   31.05   31.05
    0/PT1     PWR-3KW-AC-V2     2.0   PM0-DT-PriMCU        UPGD SKIP  6.01    6.01
    0/PT1     PWR-3KW-AC-V2     2.0   PM0-DT-Sec54vMCU     UPGD SKIP  6.01    6.01
    0/PT1     PWR-3KW-AC-V2     2.0   PM0-DT-Sec5vMCU      UPGD SKIP  6.03    6.03
    0/PT2     PWR-3KW-AC-V2     2.0   PM0-DT-PriMCU        UPGD SKIP  6.01    6.01
    0/PT2     PWR-3KW-AC-V2     2.0   PM0-DT-Sec54vMCU     UPGD SKIP  6.01    6.01
    0/PT2     PWR-3KW-AC-V2     2.0   PM0-DT-Sec5vMCU      UPGD SKIP  6.03    6.03
    0/BPID0   ASR-9912-AC       1.0   CBC                  CURRENT    7.105   7.105
    """

    reload_ready = True
    sl = ['Card', 'FPD', 'ATR', 'Status', 'Running']
    dl = {}

    output = ctx.send("show hw-module fpd", timeout=600)
    lines = output.split('\n')
    lines = [x for x in lines if x]
    for line in lines:
        line = line.strip()

        if line[0:8] == 'Location':
            for s in sl:
                n = line.find(s)
                if n != -1:
                    if s == 'Card':
                        n -= 1
                    dl[str(s)] = n
                else:
                    ctx.error("unrecognized show hw-module fpd header {}".format(line))
                    return False

        if line[0].isdigit():
            status = line[dl['Status']:dl['Running']].strip()
            location = line[0:dl['Card']].strip()
            type = line[dl['FPD']:dl['ATR']].strip()
            if 'N/A' in status:
                continue
            # take care of NSR1K CFP2 exception
            if 'NOT READY' in status:
                version = line[dl['Running']:].strip()
                if not version:
                    continue
            # take care of asr9k-x64 exception
            if 'UPGD SKIP' in status:
                continue
            if fpd_location == 'all' and fpd_type == 'all':
                if 'CURRENT' not in status and 'RLOAD REQ' not in status:
                    reload_ready = False
                    break
            elif fpd_location and fpd_type == 'all':
                if location == fpd_location:
                    if 'CURRENT' not in status and 'RLOAD REQ' not in status:
                        reload_ready = False
                        break
                else:
                    continue
            else:
                if location == fpd_location and type == fpd_type:
                    if 'CURRENT' not in status and 'RLOAD REQ' not in status:
                        reload_ready = False
                        break
                else:
                    continue

    return reload_ready


def fpd_check_status(ctx, fpd_location, fpd_type):
    """
    :param ctx
    :return: True or False

    Platform: NCS5500
    RP/0/RP0/CPU0:xrg-ncs-07#show hw-module fpd
    Wed Jun 28 17:56:16.811 UTC
                                                                   FPD Versions
                                                                   =================
    Location   Card type        HWver FPD device       ATR Status   Running Programd
    ------------------------------------------------------------------------------
    0/RP0     NCS-5501          1.0   MB-MIFPGA            CURRENT    1.01    1.01
    0/RP0     NCS-5501          1.0   Bootloader           CURRENT    1.13    1.13
    0/RP0     NCS-5501          1.0   CPU-IOFPGA           CURRENT    1.14    1.14
    0/RP0     NCS-5501          1.0   MB-IOFPGA            CURRENT    1.04    1.04

    Platform: ASR9K-X64
    RP/0/RSP0/CPU0:vkg3#show hw-module fpd
    Wed Jun 28 11:05:35.914 UTC
                                                                   FPD Versions
                                                                   =================
    Location   Card type        HWver FPD device       ATR Status   Running Programd
    ------------------------------------------------------------------------------
    0/RSP0    A9K-RSP880-SE     1.0   Alpha-FPGA           CURRENT    0.16    0.16
    0/RSP0    A9K-RSP880-SE     1.0   CBC                  CURRENT   34.38   34.38
    0/RSP0    A9K-RSP880-SE     1.0   Cha-FPGA             CURRENT    0.07    0.07
    0/RSP0    A9K-RSP880-SE     1.0   IPU-FPGA             CURRENT    0.56    0.56
    0/RSP0    A9K-RSP880-SE     1.0   IPU-FSBL             CURRENT    1.101   1.101
    0/RSP0    A9K-RSP880-SE     1.0   IPU-Linux            CURRENT    1.101   1.101
    0/RSP0    A9K-RSP880-SE     1.0   Omega-FPGA           CURRENT    0.16    0.16
    0/RSP0    A9K-RSP880-SE     1.0   Optimus-FPGA         CURRENT    0.12    0.12
    0/RSP0    A9K-RSP880-SE     1.0   Primary-BIOS         CURRENT   10.58   10.58
    0/RSP1    A9K-RSP880-SE     1.0   Alpha-FPGA           CURRENT    0.16    0.16
    0/RSP1    A9K-RSP880-SE     1.0   CBC                  CURRENT   34.38   34.38
    0/RSP1    A9K-RSP880-SE     1.0   Cha-FPGA             CURRENT    0.07    0.07
    0/RSP1    A9K-RSP880-SE     1.0   IPU-FPGA             CURRENT    0.56    0.56
    0/RSP1    A9K-RSP880-SE     1.0   IPU-FSBL             CURRENT    1.101   1.101
    0/RSP1    A9K-RSP880-SE     1.0   IPU-Linux            CURRENT    1.101   1.101
    0/RSP1    A9K-RSP880-SE     1.0   Omega-FPGA           CURRENT    0.16    0.16
    0/RSP1    A9K-RSP880-SE     1.0   Optimus-FPGA         CURRENT    0.12    0.12
    0/RSP1    A9K-RSP880-SE     1.0   Primary-BIOS         CURRENT   10.58   10.58
    0/FT0     ASR-9904-FAN      1.0   CBC                  CURRENT   31.05   31.05
    0/0       A9K-8X100GE-SE    1.0   CBC                  CURRENT   38.23   38.23
    0/0       A9K-8X100GE-SE    1.0   Dalla                CURRENT    1.09    1.09
    0/0       A9K-8X100GE-SE    1.0   IPU-FPGA             CURRENT    1.93    1.93
    0/0       A9K-8X100GE-SE    1.0   IPU-FSBL             CURRENT    1.100   1.100
    0/0       A9K-8X100GE-SE    1.0   IPU-Linux            CURRENT    1.100   1.100
    0/0       A9K-8X100GE-SE    1.0   Meldun-0             CURRENT    1.07    1.07
    0/0       A9K-8X100GE-SE    1.0   Meldun-1             CURRENT    1.07    1.07
    0/0       A9K-8X100GE-SE    1.0   Primary-BIOS         CURRENT    8.43    8.43
    0/BPID0   ASR-9904-AC       1.0   CBC                  CURRENT    7.105   7.105
    0/PT0     PWR-3KW-AC-V2     3.0   PM0-EM-PriMCU        N/A        3.06    3.06
    0/PT0     PWR-3KW-AC-V2     3.0   PM0-EM-Sec54vMCU     CURRENT    3.12    3.12
    0/PT0     PWR-3KW-AC-V2     3.0   PM0-EM-Sec5vMCU      CURRENT    3.18    3.18
    0/PT0     PWR-3KW-AC-V2     3.0   PM1-EM-PriMCU        N/A        3.06    3.06
    0/PT0     PWR-3KW-AC-V2     3.0   PM1-EM-Sec54vMCU     CURRENT    3.12    3.12
    0/PT0     PWR-3KW-AC-V2     3.0   PM1-EM-Sec5vMCU      CURRENT    3.18    3.18
    0/PT0     PWR-3KW-AC-V2     3.0   PM2-EM-PriMCU        N/A        3.06    3.06
    0/PT0     PWR-3KW-AC-V2     3.0   PM2-EM-Sec54vMCU     CURRENT    3.12    3.12
    0/PT0     PWR-3KW-AC-V2     3.0   PM2-EM-Sec5vMCU      CURRENT    3.18    3.18
    0/PT0     PWR-3KW-AC-V2     3.0   PM3-EM-PriMCU        N/A        3.06    3.06
    0/PT0     PWR-3KW-AC-V2     3.0   PM3-EM-Sec54vMCU     CURRENT    3.12    3.12
    0/PT0     PWR-3KW-AC-V2     3.0   PM3-EM-Sec5vMCU      CURRENT    3.18    3.18
    """

    current_status = True
    sl = ['Card', 'FPD', 'ATR', 'Status', 'Running']
    dl = {}

    output = ctx.send("show hw-module fpd", timeout=600)
    lines = output.split('\n')
    lines = [x for x in lines if x]
    for line in lines:
        line = line.strip()

        if line[0:8] == 'Location':
            for s in sl:
                n = line.find(s)
                if n != -1:
                    if s == 'Card':
                        n -= 1
                    dl[str(s)] = n
                else:
                    ctx.error("unrecognized show hw-module fpd header {}".format(line))
                    return False

        if line[0].isdigit():
            status = line[dl['Status']:dl['Running']].strip()
            location = line[0:dl['Card']].strip()
            type = line[dl['FPD']:dl['ATR']].strip()
            if 'N/A' in status:
                ctx.warning('FPD Status: {}'.format(line))
                continue
            # take care of NSR1K CFP2 exception
            if 'NOT READY' in status:
                version = line[dl['Running']:].strip()
                if not version:
                    continue
            # take care of asr9k-x64 exception
            if 'UPGD SKIP' in status:
                continue
            if fpd_location == 'all' and fpd_type == 'all':
                if 'CURRENT' not in status:
                    ctx.warning('FPD Status: {}'.format(line))
                    current_status = False
                    break
            elif fpd_location and not fpd_type:
                if location == fpd_location:
                    if 'CURRENT' not in status:
                        current_status = False
                        break
                else:
                    continue
            elif not fpd_location and fpd_type:
                if type == fpd_type:
                    if 'CURRENT' not in status:
                        current_status = False
                        break
                else:
                    continue
            else:
                if location == fpd_location and type == fpd_type:
                    if 'CURRENT' not in status:
                        current_status = False
                        break
                else:
                    continue

    return current_status


def hw_fpd_upgd(ctx, location, type):
    """
    :param ctx
    :return: True or False

    Platform: NCS5500
    RP/0/RP0/CPU0:freta1.55#upgrade hw-module location all fpd all
    Wed May 24 09:14:00.817 CEST
    upgrade command issued (use "show hw-module fpd" to check upgrade status)
    """

    cmd = 'upgrade hw-module location ' + location + ' fpd ' + type
    output = ctx.send(cmd)

    if 'upgrade command issued' in output:
        return True
    else:
        return False


def hw_fpd_reload(ctx, location):
    """
    :param ctx
    :return: True or False

    Platform: NCS5500
    RP/0/RP0/CPU0:xrg-ncs-07#admin hw-module location all reload
    Tue Jun 27 00:47:15.279 UTC

    lab connected from 127.0.0.1 using console on xr-vm_node0_RP0_CPU0
    sysadmin-vm:0_RP0# terminal length 0
    Tue Jun  27 00:47:16.337 UTC
    sysadmin-vm:0_RP0# hw-module location all reload
    Tue Jun  27 00:47:16.379 UTC
    Reload hardware module ? [no,yes] yes
    yes
    result Card graceful reload request on all succeeded.
    """
    global plugin_ctx
    plugin_ctx = ctx

    cmd = 'admin hw-module location ' + location + ' reload'

    # Seeing this message without the reboot prompt indicates a non-reload situation
    RELOAD_MODULE = re.compile("Reload hardware module \? \[no,yes\]")
    HOST_PROMPT = re.compile(ctx.prompt)

    events = [RELOAD_MODULE, HOST_PROMPT]
    transitions = [
        (RELOAD_MODULE, [0], 1, send_yes, 60),
        (HOST_PROMPT, [1], -1, None, 120)
    ]

    if not ctx.run_fsm("hw-module reload", cmd, events, transitions, timeout=120):
        ctx.warning("Failed: {}".format(cmd))
        return False

    return True


def wait_for_fpd_upgd(ctx, location, type):
    """
    :param ctx
    :return: True or False
    """
    begin = time.time()

    ctx.info("FPD upgrade in progress")

    timeout = 7200
    poll_time = 30
    time_waited = 0

    ctx.info("Waiting for FPD upgrade to complete")
    ctx.post_status("Waiting for FPD upgrade to complete")

    while 1:
        # Wait till all nodes are in CURRENT or RLOAD REQ
        time.sleep(poll_time)

        if fpd_needs_reload(ctx, location, type):
            ctx.info("Location = {}, FPD device = {} in desired state.".format(location, type))
            elapsed = time.time() - begin
            ctx.info("Overall fpd upgrade time: {} minute(s) {:.0f} second(s)".format(elapsed // 60, elapsed % 60))
            return True

        time_waited += poll_time
        if time_waited >= timeout:
            break

    # Some nodes did not come to CURRENT or RLOAD REQ
    ctx.error("FPD Upgrade Timeout: some nodes are not in CURRENT or RLOAD REQ")
    # this will never be executed
    return False
