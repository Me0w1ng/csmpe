# =============================================================================
# hardware_audit.py - plugin for auditing hardware for migrating classic XR to eXR/fleXR
#
# Copyright (c)  2013, Cisco Systems
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
import yaml

from csmpe.plugins import CSMPlugin
from migration_lib import SUPPORTED_HW_SPECS_FILE, log_and_post_status, \
    parse_admin_show_platform, get_supported_cards_for_exr_version
from csmpe.core_plugins.csm_get_inventory.ios_xr.plugin import get_package, get_inventory


class Plugin(CSMPlugin):
    """
    A plugin for auditing hardware for migration from
    ASR9K IOS-XR (a.k.a. XR) to ASR9K IOS-XR 64 bit (a.k.a. eXR)

    Console access is needed.
    """
    name = "Migration Audit Plugin"
    platforms = {'ASR9K'}
    phases = {'Migration-Audit'}

    rp_pattern = re.compile('\d+/RS??P\d+/CPU\d+')
    fc_pattern = re.compile('\d+/FC\d+/SP')
    fan_pattern = re.compile('\d+/FT\d+/SP')
    pem_pattern = re.compile('\d+/P[SM]\d+/M?\d+/SP')
    lc_pattern = re.compile('\d+/\d+/CPU\d+')

    def _check_if_hw_supported_and_in_valid_state(self, inventory, supported_hw, override):
        """
        Check if RSP/RP/FAN/PEM/FC/LC/MPA currently on device are supported and are in valid state for migration.

        Minimal requirements (with override=True):
                            all RSP/RP's are supported and in IOS XR RUN state
                            all FC's are supported and in OK state
                            all supported FAN/PEM's are in READY state
                            all supported LC's are in IOS XR RUN state
                            all MPA's are supported and in OK state

        default requirements (with override=False):
                            all RSP/RP's are supported and in IOS XR RUN state
                            all FC's are supported and in OK state
                            all FAN/PEM's are supported and in READY state
                            all supported LC's are in IOS XR RUN state
                            all MPA's are supported and in OK state

        :param inventory: the result for parsing the output of 'admin show platform'
        :param supported_hw: type: defaultdict(list). It stores info about which card types are supported in eXR for
                            RSP/RP/FAN/PEM/FC/LC
        :param override: override the requirement to check FAN/PEM hardware types
        :return: Errors out if a requirement is not met.
                If all requirements are met, returns a dictionary used later in other plugin(s) for monitoring
                the success of FPD upgrade. Keys are node names parsed from 'admin show platform'.
                 Values are integers. Value can either be 0 or 1. value 1 means that this node is supported in
                 eXR and is in valid state for migration. value 0 means that either this node is a PEM/FAN, or
                 this node is not supported in eXR.
        """
        fpd_relevant_nodes = {}

        for i in xrange(0, len(inventory)):
            node, entry = inventory[i]

            if node in fpd_relevant_nodes:
                continue

            if self.rp_pattern.match(node):
                rp_or_rsp = self._check_if_supported_and_in_valid_state(node, entry, supported_hw["RP_RSP"],
                                                                        "IOS XR RUN", for_rp_rsp=True)

                fpd_relevant_nodes[node] = rp_or_rsp

            elif self.fc_pattern.match(node):

                fc = self._check_if_supported_and_in_valid_state(node, entry, supported_hw["FC"], "OK")
                fpd_relevant_nodes[node] = fc

            elif self.lc_pattern.match(node):

                lc = self._check_if_supported_and_in_valid_state(node, entry, supported_hw["LC"], "IOS XR RUN",
                                                                 mandatory_hw_check=False)
                for j in xrange(i + 1, len(inventory)):
                    next_node, next_entry = inventory[j]
                    if "MPA" in next_entry["type"]:
                        mpa = self._check_if_supported_and_in_valid_state(next_node, next_entry,
                                                                          supported_hw["MPA"], "OK")
                        fpd_relevant_nodes[next_node] = mpa

                fpd_relevant_nodes[node] = lc

            elif self.fan_pattern.match(node):
                self._check_if_supported_and_in_valid_state(node, entry, supported_hw["FAN"], "READY",
                                                            mandatory_hw_check=not override,
                                                            mandatory_state_check=not override)
                fpd_relevant_nodes[node] = 0
            elif self.pem_pattern.match(node):
                    self._check_if_supported_and_in_valid_state(node, entry, supported_hw["PEM"], "READY",
                                                                mandatory_hw_check=not override,
                                                                mandatory_state_check=not override)
                    fpd_relevant_nodes[node] = 0
            else:
                fpd_relevant_nodes[node] = 1

        return fpd_relevant_nodes

    def _check_if_supported_and_in_valid_state(self, node_name, value, supported_type_list, operational_state,
                                               mandatory_hw_check=True, mandatory_state_check=True, for_rp_rsp=False):
        """
        Check if a card (RSP/RP/LC/FAN/PEM/FC/MPA) is supported and in valid state.
        :param mandatory_state_check:
        :param node_name: the name under "Node" column in output of CLI "show platform". i.e., "0/RSP0/CPU0"
        :param value: the inventory value for nodes - through parsing output of "show platform"
        :param supported_type_list: the list of card types/pids that are supported for migration
        :param operational_state: the state that this node can be in in order to qualify for migration
        :param mandatory_hw_check: if True and if this node matches the card_pattern, it must be supported card
                          type in order to qualify for migration. If it's False, it's not necessary that the card
                          type is supported, but if it is supported, its state must be in the operational state
                           unless mandatory_state_check is False
        :param mandatory_state_check: if True, this node's state must be in the operational state, if False,
                            it's not necessary that the node is in operational state
        :param for_rp_rsp: if True, this node is RP/RSP, so its parsed node type maybe contain extra content
                            such as '(Active)' or '(Standby)'. Example: A9K-RSP440-SE(Active)
                            so when check is node is supported for RP/RSP, we have to check if a supported hw pid can
                            be found in the node type of the node.
                            For LC/FAN/PEM/FC/MPA, we check if a supported hw pid == node type of the node.
        :return: 1 if it's confirmed that the node is supported. If mandatory_state_check is True, the node is in
                    operational state for migration, otherwise, the node may or may not be in operational state

                 0 if it's not mandatory that this node has supported card type, and it's confirmed that it does
                    not have supported card type, but if mandatory_state_check is True, the node is in
                    operational state for migration, otherwise, the node may or may not be in operational state

                 errors out if this node is in either of the situations below:
                    1. It is mandatory for this node to have supported card type, but the card type of this node is NOT
                       supported for migration.
                    2. It is mandatory for this node to be in operational state, and this node is supported for
                       migration, but it is not in the operational state for migration.
        """
        supported = False

        for supported_type in supported_type_list:
            #
            if (for_rp_rsp and supported_type in value['type']) or \
                    (not for_rp_rsp and supported_type == value['type']):
                supported = True
                break

        if mandatory_hw_check and not supported:
            self.ctx.error("The card type for {} is not supported for migration to ASR9K-X64.".format(node_name) +
                           " Please check the user manual under 'Help' on CSM Server for list of" +
                           " supported hardware for ASR9K-X64. Make sure CSM can access CCO so that the list" +
                           " is always up-to-date.")

        if mandatory_state_check and supported and value['state'] != operational_state:
            self.ctx.error("{} is supported in ASR9K-X64, but it's in {}".format(node_name, value['state']) +
                           " state. Valid operational state for migration: {}".format(operational_state))
        if supported:
            return 1
        return 0

    def run(self):

        software_version_tuple = self.ctx.load_job_data('hardware_audit_version')
        if software_version_tuple:
            software_version = software_version_tuple[0]
            self.ctx.info("Hardware audit for software release version " + str(software_version))
        else:
            self.ctx.error("No software version selected.")

        override_hw_req_tuple = self.ctx.load_job_data('override_hw_req')
        if override_hw_req_tuple and override_hw_req_tuple[0] == "1":
            override_hw_req = True
            log_and_post_status(self.ctx,
                                "Running hardware audit to check minimal requirements for card types and states.")
        else:
            override_hw_req = False
            log_and_post_status(self.ctx, "Running hardware audit on all nodes.")

        try:
            with open(SUPPORTED_HW_SPECS_FILE) as supported_hw_file:
                supported_hw_list = yaml.load(supported_hw_file)
        except Exception as e:
            self.ctx.error("Loading ASR9K-X64 supported hardware file hit exception: {}".format(str(e)))

        self.ctx.info("yaml content:" + str(supported_hw_list))
        supported_cards = get_supported_cards_for_exr_version(self.ctx, supported_hw_list, software_version)

        # show platform can take more than 1 minute after router reload. Issue No. 47
        output = self.ctx.send("admin show platform", timeout=600)
        inventory = parse_admin_show_platform(output)

        log_and_post_status(self.ctx, "Check if cards on device are supported for migration.")
        fpd_relevant_nodes = self._check_if_hw_supported_and_in_valid_state(inventory,
                                                                            supported_cards,
                                                                            override_hw_req)
        self.ctx.save_job_data("fpd_relevant_nodes", fpd_relevant_nodes)

        log_and_post_status(self.ctx, "Hardware audit completed successfully.")

        # Refresh package and inventory information
        get_package(self.ctx)
        get_inventory(self.ctx)

        return True
