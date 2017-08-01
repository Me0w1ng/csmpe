# =============================================================================
# Copyright (c)  2016, Cisco Systems
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


def parse_show_platform(ctx, output):
    """
    :param ctx: PluginContext
    :param output: output from 'show platform'
    :return: dictionary of nodes

    ASR9K:
    RP/0/RSP0/CPU0:PE4#admin show platform
    Node            Type                      State            Config State
    -----------------------------------------------------------------------------
    0/RSP0/CPU0     A9K-RSP880-LT-SE(Active)  IOS XR RUN       PWR,NSHUT,MON
    0/RSP1/CPU0     A9K-RSP880-LT-SE(Standby) IOS XR RUN       PWR,NSHUT,MON
    0/FT0/SP        ASR-9006-FAN-V2           READY
    0/FT1/SP        ASR-9006-FAN-V2           READY
    0/0/CPU0        A9K-24X10GE-1G-SE         IOS XR RUN       PWR,NSHUT,MON
    0/PS0/M0/SP     A9K-3KW-AC                READY            PWR,NSHUT,MON
    0/PS0/M1/SP     A9K-3KW-AC                READY            PWR,NSHUT,MON
    0/PS0/M2/SP     A9K-3KW-AC                READY            PWR,NSHUT,MON

    XR12K:
    RP/0/7/CPU0:GSR-PE19#admin show platform
    Node		    Type		    PLIM		    State		    Config State
    -----------------------------------------------------------------------------
    0/0/CPU0        L3LC Eng 5      Jacket Card     IOS XR RUN      PWR,NSHUT,MON
    0/1/CPU0        L3LC Eng 5+     Jacket Card     IOS XR RUN      PWR,NSHUT,MON
    0/1/0           SPA             SPA-10X1GE-V2   READY           PWR,NSHUT
    0/1/1           SPA             SPA-1XCHOC48/DS READY           PWR,NSHUT
    0/3/CPU0        L3LC Eng 5+     Jacket Card     IOS XR RUN      PWR,NSHUT,MON
    0/3/0           SPA             SPA-10X1GE-V2   READY           PWR,NSHUT
    0/5/CPU0        L3LC Eng 3      OC12-ATM-4      IOS XR RUN      PWR,NSHUT,MON
    0/6/CPU0        L3LC Eng 5      Jacket Card     IOS XR RUN      PWR,NSHUT,MON
    0/17/CPU0       CSC_OC192(P)    N/A             PWD             PWR,NSHUT,MON
    0/18/CPU0       SFC_OC192       N/A             PWD             PWR,NSHUT,MON
    0/19/CPU0       SFC_OC192       N/A             PWD             PWR,NSHUT,MON

    CRS:
    Node          Type              PLIM               State           Config State
    ------------- ----------------- ------------------ --------------- ---------------
    0/0/CPU0      MSC-X             40-10GbE           IOS XR RUN      PWR,NSHUT,MON
    0/1/SP        MSC-B(SP)         N/A                IOS XR RUN      PWR,NSHUT,MON
    0/1/CPU0      MSC-B             Jacket Card        IOS XR RUN      PWR,NSHUT,MON
    0/1/1         MSC-B(SPA)        1x10GE             OK              PWR,NSHUT,MON
    0/1/2         MSC-B(SPA)        10X1GE             OK              PWR,NSHUT,MON
    0/2/CPU0      FP-X              4-100GbE           IOS XR RUN      PWR,NSHUT,MON
    0/3/CPU0      MSC-140G          N/A                UNPOWERED       NPWR,NSHUT,MON
    0/4/CPU0      FP-X              N/A                UNPOWERED       NPWR,NSHUT,MON
    0/7/CPU0      MSC-X             40-10GbE           IOS XR RUN      PWR,NSHUT,MON
    0/8/CPU0      MSC-140G          N/A                UNPOWERED       NPWR,NSHUT,MON
    0/14/CPU0     MSC-X             4-100GbE           IOS XR RUN      PWR,NSHUT,MON
    0/RP0/CPU0    RP(Active)        N/A                IOS XR RUN      PWR,NSHUT,MON
    0/RP1/CPU0    RP(Standby)       N/A                IOS XR RUN      PWR,NSHUT,MON

    """
    host = ctx.get_host
    inventory = {}

    # Use the tuple to record the begin and end positions of each column.  Unfortunately,
    # we cannot rely on the header line as it contains a mixed of space and tab characters.
    if host.family == 'ASR9K':
        dl = {'Node': (0, 16), 'Type': (16, 42), 'State': (42, 59), 'Config State': (59, 77)}
    elif host.family == 'CRS':
        dl = {'Node': (0, 14), 'Type': (14, 32), 'State': (51, 67), 'Config State': (67, 82)}
    elif host.family == 'XR12K':
        dl = {'Node': (0, 16), 'Type': (16, 32), 'State': (47, 64), 'Config State': (64, 79)}
    else:
        ctx.warning("Unsupported platform {}".format(host.family))
        return None

    lines = output.split('\n')
    lines = [x for x in lines if x]
    for line in lines:
        if line[0].isdigit():
            node = line[dl['Node'][0]:dl['Node'][1]].strip()
            if not re.search('CPU\d+$', node):
                continue

            node_type = line[dl['Type'][0]:dl['Type'][1]].strip()
            state = line[dl['State'][0]:dl['State'][1]].strip()
            config_state = line[dl['Config State'][0]:dl['Config State'][1]].strip()

            entry = {
                'type': node_type,
                'state': state,
                'config_state': config_state
            }
            inventory[node] = entry

    return inventory
