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

from csmpe.plugins import CSMPlugin
from install import install_satellite_transfer
from csmpe.core_plugins.csm_get_inventory.ios_xr.plugin import get_satellite


class Plugin(CSMPlugin):
    """This plugin removes all inactive packages from the device."""
    name = "Satellite-Transfer Plugin"
    platforms = {'ASR9K'}
    phases = {'Satellite-Transfer'}
    os = {'XR'}

    def run(self):

        """
        Produces a list of satellite ID that needs transfer

        RP/0/RP0/CPU0:AGN_PE_11_9k#install nv satellite 160,163 transfer
        """
        satellite_ids = self.ctx.load_job_data('selected_satellite_ids')

        # ctype = type(satellite_ids[0])
        # self.ctx.info("ctype = {}".format(ctype))
        self.ctx.info("satellite_ids = {}".format(satellite_ids[0]))

        self.ctx.info("Satellite-Transfer Pending")
        self.ctx.post_status("Satellite-Transfer Pending")

        result = install_satellite_transfer(self.ctx, satellite_ids[0])

        self.ctx.info("Refresh satellite inventory information")
        self.ctx.post_status("Refresh satellite inventory information")

        # Refresh satellite inventory information
        get_satellite(self.ctx)

        if result:
            self.ctx.info("Satellite-Transfer completed")
        else:
            self.ctx.error("Satellite-Transfer failed to complete.")
