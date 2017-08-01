# =============================================================================
# plugin
#
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
import string
from csmpe.plugins import CSMPlugin
from csmpe.core_plugins.csm_install_operations.ios_xe.utils import number_of_rsp


class Plugin(CSMPlugin):
    """
    This plugin checks if the node redundancy is sufficient to proceed the upgrade.
    """
    name = "Node Redundancy Check Plugin"
    platforms = {'ASR900', 'ASR1K'}
    phases = {'Pre-Upgrade', 'Post-Upgrade'}

    def run(self):
        """
        PAN-5201-ASR903#show redundancy states
        my state = 13 -ACTIVE
        peer state = 8  -STANDBY HOT
        Mode = Duplex
        Unit = Secondary
        Unit ID = 49

        Redundancy Mode (Operational) = sso
        Redundancy Mode (Configured)  = sso
        Redundancy State              = sso
        Maintenance Mode = Disabled
        Manual Swact = enabled
        Communications = Up

        client count = 107
        client_notification_TMR = 30000 milliseconds
        RF debug mask = 0x0
        """

        sub_platforms = ['ASR-903', 'ASR-907']
        rsp_count = 1

        if self.ctx._connection.platform not in sub_platforms:
            self.ctx.info("Node redundancy not supported by "
                          "{}".format(self.ctx._connection.platform))
            return

        rsp_count = number_of_rsp(self.ctx)
        if rsp_count != 2:
            self.ctx.info("Node redundancy not supported by "
                          " number of RSP: {}".format(rsp_count))
            return

        cmd = "show redundancy states"
        output = self.ctx.send(cmd)
        if not output:
            self.ctx.error("Show redundancy output is insufficient.")
            return

        sso_ready = 0

        lines = string.split(output, '\n')
        lines = [x for x in lines if x]

        for line in lines:
            m = re.search('my state = .* -(.*)', line)
            if m:
                state = m.group(1)
                if 'ACTIVE' in state:
                    sso_ready = sso_ready | 1
                    self.ctx.info('{}'.format(line.lstrip()))
                continue

            m = re.search('peer state = .* -(.*)', line)
            if m:
                state = m.group(1)
                if 'STANDBY HOT' in state:
                    sso_ready = sso_ready | 2
                    self.ctx.info('{}'.format(line.lstrip()))
                continue

            m = re.search('Redundancy Mode \(Operational\)\s+= (.*)', line)
            if m:
                state = m.group(1)
                if 'sso' in state:
                    sso_ready = sso_ready | 4
                    self.ctx.info('{}'.format(line.lstrip()))
                continue

            m = re.search('Redundancy Mode \(Configured\)\s+= (.*)', line)
            if m:
                state = m.group(1)
                if 'sso' in state:
                    sso_ready = sso_ready | 8
                    self.ctx.info('{}'.format(line.lstrip()))
                continue

            m = re.search('Redundancy State        \s+ = (.*)', line)
            if m:
                state = m.group(1)
                if 'sso' in state:
                    sso_ready = sso_ready | 16
                    self.ctx.info('{}'.format(line.lstrip()))
                continue

        self.ctx.info("sso_ready = {}".format(sso_ready))
        if sso_ready == 31:
            self.ctx.info("Router redundancy has reached SSO state.")
        else:
            self.ctx.warning("Router redundancy has not reached SSO state.")
