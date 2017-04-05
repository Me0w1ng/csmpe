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

from package_lib import SoftwarePackage
from csmpe.plugins import CSMPlugin
from install import install_add_remove
from csmpe.core_plugins.csm_get_inventory.ios_xr.plugin import get_package, get_inventory


class Plugin(CSMPlugin):
    """This plugin removes inactive packages from the device."""
    name = "Install Remove Plugin"
    platforms = {'ASR9K', 'CRS'}
    phases = {'Remove'}
    os = {'XR'}

    def run(self):
        packages = self.ctx.software_packages
        if packages is None:
            self.ctx.error("No package list provided")
            return

        # If a wide card character is detected, like 'disk0:*6.0.2*', only the first element
        # in the list is considered valid.  An example CLI is 'admin install remove disk0:*6.0.2*'.
        if any('*' in package for package in packages):
            to_remove = packages[0]
        else:
            pkgs = SoftwarePackage.from_package_list(packages)

            installed_inact = SoftwarePackage.from_show_cmd(self.ctx.send("admin show install inactive summary"))
            packages_to_remove = pkgs & installed_inact

            if not packages_to_remove:
                self.ctx.warning("Packages already removed. Nothing to be removed")
                return

            to_remove = " ".join(map(str, packages_to_remove))

        cmd = 'admin install remove {} prompt-level none async'.format(to_remove)

        self.ctx.info("Remove Package(s) Pending")
        self.ctx.post_status("Remove Package(s) Pending")

        install_add_remove(self.ctx, cmd)

        self.ctx.info("Package(s) Removed Successfully")

        # Refresh package and inventory information
        get_package(self.ctx)
        get_inventory(self.ctx)
