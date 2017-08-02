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
import os
from csmpe.helpers.parser import parse
from csmpe.plugins import CSMPlugin
from condoor.exceptions import CommandSyntaxError

class Plugin(CSMPlugin):
    """This plugin checks the ISIS neighbor."""
    name = "LDP Neighbor Check"
    phases = {'Pre-Check', 'Post-Check'}
    os = {'XR', 'eXR', 'XRv'}

    def _run(self):
        template = os.path.join(os.path.dirname(__file__), "show-mpls-ldp-neighbor-brief.textfsm")
        try:
            output = self.ctx.send("show mpls ldp neighbor brief")
        except CommandSyntaxError:
            self.ctx.error("Command syntax error")
        result = parse(output, template)

        if self.ctx.phase == "Pre-Check":
            self.ctx.save_data("ldp_neighbors", result)

        if self.ctx.phase == "Post-Check":
            print(self.ctx.load_data("ldp_neighbors"))
            previous_data, timestamp = self.ctx.load_data("ldp_neighbors")
            self.compare_data(previous_data, result)

    def compare_data(self, previous_data, current_data):
        if previous_data is None:
            self.ctx.warning("No data stored from Pre-Check phase. Can't compare.")
            return

        print(previous_data)
        print(current_data)

