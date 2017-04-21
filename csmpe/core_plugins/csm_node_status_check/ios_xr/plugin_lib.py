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
    Node            Type                      State            Config State
    -----------------------------------------------------------------------------
    0/RSP0/CPU0     A9K-RSP440-SE(Active)     IOS XR RUN       PWR,NSHUT,MON
    0/FT0/SP        ASR-9006-FAN              READY
    0/1/CPU0        A9K-40GE-E                IOS XR RUN       PWR,NSHUT,MON
    0/2/CPU0        A9K-MOD80-SE              UNPOWERED        NPWR,NSHUT,MON
    0/3/CPU0        A9K-8T-L                  UNPOWERED        NPWR,NSHUT,MON
    0/PS0/M0/SP     A9K-3KW-AC                READY            PWR,NSHUT,MON
    0/PS0/M1/SP     A9K-3KW-AC                READY            PWR,NSHUT,MON

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
    if host.family == 'ASR9K':
        sl = ['Node', 'Type', 'State', 'Config State']
    elif host.family == 'CRS':
        sl = ['Node', 'Type', 'PLIM', 'State', 'Config State']
    else:
        ctx.warning("Unsupported platform {}".format(host.family))
        return None
    dl = {}

    lines = output.split('\n')
    lines = [x for x in lines if x]
    for line in lines:
        line = line.strip()

        if line[0:4] == 'Node':
            for s in sl:
                n = line.find(s)
                if n != -1:
                    dl[s] = n
                else:
                    ctx.warning("unrecognized show platform header {}".format(line))
                    return None
            continue

        if line[0].isdigit():
            node = line[:dl['Type']].strip()
            if not re.search('CPU\d+$', node):
                continue

            if host.family == 'ASR9K':
                node_type = line[dl['Type']:dl['State']].strip()
            else:   # CRS
                node_type = line[dl['Type']:dl['PLIM']].strip()

            state = line[dl['State']:dl['Config State']].strip()
            config_state = line[dl['Config State']:].strip()

            entry = {
                'type': node_type,
                'state': state,
                'config_state': config_state
            }
            inventory[node] = entry

    return inventory
