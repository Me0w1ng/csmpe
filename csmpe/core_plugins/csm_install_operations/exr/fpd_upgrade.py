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
from fpd_upgd_lib import fpd_is_current, fpd_needs_upgd, fpd_check_status, \
    hw_fpd_upgd, hw_fpd_reload, wait_for_fpd_upgd
from install import wait_for_reload
from csmpe.core_plugins.csm_get_inventory.exr.plugin import get_package, get_inventory
from csmpe.core_plugins.csm_install_operations.utils import update_device_info_udi


class Plugin(CSMPlugin):
    """This plugin removes inactive packages from the device."""
    name = "Install FPD Upgrade Plugin"
    platforms = {'ASR9K', 'NCS1K', 'NCS1001', 'NCS4K', 'NCS5K', 'NCS540',
                 'NCS5500', 'NCS6K', 'IOSXRv-9K', 'IOSXRv-X64'}
    phases = {'FPD-Upgrade'}
    os = {'eXR'}

    def run(self):

        self.ctx.info("FPD-Upgrade Pending")
        self.ctx.post_status("FPD-Upgrade Pending")

        fpd_location = self.ctx.load_job_data('fpd_location')[0]
        fpd_type = self.ctx.load_job_data('fpd_type')[0]

        self.ctx.info("fpd_location = {}".format(fpd_location))
        self.ctx.info("fpd_type = {}".format(fpd_type))

        # case 1: both fpd_location and fpd_type are none.
        if not fpd_location and not fpd_type:
            fpd_location = 'all'
            fpd_type = 'all'
        # case 2: only fpd_location is specified
        # case 3: only fpd_type is specified
        # case 4: both fpd_location and fpd_type are specified

        if fpd_is_current(self.ctx, fpd_location, fpd_type):
            self.ctx.info("All FPD devices are CURRENT. Nothing to be upgraded.")
            return True

        upgd_locations = fpd_needs_upgd(self.ctx, fpd_location, fpd_type)
        self.ctx.info("locations to be upgraded = {}".format(upgd_locations))
        if upgd_locations:
            if fpd_location == 'all' and fpd_type == 'all':
                if not hw_fpd_upgd(self.ctx, fpd_location, fpd_type):
                    self.ctx.error("Fail to issue {}".format('upgrade hw-module location all fpd all'))
                    return
                wait_for_fpd_upgd(self.ctx, fpd_location, fpd_type)
            elif fpd_location and not fpd_type:
                type = 'all'
                if not hw_fpd_upgd(self.ctx, fpd_location, type):
                    cmd = 'upgrade hw-module location ' + fpd_location + ' fpd ' + type
                    self.ctx.error("Fail to issue {}".format(cmd))
                    return
                wait_for_fpd_upgd(self.ctx, fpd_location, type)
            elif not fpd_location and fpd_type:
                for location in upgd_locations:
                    if not hw_fpd_upgd(self.ctx, location, fpd_type):
                        cmd = 'upgrade hw-module location ' + location + ' fpd ' + fpd_type
                        self.ctx.error("Fail to issue {}".format(cmd))
                        return
                    wait_for_fpd_upgd(self.ctx, location, fpd_type)
                    time.sleep(30)  # CLI may not work if issuing too quickly
            else:
                if not hw_fpd_upgd(self.ctx, fpd_location, fpd_type):
                    cmd = 'upgrade hw-module location ' + fpd_location + ' fpd ' + fpd_type
                    self.ctx.error("Fail to issue {}".format(cmd))
                    return
                wait_for_fpd_upgd(self.ctx, fpd_location, fpd_type)

        if not fpd_location and fpd_type:
            # check if RP0 / RP1 is to be reloaded
            location = None
            if upgd_locations:
                for location in upgd_locations:
                    if 'RP' in location or 'RSP' in location:
                        location = 'all'
                        break

            if location == 'all':
                if not hw_fpd_reload(self.ctx, location):
                    cmd = 'admin hw-module location ' + location + ' reload'
                    self.ctx.error("Fail to issue {}".format(cmd))
                    return
            else:
                if upgd_locations:
                    for location in upgd_locations:
                        if not hw_fpd_reload(self.ctx, location):
                            cmd = 'admin hw-module location ' + location + ' reload'
                            self.ctx.error("Fail to issue {}".format(cmd))
                            return
                        time.sleep(10)
        else:
            if not hw_fpd_reload(self.ctx, fpd_location):
                cmd = 'admin hw-module location ' + fpd_location + ' reload'
                self.ctx.error("Fail to issue {}".format(cmd))
                return

        success = wait_for_reload(self.ctx)
        if not success:
            self.ctx.error("Reload or boot failure")
            return

        self.ctx.info("Refreshing package and inventory information")
        self.ctx.post_status("Refreshing package and inventory information")
        # Refresh package and inventory information
        get_package(self.ctx)
        get_inventory(self.ctx)

        update_device_info_udi(self.ctx)

        if fpd_check_status(self.ctx, fpd_location, fpd_type):
            self.ctx.info("FPD-Upgrade Successfully")
            return True
        else:
            self.ctx.error("FPD-Upgrade Completed but the status of one or more nodes is not Current or N/A")
            return False
