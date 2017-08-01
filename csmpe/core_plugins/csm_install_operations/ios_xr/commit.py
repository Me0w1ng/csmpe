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


import re

from csmpe.plugins import CSMPlugin
from install import watch_operation, log_install_errors
from csmpe.core_plugins.csm_get_inventory.ios_xr.plugin import get_package, get_inventory


class Plugin(CSMPlugin):
    """This plugin Activates packages on the device."""
    name = "Install Commit Plugin"
    platforms = {'ASR9K', 'XR12K', 'CRS'}
    phases = {'Commit'}
    os = {'XR'}

    def run(self):
        """
        It performs commit operation
        """

        failed_oper = r'Install operation (\d+) failed'
        completed_with_failure = 'Install operation (\d+) completed with failure'
        success_oper = r'Install operation (\d+) completed successfully'

        cmd = "admin install commit"
        output = self.ctx.send(cmd)
        result = re.search('Install operation (\d+) \'', output)
        if result:
            op_id = result.group(1)
            watch_operation(self.ctx, op_id)
        else:
            log_install_errors(self.ctx, output)
            self.ctx.error("Operation ID not found.")
            return

        cmd = "admin show install log {} detail".format(op_id)
        output = self.ctx.send(cmd)

        if re.search(failed_oper, output):
            log_install_errors(self.ctx, output)
            self.ctx.error("Install operation failed.")
            return

        if re.search(completed_with_failure, output):
            log_install_errors(self.ctx, output)
            self.ctx.info("Completed with failure but failure was after Point of No Return.")
        elif re.search(success_oper, output):
            self.ctx.info("Operation {} finished successfully.".format(op_id))

        # Refresh package and inventory information
        get_package(self.ctx)
        get_inventory(self.ctx)
