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
    fpd_package_installed, fpd_check_status, hw_fpd_reload, active_rsp_location
from install import wait_for_reload
from csmpe.core_plugins.csm_get_inventory.exr.plugin import get_package, get_inventory
from csmpe.core_plugins.csm_install_operations.utils import update_device_info_udi


class Plugin(CSMPlugin):
    """This plugin removes inactive packages from the device."""
    name = "Install FPD Upgrade Plugin"
    platforms = {'ASR9K'}
    phases = {'FPD-Upgrade'}
    os = {'XR'}

    def _run(self):

        need_reload = False

        self.ctx.info("FPD-Upgrade Pending")
        self.ctx.post_status("FPD-Upgrade Pending")

        if not fpd_package_installed(self.ctx):
            self.ctx.error("No FPD package is active on device. "
                           "Please install and activate the FPD package on device first.")
            return False

        locations = fpd_locations(self.ctx)
        active_location = active_rsp_location(self.ctx)

        upgd_result = True
        begin = time.time()
        for location in locations:
            if fpd_needs_upgd(self.ctx, location):
                need_reload = True
                if not hw_fpd_upgd(self.ctx, location):
                    upgd_result = False

        if not need_reload:
            self.ctx.info("All FPD devices are current. Nothing to be upgraded.")
            return True

        elapsed = time.time() - begin
        self.ctx.info("Overall fpd upgrade time: {} minute(s) {:.0f} second(s)".format(elapsed // 60, elapsed % 60))

        self.ctx.info("Reloading the host")

        if not hw_fpd_reload(self.ctx):
            self.ctx.error("Encountered error when attempting to reload device.")
            return False

        self.ctx.info("Wait for the host reload to complete")
        success = wait_for_reload(self.ctx)
        if not success:
            self.ctx.error("Reload or boot failure")
            return False

        if fpd_needs_upgd(self.ctx, active_location):
            if not hw_fpd_upgd(self.ctx, active_location):
                upgd_result = False
            if not hw_fpd_reload(self.ctx, location=active_location):
                self.ctx.error("Encountered error when attempting to reload device.")
                return False
            success = wait_for_reload(self.ctx)
            if not success:
                self.ctx.error("Reload or boot failure")
                return False
        time.sleep(30)
        if fpd_needs_upgd(self.ctx, active_location):
            if not hw_fpd_upgd(self.ctx, active_location):
                upgd_result = False
            if not hw_fpd_reload(self.ctx, location=active_location):
                self.ctx.error("Encountered error when attempting to reload device.")
                return False
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

        if upgd_result and fpd_check_status(self.ctx, locations):
            self.ctx.info("FPD-Upgrade Successfully")
            return True
        else:
            self.ctx.error("FPD-Upgrade completed but the status of one or more nodes is not current")
            return False
