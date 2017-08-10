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

import abc
import six
import yaml


def apply_data_config(cls):
    if cls.data_config_file:
        try:
            plugin_data_specs = yaml.load(open(cls.data_config_file))
            cls.data_specs = plugin_data_specs
            return cls
        except IOError:
            pass
    cls.data_specs = {}
    return cls


@apply_data_config
@six.add_metaclass(abc.ABCMeta)
class CSMPlugin(object):
    """This is a base class for all plugins. Inheriting from this class is not mandatory,
    however the Plugin class must implement the `run` method.
    The object constructor must accept a single parameter which represents
    the :class:`csmpe.InstallContext` object.

    The Plugin class must also have the following attributes.
    """
    #: The string representing the name of the plugin.
    name = "Plugin Template"

    #: The set of strings representing the install phases during which the plugin will be dispatched.
    #: Empty set means that plugin will NEVER be executed. The currently supported values are:
    #: *Pre-Check*, *Pre-Add*, *Add*, *Pre-Activate*, *Pre-Deactivate*, *Deactivate*,
    #: *Remove*, *Commit*
    phases = set()

    #: The set of strings representing the supported platforms by the plugin. Empty set means ANY platform.
    #: The currently supported values are: *ASR9K*, *CRS*, *NCS6K*
    platforms = set()

    #: The set of operating system type strings. The supported values are: *IOS*, *XR*, *eXR*, *XE*.
    #: Empty set means plugin will be executed regardless of the detected operating system.
    os = set()

    data_config_file = None

    need_connection = True

    def __init__(self, ctx):
        """ This is a constructor of a plugin object. The constructor can be overridden by the plugin code.
        The CSM Plugin Engine passes the :class:`csmpe.InstallContext` object
        as an argument. This context object provides the API interface for the plugin including:

        - Device communication (using condoor)
        - CSM status and information update
        - Progress, error and status logging.

        :param ctx: The install context object :class:`csmpe.InstallContext`
        :return: None
        """
        self.ctx = ctx

    def run(self, data=None):
        self.ctx.current_plugin = None
        self.ctx.info("Dispatching: '{}#{}'".format(self.name, self.ctx.plugin_number))
        self.ctx.post_status(self.name)
        self.ctx.current_plugin = self.name

        current_connection = self.ctx.connection

        if not current_connection and self.need_connection:
            self.ctx.info("Reconnecting with device.")
            self.ctx.init_connection()
        elif current_connection and not self.need_connection:
            self.ctx.info("Disconnecting with device.")
            current_connection.disconnect()
            self.ctx.connection = None

        self.ctx.init_plugin_data(self.data_specs)

        self._run()
        self.ctx.plugin_number += 1

    @abc.abstractmethod
    def _run(self):
        """
        Must be implemented by the plugin code.

        :return: None
        """
