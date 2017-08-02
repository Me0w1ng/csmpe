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
from unittest import TestCase

from csmpe.context import InstallContext, PluginContext
from csmpe.plugin_managers import get_csm_plugin_manager


class TestPluginContext(TestCase):
    def test_save_load_data(self):
        """Test if the data is stored properly in the context."""
        ctx = InstallContext()
        plugin_context = PluginContext()
        # associate InstallContext outside constructor to avoid auto connect.
        plugin_context._csm = ctx

        data1 = {"key1": 1, "key2": {
            "key3": "test"
        }}
        plugin_context.save_data('test_data', data1)
        data2, timestamp = plugin_context.load_data('test_data')
        self.assertDictEqual(data1, data2, "Loaded data different then saved.")

    def test_save_load_data_no_key(self):
        """Test if the data is None when no key."""
        ctx = InstallContext()
        plugin_context = PluginContext()
        # associate InstallContext outside constructor to avoid auto connect.
        plugin_context._csm = ctx

        data, timestamp = plugin_context.load_data('no_key')
        self.assertIsNone(data, "No key does not return None")

