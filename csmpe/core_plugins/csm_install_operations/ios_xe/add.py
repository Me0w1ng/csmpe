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

import re
from csmpe.plugins import CSMPlugin
from utils import install_add_remove
from csmpe.core_plugins.csm_get_inventory.ios_xe.plugin import get_package, get_inventory
from condoor.exceptions import CommandSyntaxError


class Plugin(CSMPlugin):
    """This plugin adds packages from repository to the device."""
    name = "Install Add Plugin"
    platforms = {'ASR900', 'ASR1K'}
    phases = {'Add'}
    os = {'XE'}

    def run(self):
        server_repository_url = self.ctx.server_repository_url

        if server_repository_url is None:
            self.ctx.error("No repository provided")
            return

        packages = self.ctx.software_packages
        if packages is None:
            self.ctx.error("No package list provided")
            return

        self.ctx.info("Add Package(s) Pending")
        self.ctx.post_status("Add Package(s) Pending")

        try:
            self.ctx.send('dir harddisk:')
            disk = 'harddisk:'
        except CommandSyntaxError:
            disk = 'bootflash:'
        stby_disk = 'stby-' + disk

        for package in packages:

            output = self.ctx.send('dir ' + disk + package)
            m = re.search('No such file', output)

            if not m:
                self.ctx.info("No action: {} exists in {}".format(package, disk))
                continue

            cmd = "copy {}/{} {}".format(server_repository_url, package, disk)
            install_add_remove(self.ctx, cmd)

            cmd = "dir " + stby_disk
            try:
                self.ctx.send(cmd)
                cmd = "copy {}{} {}{}".format(disk, package, stby_disk, package)
                install_add_remove(self.ctx, cmd)
            except CommandSyntaxError:
                continue

        self.ctx.info("Package(s) Added Successfully")

        # Refresh package and inventory information
        get_package(self.ctx)
        get_inventory(self.ctx)
