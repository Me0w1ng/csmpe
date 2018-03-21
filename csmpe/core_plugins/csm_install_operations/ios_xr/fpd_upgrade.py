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

import time

from csmpe.plugins import CSMPlugin
from fpd_upgd_lib import fpd_locations, fpd_needs_upgd, hw_fpd_upgd, \
    fpd_package_installed, fpd_check_status, hw_fpd_reload, cbc_pwr_only
from install import wait_for_reload
from csmpe.core_plugins.csm_get_inventory.exr.plugin import get_package, get_inventory
from csmpe.core_plugins.csm_install_operations.utils import update_device_info_udi


class Plugin(CSMPlugin):
    """This plugin removes inactive packages from the device."""
    name = "Install FPD Upgrade Plugin"
    platforms = {'ASR9K'}
    phases = {'FPD-Upgrade'}
    os = {'XR'}

    def run(self):

        need_reload = False

        # XR ddts CSCvb67386 workaround
        # if cbc only or power module only, then do not reload
        avoid_reload = False

        self.ctx.info("FPD-Upgrade Pending")
        self.ctx.post_status("FPD-Upgrade Pending")

        if not fpd_package_installed(self.ctx):
            self.ctx.error("No FPD package is active on device. "
                           "Please install and activate the FPD package on device first.")
            return False

        fpd_location = self.ctx.load_job_data('fpd_location')[0]
        fpd_type = self.ctx.load_job_data('fpd_type')[0]

        self.ctx.info("fpd_location = {}".format(fpd_location))
        self.ctx.info("fpd_type = {}".format(fpd_type))

        if not fpd_location:
            fpd_location = 'all'
        if not fpd_type:
            fpd_type = 'all'

        # case 1: both fpd_location and fpd_type are none.
        # case 2: only fpd_location is specified
        # case 3: only fpd_type is specified
        # case 4: both fpd_location and fpd_type are specified

        locations = fpd_locations(self.ctx)
        self.ctx.info("FPD Location to be upgraded = {}".format(locations))

        upgd_result = True
        begin = time.time()
        for location in locations:
            if location == fpd_location or fpd_location == 'all':
                if fpd_needs_upgd(self.ctx, location, fpd_type):
                    need_reload = True
                    if not hw_fpd_upgd(self.ctx, location, fpd_type):
                        upgd_result = False
            else:
                continue

        if not need_reload:
            self.ctx.info("All FPD devices are current. Nothing to be upgraded.")
            return True

        if 'cbc' in fpd_type or '/PS' in 'fpd_location':
            avoid_reload = True

        if fpd_location == 'all' and fpd_type == 'all':
            avoid_reload = cbc_pwr_only(self.ctx)

        if not avoid_reload:
            elapsed = time.time() - begin
            self.ctx.info("Overall fpd upgrade time: {} minute(s) {:.0f} second(s)".format(elapsed // 60, elapsed % 60))

            self.ctx.info("Reloading the host")

            if not hw_fpd_reload(self.ctx, fpd_location):
                self.ctx.warning("Encountered error when attempting to reload device.")

            self.ctx.info("Wait for the host reload to complete")
            success = wait_for_reload(self.ctx)
            if not success:
                self.ctx.error("Reload or boot failure")
                return False

        self.ctx.info("Refreshing package and inventory information")
        self.ctx.post_status("Refreshing package and inventory information")
        # Refresh package and inventory information
        get_package(self.ctx)
        get_inventory(self.ctx)

        update_device_info_udi(self.ctx)

        if upgd_result:
            for location in locations:
                if location == fpd_location or fpd_location == 'all':
                    if not fpd_check_status(self.ctx, location, fpd_type):
                        upgd_result = False
                else:
                    continue

        if upgd_result:
            self.ctx.info("FPD-Upgrade Successfully")
            return True
        else:
            self.ctx.error("FPD-Upgrade completed but the status of one or more nodes is not current")
            return False
