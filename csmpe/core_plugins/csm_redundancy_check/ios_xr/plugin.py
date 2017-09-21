# =============================================================================
# plugin
#
# Copyright (c)  2016, Cisco Systems
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

from csmpe.plugins import CSMPlugin


class Plugin(CSMPlugin):
    """
    This plugin checks if the node redundancy is sufficient to proceed the upgrade.
    """
    name = "Node Redundancy Check Plugin"
    platforms = {'ASR9K', 'XR12K', 'CRS'}
    phases = {'Pre-Upgrade', 'Pre-Activate'}

    def run(self):
        """
        RP/0/RP0/CPU0:CRS-X-Deploy2#admin show redundancy location all
        Tue May 17 21:00:15.863 UTC
        Redundancy information for node 0/RP0/CPU0:
        ==========================================
        Node 0/RP0/CPU0 is in ACTIVE role
        Partner node (0/RP1/CPU0) is in STANDBY role
        Standby node in 0/RP1/CPU0 is ready
        Standby node in 0/RP1/CPU0 is NSR-ready
        """
        cmd = "show redundancy location all"
        if self.ctx.os_type != "eXR":
            cmd = "admin " + cmd
        output = self.ctx.send(cmd)
        lines = output.split("\n", 50)
        if len(lines) < 6:
            self.ctx.error("Show redundancy output is insufficient.")

        for ln, line in enumerate(lines[:6]):
            if "is in STANDBY role" in line:
                if "is ready" in lines[ln + 1]:
                    break
                else:
                    self.ctx.error("Standby is not ready. Upgrade can not proceed.")

        self.ctx.info("Node redundancy level sufficient")
