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
import subprocess

from csmpe.plugins import CSMPlugin


class Plugin(CSMPlugin):
    """This plugin executes a command that provokes an external script in the filesystem."""
    name = "Script Executor"
    phases = {'Pre-Check', 'Post-Check'}

    data_from_csm = ["full_command"]

    def _run(self):
        connection = self.ctx.connection
        if connection:
            connection.disconnect()

        if not self.full_command:
            self.ctx.error("No command provided.")

        self.ctx.info("Executing script with command '{}'".format(" ".join(self.full_command)))

        try:
            command = subprocess.Popen(self.full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            output, error = command.communicate()
        except OSError as e:
            self.ctx.error("OSError executing {}: {}".format(self.full_command, e))

        if error:
            self.ctx.error("Error executing {}: {}".format(self.full_command, error))

        self.ctx.info("Script execution completed. Output:\n{}".format(output))
