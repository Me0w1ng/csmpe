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
from utils import get_filesystems


class Plugin(CSMPlugin):
    """This plugin checks if the filesystems are writable"""
    name = "Filesystem Check Plugin"
    platforms = {'ASR9K', 'CRS'}
    phases = {'Pre-Upgrade'}
    os = {'None'}

    def _can_create_dir(self, filesystem):

        def send_newline(ctx):
            ctx.ctrl.sendline()
            return True

        def error(ctx):
            ctx.message = "Filesystem error"
            return False

        def readonly(ctx):
            ctx.message = "Filesystem is readonly"
            return False

        test_dir = "rw_test"
        directory = filesystem + test_dir

        REMOVE_DIR = re.compile(re.escape("Remove directory filename [{}]?".format(test_dir)))
        DELETE_CONFIRM = re.compile(re.escape("Delete {}/{}[confirm]".format(filesystem, test_dir)))
        # TODO(klstnaie): this plugin is IOX XR specific. Must be fixed
        # IOS XR specific - does not cover the eXR
        REMOVE_ERROR = re.compile(re.escape("%Error Removing dir {} (Directory doesnot exist)".format(test_dir)))

        CREATE_DIR = re.compile(re.escape("Create directory filename [{}]?".format(test_dir)))
        CREATED_DIR = re.compile(re.escape("Created dir {}/{}".format(filesystem, test_dir)))
        READONLY = re.compile(re.escape("%Error Creating Directory {}/{} (Read-only file system)".format(
            filesystem, test_dir)))

        command = "rmdir {}".format(directory)
        PROMPT = self.ctx.prompt
        TIMEOUT = self.ctx.TIMEOUT

        events = [PROMPT, REMOVE_DIR, DELETE_CONFIRM, REMOVE_ERROR, TIMEOUT]
        transitions = [
            (REMOVE_DIR, [0], 1, send_newline, 5),
            (DELETE_CONFIRM, [1], 2, send_newline, 5),
            # if dir does not exist initially it's ok
            (REMOVE_ERROR, [0], 2, None, 0),
            (PROMPT, [2], -1, None, 0),
            (TIMEOUT, [0, 1, 2], -1, error, 0)

        ]
        self.ctx.info("Removing test directory from {} if exists".format(directory))
        if not self.ctx.run_fsm(self.name, command, events, transitions, timeout=5):
            return False

        command = "mkdir {}".format(directory)
        events = [PROMPT, CREATE_DIR, CREATED_DIR, READONLY, TIMEOUT]
        transitions = [
            (CREATE_DIR, [0], 1, send_newline, 5),
            (CREATED_DIR, [1], 2, send_newline, 5),
            (PROMPT, [2], -1, None, 0),
            (TIMEOUT, [0, 1, 2], -1, error, 0),
            (READONLY, [1], -1, readonly, 0)
        ]
        self.ctx.info("Creating test directory on {}".format(directory))
        if not self.ctx.run_fsm(self.name, command, events, transitions, timeout=5):
            return False

        command = "rmdir {}".format(directory)
        events = [PROMPT, REMOVE_DIR, DELETE_CONFIRM, REMOVE_ERROR, TIMEOUT]
        transitions = [
            (REMOVE_DIR, [0], 1, send_newline, 5),
            (DELETE_CONFIRM, [1], 2, send_newline, 5),
            (REMOVE_ERROR, [0], -1, error, 0),
            (PROMPT, [2], -1, None, 0),
            (TIMEOUT, [0, 1, 2], -1, error, 0)

        ]
        self.ctx.info("Removing test directory from {}".format(directory))
        if not self.ctx.run_fsm(self.name, command, events, transitions, timeout=5):
            return False

        return True

    def run(self):

        file_systems = get_filesystems(self.ctx)

        disk0 = file_systems.get('disk0:', None)
        if not disk0:
            self.ctx.error("No filesystem 'disk0:' on active RP.")

        disk1 = file_systems.get('disk1:', None)
        if not disk1:
            self.ctx.warning("No filesystem 'disk1:' on active RP.")

        for fs, values in file_systems.iteritems():
            if 'rw' not in values.get('flags'):
                self.ctx.error("{} is not writable.".format(fs))

        if not self._can_create_dir("disk0:"):
            self.ctx.error("Can't create directory on 'disk0:'. Filesystem might be read only. Please contact TAC.")

        self.ctx.info("Filesystem disk0: is writable.")
        return True
