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
from fpd_upgd_lib import fpd_is_current, fpd_needs_upgd, fpd_needs_reload, fpd_check_status, \
    hw_fpd_upgd, hw_fpd_reload, wait_for_fpd_upgd
from install import wait_for_reload
from csmpe.core_plugins.csm_get_inventory.exr.plugin import get_package, get_inventory
from csmpe.core_plugins.csm_install_operations.utils import update_device_info_udi


class Plugin(CSMPlugin):
    """This plugin removes inactive packages from the device."""
    name = "Install FPD Upgrade"
    platforms = {'ASR9K', 'NCS1K', 'NCS4K', 'NCS5K', 'NCS5500', 'NCS6K'}
    # NCS1K, NCS4K, NCS5K, NCS6K to be tested
    phases = {'FPD-Upgrade'}
    os = {'eXR'}

    def _run(self):

        self.ctx.info("FPD-Upgrade Pending")
        self.ctx.post_status("FPD-Upgrade Pending")

        if fpd_is_current(self.ctx):
            self.ctx.info("All FPD devices are CURRENT. Nothing to be upgraded.")
            return True

        if fpd_needs_upgd(self.ctx):
            if not hw_fpd_upgd(self.ctx):
                self.ctx.error("Fail to issue {}".format('upgrade hw-module location all fpd all'))
                return
            wait_for_fpd_upgd(self.ctx)

        if fpd_needs_reload(self.ctx):
            if not hw_fpd_reload(self.ctx):
                self.ctx.error("Fail to issue {}".format('admin hw-module location all reload'))
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

        if fpd_check_status(self.ctx):
            self.ctx.info("FPD-Upgrade Successfully")
            return True
        else:
            self.ctx.error("FPD-Upgrade Completed but the status of one or more nodes is not Current or N/A")
            return False
