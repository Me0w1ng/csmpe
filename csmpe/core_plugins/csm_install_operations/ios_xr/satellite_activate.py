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

import subprocess
from csmpe.plugins import CSMPlugin
from install import install_satellite_activate
from csmpe.core_plugins.csm_get_inventory.ios_xr.plugin import get_satellite


class Plugin(CSMPlugin):
    """This plugin removes all inactive packages from the device."""
    name = "Satellite-Activate Plugin"
    platforms = {'ASR9K'}
    phases = {'Satellite-Activate'}
    os = {'XR'}

    def run(self):

        """
        Produces a list of satellite ID that needs transfer

        RP/0/RP0/CPU0:AGN_PE_11_9k#install nv satellite 160,163 transfer
        """
        satellite_ids = self.ctx.load_job_data('selected_satellite_ids')
        pre_check_script = self.ctx.load_job_data('pre_check_script')[0]
        post_check_script = self.ctx.load_job_data('post_check_script')[0]

        if pre_check_script:
            pre_check_script = str(pre_check_script)
        if post_check_script:
            post_check_script = str(post_check_script)

        if pre_check_script:
            self.ctx.info("Satellite-Activate pre_check_script {} Pending".format(pre_check_script))
            try:
                output = subprocess.check_output(pre_check_script, shell=True)
                self.ctx.info("pre_check_script {} output:".format(pre_check_script))
                self.ctx.info("{}".format(output.decode('UTF-8').rstrip()))
            except subprocess.CalledProcessError as e:
                self.ctx.warning('Satellite-Activate pre_check_script {} error:'.format(pre_check_script))
                self.ctx.error(e.output)
            self.ctx.info("Satellite-Activate pre_check_script {} completed".format(pre_check_script))

        # ctype = type(satellite_ids[0])
        # self.ctx.info("ctype = {}".format(ctype))
        self.ctx.info("satellite_ids = {}".format(satellite_ids[0]))

        self.ctx.info("Satellite-Activate Pending")
        self.ctx.post_status("Satellite-Activate Pending")

        result = install_satellite_activate(self.ctx, satellite_ids[0])

        self.ctx.info("Refresh satellite inventory information")
        self.ctx.post_status("Refresh satellite inventory information")

        # Refresh satellite inventory information
        get_satellite(self.ctx)

        if post_check_script:
            self.ctx.info("Satellite-Activate post_check_script {} Pending".format(post_check_script))
            try:
                output = subprocess.check_output(post_check_script, shell=True)
                self.ctx.info("post_check_script {} output:".format(post_check_script))
                self.ctx.info("{}".format(output.decode('UTF-8').rstrip()))
            except subprocess.CalledProcessError as e:
                self.ctx.warning('Satellite-Activate post_check_script {} error:'.format(post_check_script))
                self.ctx.error(e.output)
            self.ctx.info("Satellite-Activate post_check_script {} completed".format(post_check_script))

        if result:
            self.ctx.info("Satellite-Activate completed")
        else:
            self.ctx.error("Satellite-Activate failed to complete.")
