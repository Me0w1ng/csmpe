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

from unittest import TestCase, skip, skipIf

from csmpe.core_plugins.csm_install_operations.ios_xr import package_lib as plib


class TestSoftwarePackage(TestCase):
    def test_init(self):
        packages = {
            "disk0:asr9k-mini-px-4.3.2": {
                "platform": "asr9k",
                "package_type": "mini",
                "version": "4.3.2",
                "smu": None,
                "sp": None,
                "subversion": None
            },
            "disk0:asr9k-px-5.3.3.09I.CSCus12345-1.0.0": {
                "platform": "asr9k",
                "package_type": None,
                "version": "5.3.3.09I",
                "smu": "CSCus12345",
                "sp": None,
                "subversion": "1.0.0"
            },
            "disk0:asr9k-px-4.3.2.sp2-1.0.0": {
                "platform": "asr9k",
                "package_type": None,
                "version": "4.3.2",
                "smu": None,
                "sp": "sp2",
                "subversion": "1.0.0"
            },
            "asr9k-px-5.3.3.CSCux61372-0.0.5.d.pie": {
                "platform": "asr9k",
                "package_type": None,
                "version": "5.3.3",
                "smu": "CSCux61372",
                "sp": None,
                "subversion": "0.0.5"
            },
        }
        for package, attributes in packages.items():
            sp = plib.SoftwarePackage(package)
            for attribute, value in attributes.items():
                a = getattr(sp, attribute)
                self.assertEqual(a, value, "{}: {}!={}".format(package, attribute, value))

    def test_unique_elements(self):
        pkg = "asr9k-px-5.3.3.CSCux61372-0.0.5.d.pie"
        pkglist = [pkg, pkg, pkg]

        sp = plib.SoftwarePackage.from_package_list(pkglist)
        self.assertEqual(len(sp), 1)

    def test_intersection(self):
        packages1 = ["disk0:asr9k-mini-px-4.3.2",
                    "asr9k-px-5.3.3.CSCux61372-0.0.5.d.pie",
                    "disk0:asr9k-px-5.3.3.09I.CSCus12345-1.0.0",
                    "disk0:asr9k-px-4.3.2.sp2-1.0.0",
                    "asr9k-px-5.3.3.CSCux61372-0.0.5.d.pie",
                    ]

        packages2 = ["disk0:asr9k-px-5.3.3.09I.CSCus12345-1.0.0",
                    "disk0:asr9k-px-4.3.2.sp2-1.0.0",
                    "asr9k-px-5.3.3.CSCux61372-0.0.5.d.pie",
                    ]

        sp1 = plib.SoftwarePackage.from_package_list(packages1)
        sp2 = plib.SoftwarePackage.from_package_list(packages2)

        packages = sp1 & sp2
        self.assertEqual(len(packages), len(packages2))

        for pkg in packages:
            self.assertTrue(pkg.package_name in packages2)


    def test_sub(self):
        pass


    def test_import_from_cmd(self):
        output = """
Default Profile:
  SDRs:
    Owner
  Inactive Packages:
    disk0:asr9k-mini-px-5.3.1
    disk0:asr9k-mpls-px-5.3.1
    disk0:asr9k-bng-px-5.3.1
    disk0:asr9k-fpd-px-5.3.1
    disk0:asr9k-k9sec-px-5.3.1
    disk0:asr9k-li-px-5.3.1
    disk0:asr9k-mcast-px-5.3.1
    disk0:asr9k-mgbl-px-5.3.1
    disk0:asr9k-doc-px-5.3.1
    disk0:asr9k-optic-px-5.3.1
    disk0:asr9k-services-px-5.3.1
    disk0:asr9k-video-px-5.3.1
    disk0:asr9k-doc-px-5.3.3
    disk0:asr9k-px-5.3.3.09I.CSCus12345-1.0.0
    disk0:asr9k-services-px-5.2.4
    disk0:asr9k-video-px-5.2.4
"""
        pkgs = plib.SoftwarePackage.from_show_cmd(output)

        self.assertEqual(len(pkgs), 16)

        p = plib.SoftwarePackage("asr9k-px-5.3.3.09I.CSCus12345-1.0.0")

        self.assertTrue(p in pkgs)

