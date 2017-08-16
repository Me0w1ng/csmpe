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
import os

from csmpe.plugins import CSMPlugin
from csmpe.plugins import apply_data_config


@apply_data_config
class Plugin(CSMPlugin):
    """This plugin executes a command that invokes an external script in the filesystem."""
    name = "Script Executor"
    phases = {'Pre-Check', 'Post-Check'}

    need_connection = False

    data_config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'plugin_data_specs.yaml')

    def _run(self):

        full_command = self.ctx.plugin_data.get('full_command', None)

        if not full_command:
            self.ctx.error("No command provided.")

        self.ctx.info("Executing script with command '{}'".format(full_command))

        script_log = open(os.path.join(self.ctx.log_directory, 'script.log'), 'a', 0)

        script_log.write("Plugin: {}#{}\n".format(self.name, self.ctx.plugin_number))
        script_log.write("Command: {}\n".format(full_command))
        script_log.write("Output:\n")

        try:
            command = subprocess.Popen(full_command.split(" "), stdout=script_log, stderr=subprocess.STDOUT)

            output, error = command.communicate()
        except OSError as e:
            script_log.close()
            self.ctx.error("OSError executing {}: {}".format(full_command, e))

        if error:
            script_log.close()
            self.ctx.error("Error executing {}: {}".format(full_command, error))

        script_log.close()
        self.ctx.info("Execution completed.")
