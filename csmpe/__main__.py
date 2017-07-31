#!/usr/bin/env python
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

try:
    import click
except ImportError:
    print("Install click python package\n pip install click")
    exit()

import logging
import os
import textwrap
import urlparse

from csmpe.context import InstallContext
from csmpe.plugin_managers import get_csm_plugin_manager
from csmpe.plugin_managers.base import install_phases
from csmpe.helpers.mop import MopFile

_PLATFORMS = ["ASR9K", "NCS4K", "NCS6K", "CRS", "ASR900"]
_OS = ["IOS", "XR", "eXR", "XE"]


def print_plugin_info(pm, detail=False, brief=False):
    for plugin, details in pm.plugins.items():
        platforms = ", ".join(details['platforms'])
        phases = ", ".join(details['phases']) if bool(details['phases']) else "Any"
        os = ", ".join(details['os']) if bool(details['os']) else "Any"
        if brief:
            click.echo("[{}] [{}] [{}] {}".format(platforms, phases, os, details['name']))
        else:
            click.echo("Name: {}".format(details['name']))
            click.echo("Platforms: {}".format(platforms))
            click.echo("Phases: {}".format(phases))
            click.echo("OS: {}".format(os))
            description = "Description: {}\n".format(details['description'])
            description = "\n".join(textwrap.wrap(description, 60))
            click.echo(description)

            if detail:
                click.echo("  UUID: {}".format(plugin))
                package_name = details['package_name']
                click.echo("  Package Name: {}".format(package_name))
                pkginfo = pm.get_package_metadata(package_name)
                click.echo("  Summary: {}".format(pkginfo.summary))
                click.echo("  Version: {}".format(pkginfo.version))
                click.echo("  Author: {}".format(pkginfo.author))
                click.echo("  Author Email: {}".format(pkginfo.author_email))
            click.echo()


def validate_phase(ctx, param, value):
    if value:
        if value.strip() not in install_phases:
            raise click.BadParameter("The supported plugin phases are: {}".format(", ".join(install_phases)))
    return value


class URL(click.ParamType):
    name = 'url'

    def convert(self, value, param, ctx):
        if not isinstance(value, tuple):
            parsed = urlparse.urlparse(value)
            if parsed.scheme not in ('telnet', 'ssh'):
                self.fail('invalid URL scheme (%s).  Only telnet and ssh URLs are '
                          'allowed' % parsed, param, ctx)
        return value


@click.group()
def cli():
    """This script allows maintaining and executing the plugins."""
    pass


def filter_plugins(platform=None, phase=None, os=None):
    pm = get_csm_plugin_manager(None, load_plugins=False, invoke_on_load=False)
    pm.set_phase_filter(phase)
    pm.set_platform_filter(platform)
    pm.set_os_filter(os)
    pm.load(invoke_on_load=False)
    return pm


@cli.command("list", help="List all the plugins available.", short_help="List plugins")
@click.option("--platform", type=click.Choice(_PLATFORMS),
              help="Supported platform.")
@click.option("--phase", type=click.Choice(install_phases),
              help="Supported phase.")
@click.option("--os", type=click.Choice(_OS),
              help="Supported OS.")
@click.option("--detail", is_flag=True,
              help="Display detailed information about installed plugins.")
@click.option("--brief", is_flag=True,
              help="Display brief information about installed plugins.")
def plugin_list(platform, phase, os, detail, brief):

    pm = filter_plugins(platform, phase, os)
    click.echo("List of installed plugins:\n")
    if platform:
        click.echo("Plugins for platform: {}".format(platform))
    if phase:
        click.echo("Plugins for phase: {}".format(phase))
    if os:
        click.echo("Plugins for os: {}".format(os))

    print_plugin_info(pm, detail, brief)


run_help_message = "Run specific plugin on the device." +\
    " Optionally, you can specify PLUGIN_NAMES in the end." +\
    " Just wrap each plugin name in quotes. Plugin names should be separated by space." +\
    " Example 1: 'Node Status Check Plugin'." +\
    " Example 2: 'Node Status Check Plugin' 'Node Redundancy Check Plugin' 'ISIS Neighbor Check Plugin'." +\
    " If you want the plugins to be executed in the specified order, make sure to also set the --mop flag."


@cli.command("run", help=run_help_message, short_help="Run plugin")
@click.option("--url", multiple=True, required=True, envvar='CSMPLUGIN_URLS', type=URL(),
              help='The connection url to the host (i.e. telnet://user:pass@hostname). '
                   'The --url option can be repeated to define multiple jumphost urls. '
                   'If no --url option provided the CSMPLUGIN_URLS environment variable is used.')
@click.option("--phase", required=False, type=click.Choice(install_phases),
              help="An install phase to run the plugin for.")
@click.option("--cmd", multiple=True, default=[],
              help='The command to be passed to the plugin in ')
@click.option("--log_dir", default="/tmp", type=click.Path(),
              help="An install phase to run the plugin for. If not path specified then default /tmp directory is used.")
@click.option("--package", default=[], multiple=True,
              help="Package for install operations. This package option can be repeated to provide multiple packages.")
@click.option("--repository_url", default=None,
              help="The package repository URL. (i.e. tftp://server/dir")
@click.option("--mopfile", required=False, type=click.File("r"),
              help='The filename with the MOP definition')
@click.option("--mop", required=False, is_flag=True, default=False,
              help='When this flag is set, a list of plugin name(s) must be provided '
                   'in the end of the command to define the order of execution of the '
                   'specified plugins. When this flag is not set, if any plugin name '
                   'is provided in the end, the specified plugin(s) will be executed '
                   'in no particular order.')
@click.argument("plugin_names", required=False, default=None, nargs=-1)
def plugin_run(url, phase, cmd, log_dir, package, repository_url, mopfile, mop, plugin_names):

    if mop and not plugin_names:
        raise click.BadParameter("plugin names must be specified in the end of the command when --mop is set.")

    ctx = InstallContext()
    ctx.hostname = "Hostname"
    ctx.host_urls = list(url)
    ctx.success = False

    ctx.requested_action = phase
    ctx.log_directory = log_dir
    session_filename = os.path.join(log_dir, "session.log")
    plugins_filename = os.path.join(log_dir, "plugins.log")
    condoor_filename = os.path.join(log_dir, "condoor.log")

    if os.path.exists(session_filename):
        os.remove(session_filename)
    if os.path.exists(plugins_filename):
        os.remove(plugins_filename)
    if os.path.exists(condoor_filename):
        os.remove(condoor_filename)

    ctx.log_level = logging.DEBUG
    ctx.software_packages = list(package)
    ctx.server_repository_url = repository_url

    if cmd:
        ctx.custom_commands = list(cmd)

    if mop:
        ctx.plugin_execution_order = list(plugin_names)

    if mopfile:
        mop = MopFile(mopfile)
        plugin_names = list(mop.plugin_names())
        ctx.plugin_execution_order = mop.plugin_names()
        ctx.mop_specs = mop['mop']

    pm = get_csm_plugin_manager(ctx)
    pm.set_name_filter(set(plugin_names))

    results = pm.dispatch("run")

    click.echo("\n Plugin execution finished.\n")
    click.echo("Log files dir: {}".format(log_dir))
    click.echo(" {} - device session log".format(session_filename))
    click.echo(" {} - plugin execution log".format(plugins_filename))
    click.echo(" {} - device connection debug log".format(condoor_filename))
    click.echo("Results: {}".format(" ".join(map(str, results))))


if __name__ == '__main__':
    cli()
