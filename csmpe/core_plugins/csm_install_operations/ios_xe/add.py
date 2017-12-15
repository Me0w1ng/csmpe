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
from utils import install_add_remove, install_add_ftp, install_add_scp
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

        self.ctx.pause_session_logging()
        try:
            self.ctx.send('dir harddisk:')
            disk = 'harddisk:'
        except CommandSyntaxError:
            disk = 'bootflash:'
        self.ctx.resume_session_logging()

        for package in packages:

            stby_disk = ''
            self.ctx.pause_session_logging()
            output = self.ctx.send('dir ' + disk + package)
            self.ctx.resume_session_logging()

            m = re.search('No such file', output)

            if not m:
                self.ctx.info("No action: {} exists in {}".format(package, disk))
                continue

            if server_repository_url.startswith("tftp"):
                cmd = "copy {}/{} {}".format(server_repository_url, package, disk)
                install_add_remove(self.ctx, cmd)
            elif server_repository_url.startswith("ftp"):
                install_add_ftp(self.ctx, package, disk)
            elif server_repository_url.startswith("scp"):
                install_add_scp(self.ctx, package, disk)
            else:
                self.ctx.error("Unsupported repository type {}".format(server_repository_url))

            cmd = "dir " + 'stby-' + disk
            self.ctx.pause_session_logging()
            try:
                self.ctx.send(cmd)
                stby_disk = 'stby-' + disk
            except CommandSyntaxError:
                continue
            self.ctx.resume_session_logging()

            if stby_disk:
                cmd = "copy {}{} {}{}".format(disk, package, stby_disk, package)
                install_add_remove(self.ctx, cmd)

        self.ctx.info("Package(s) Added Successfully")

        # Refresh package and inventory information
        get_package(self.ctx)
        get_inventory(self.ctx)
