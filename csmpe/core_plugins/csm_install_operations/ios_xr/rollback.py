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
from install import install_activate_deactivate, parse_pkg_list, report_changed_pkg
from csmpe.core_plugins.csm_get_inventory.ios_xr.plugin import get_package, get_inventory
from csmpe.core_plugins.csm_install_operations.utils import update_device_info_udi


class Plugin(CSMPlugin):
    """This plugin rollback to the last committed installation point."""
    name = "Install Rollback Plugin"
    platforms = {'ASR9K', 'XR12K', 'CRS'}
    phases = {'Rollback'}
    os = {'XR'}

    def run(self):

        self.ctx.send("admin show install active summary")
        self.ctx.send("admin show install committed summary")

        cmd = 'admin install rollback to committed prompt-level none asynchronous'

        output = self.ctx.send("show install active summary")
        before = parse_pkg_list(output)

        self.ctx.info("Install rollback to the last committed installation point Pending")
        self.ctx.post_status("Install rollback to the last committed installation point Pending")

        install_activate_deactivate(self.ctx, cmd)

        self.ctx.info("Install rollback done")

        output = self.ctx.send("show install active summary")
        after = parse_pkg_list(output)

        pkg_list = report_changed_pkg(before, after)
        pkg_change_list = ','.join(pkg_list)

        self.ctx.save_job_data("package_change_list", pkg_change_list)
        self.ctx.info("package change list:")

        for pkg in pkg_list:
            self.ctx.info("\t{}".format(pkg))

        self.ctx.info("Refreshing package and inventory information")
        self.ctx.post_status("Refreshing package and inventory information")

        # Refresh package and inventory information
        get_package(self.ctx)
        get_inventory(self.ctx)

        update_device_info_udi(self.ctx)
