import time
import re
import yaml
import collections

from csmpe.context import PluginError
from csmpe.core_plugins.csm_custom_commands_capture.plugin import Plugin as CmdCapturePlugin

SUPPORTED_HW_SPECS_FILE = "./asr9k_x64/asr9k_x64_supported_hardware.yaml"

ADMIN_RP = "\d+/RS?P\d+"
ADMIN_LC = "\d+/\d+"


def log_and_post_status(ctx, msg):
    ctx.info(msg)
    ctx.post_status(msg)


def parse_exr_admin_show_platform(output):
    """Get all RSP/RP/LC string node names matched with the card type."""
    inventory = dict()
    lines = output.split('\n')

    for line in lines:
        line = line.strip()
        if len(line) > 0 and line[0].isdigit():
            node = line[:10].strip()
            # print "node = *{}*".format(node)
            node_type = line[10:34].strip()
            # print "node_type = *{}*".format(node_type)
            inventory[node] = node_type
    return inventory


def parse_admin_show_platform(output):
    """
    :param output: output from 'admin show platform' for ASR9K
    :return: list of tuples of (node name, node info)

    ASR9K:
    Node            Type                      State            Config State
    -----------------------------------------------------------------------------
    0/RSP0/CPU0     A9K-RSP440-SE(Active)     IOS XR RUN       PWR,NSHUT,MON
    0/FT0/SP        ASR-9006-FAN              READY
    0/1/CPU0        A9K-40GE-E                IOS XR RUN       PWR,NSHUT,MON
    0/2/CPU0        A9K-MOD80-SE              UNPOWERED        NPWR,NSHUT,MON
    0/3/CPU0        A9K-8T-L                  UNPOWERED        NPWR,NSHUT,MON
    0/PS0/M0/SP     A9K-3KW-AC                READY            PWR,NSHUT,MON
    0/PS0/M1/SP     A9K-3KW-AC                READY            PWR,NSHUT,MON
    """
    inventory = []
    lines = output.split('\n')
    for line in lines:
        line = line.strip()
        if len(line) > 0 and line[0].isdigit():
            node = line[:16].strip()
            entry = {
                'type': line[16:42].strip(),
                'state': line[42:59].strip(),
                'config_state': line[59:].strip()
            }
            inventory.append((node, entry))
            # print node

    return inventory


def get_all_supported_nodes(ctx, supported_cards):
    """Get the list of string node names(all available RSP/RP/LC) that are supported for migration."""
    supported_nodes = []
    ctx.send("admin")
    # show platform can take more than 1 minute after router reload. Issue No. 47
    output = ctx.send("show platform", timeout=600)
    inventory = parse_exr_admin_show_platform(output)

    rp_pattern = re.compile(ADMIN_RP)
    lc_pattern = re.compile(ADMIN_LC)
    supported_rp = supported_cards["RP_RSP"]
    supported_lc = supported_cards["LC"]

    for node, node_type in inventory.items():
        if rp_pattern.match(node):
            for rp in supported_rp:
                if rp in node_type:
                    supported_nodes.append(node)
                    break
        elif lc_pattern.match(node):
            for lc in supported_lc:
                if lc == node_type:
                    supported_nodes.append(node)
                    break
    ctx.send("exit")
    ctx.info("Support nodes: " + str(supported_nodes))
    return supported_nodes


def compare_version_numbers(version1, version2):
    nums1 = version1.split('.')
    nums2 = version2.split('.')
    for i in range(min(len(nums1), len(nums2))):
        if int(nums1[i]) < int(nums2[i]):
            return -1
        elif int(nums1[i]) > int(nums2[i]):
            return 1
    if len(nums1) == len(nums2):
        return 0
    return -1 if len(nums1) < len(nums2) else 1


def get_version(ctx):
    output = ctx.send("show version | include Version")
    version = re.search("Version\s*?(\d+\.\d+\.\d+)(?:\.\d+I)?", output)
    if not version:
        ctx.error("Failure to retrieve release number.")
    return version.group(1)


def get_supported_cards_for_exr_version(ctx, supported_hw_list, exr_version):
    supported_cards = collections.defaultdict(list)
    for supported_hw in supported_hw_list:
        if 'version' not in supported_hw:
            ctx.error("Missing version number in the ASR9K-X64 supported hardware file.")
        if compare_version_numbers(exr_version, supported_hw['version']) >= 0:
            for card_type in supported_hw:
                if card_type != 'version':
                    supported_cards[card_type].extend(supported_hw[card_type])
        else:
            break
    return supported_cards


def check_exr_final_band(ctx, timeout=7200):
    log_and_post_status(ctx, "Waiting for all supported nodes to come to FINAL Band.")
    if wait_for_final_band(ctx, timeout):
        log_and_post_status(ctx, "All supported nodes are in FINAL Band.")
    else:
        log_and_post_status(ctx, "Warning: Not all supported nodes went to FINAL Band after {} minutes.".format(timeout / 60))
    return True


def wait_for_final_band(ctx, timeout):
    """This is for ASR9K eXR. Wait for all present nodes to come to FINAL Band."""
    exr_version = get_version(ctx)
    try:
        with open(SUPPORTED_HW_SPECS_FILE) as supported_hw_file:
            supported_hw_list = yaml.load(supported_hw_file)
    except Exception as e:
        ctx.error("Loading ASR9K-X64 supported hardware file hit exception: {}".format(str(e)))

    supported_cards = get_supported_cards_for_exr_version(ctx, supported_hw_list, exr_version)
    supported_nodes = get_all_supported_nodes(ctx, supported_cards)
    # Wait for all nodes to Final Band
    poll_time = 20
    time_waited = 0

    cmd = "show platform vm"
    # ctx.send("admin")
    # cmd = "show platform"
    while 1:
        # Wait till all nodes are in FINAL Band
        time_waited += poll_time
        if time_waited >= timeout:
            break
        time.sleep(poll_time)
        output = ctx.send(cmd)
        if check_show_plat_vm(output, supported_nodes):
            return True

        """
        if check_sw_status_admin(supported_nodes, output):
            ctx.send("exit")
        """
    # ctx.send("exit")
    # Some nodes did not come to FINAL Band
    return False


def check_show_plat_vm(output, supported_nodes):
    """Check if all supported nodes reached FINAL Band status"""

    entries_in_show_plat_vm = []
    lines = output.splitlines()
    for line in lines:
        line = line.strip()
        if len(line) > 0 and line[0].isdigit():
            entries_in_show_plat_vm.append(line)

    if len(entries_in_show_plat_vm) >= len(supported_nodes):
        ready_nodes_count = 0
        for entry in entries_in_show_plat_vm:
            for node in supported_nodes:
                if entry.startswith(node):
                    if 'FINAL Band' in entry:
                        ready_nodes_count += 1
                        break
                    else:
                        return False
        if ready_nodes_count == len(supported_nodes):
            return True
    return False


def check_sw_status_admin(supported_nodes, output):
    """Check if a node is in OPERATIONAL status"""
    lines = output.splitlines()

    for line in lines:
        line = line.strip()
        if len(line) > 0 and line[0].isdigit():
            node = line[0:10].strip()
            if node in supported_nodes:
                sw_status = line[48:62].strip()
                if "OPERATIONAL" not in sw_status:
                    return False
    return True


def run_additional_custom_commands(ctx, additional_commands):
    """
    Help method to run additional custom commands besides the ones defined by user
    :param ctx: plugin context (PluginContext)
    :param additional_commands: a set containing all the custom commands you wish to run
    :return: None
    """
    user_defined_custom_commands = ctx.custom_commands

    if type(user_defined_custom_commands) is list:
        for command in user_defined_custom_commands:
            if command in additional_commands:
                additional_commands.remove(command)

    if additional_commands:
        ctx.custom_commands = list(additional_commands)
        try:
            cmd_capture_plugin = CmdCapturePlugin(ctx)
            cmd_capture_plugin.run()
        except PluginError as e:
            ctx.warning("Failed to capture output of a command. Error: {}".format(e))

        ctx.custom_commands = user_defined_custom_commands

    return
