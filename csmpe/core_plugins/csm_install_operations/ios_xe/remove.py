# =============================================================================
#
# Copyright (c) 2016, Cisco Systems
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

from csmpe.plugins import CSMPlugin
from csmpe.core_plugins.csm_get_inventory.ios_xe.plugin import get_package, get_inventory
from utils import remove_exist_image
from condoor.exceptions import CommandSyntaxError


class Plugin(CSMPlugin):
    """This plugin removes inactive packages from the device."""
    name = "Install Remove Plugin"
    platforms = {'ASR900', 'ASR1K'}
    phases = {'Remove'}
    os = {'XE'}

    def run(self):
        packages_to_remove = self.ctx.software_packages
        if packages_to_remove is None:
            self.ctx.error("No package list provided")
            return

        self.ctx.info("Remove Package(s) Pending")
        self.ctx.post_status("Remove Package(s) Pending")

        try:
            self.ctx.send('dir harddisk:')
            disk = 'harddisk:'
        except CommandSyntaxError:
            disk = 'bootflash:'

        for pkg in packages_to_remove:
            self.ctx.info("Delete package {}{}".format(disk, pkg))

            package = disk + pkg
            output = remove_exist_image(self.ctx, package)

            if not output:
                self.ctx.info("{}{} Removal Failed".format(disk, pkg))
                break

            package = 'stby-' + disk + pkg
            cmd = 'dir ' + package
            try:
                output = self.ctx.send(cmd)
                if 'No such file or directory' in output:
                    continue
                output = remove_exist_image(self.ctx, package)
                if not output:
                    self.ctx.warning("stby-{}{} Removal Failed".format(disk, pkg))
                    break
            except CommandSyntaxError:
                continue
        else:
            self.ctx.info("Package(s) Removed Successfully")
            # Refresh package and inventory information
            get_package(self.ctx)
            get_inventory(self.ctx)
            return

        self.ctx.error("Package(s) Removal Failed")
        return
