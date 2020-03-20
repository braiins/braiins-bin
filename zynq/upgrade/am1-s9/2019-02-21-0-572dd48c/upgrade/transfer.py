#!/usr/bin/env python3

# Copyright (C) 2018  Braiins Systems s.r.o.
#
# This file is part of Braiins Build System (BB).
#
# BB is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import socket
import time
import sys
import os

from progress.bar import Bar
from time import time as now


class Progress:
    def __init__(self, file_path, file_size=None):
        self.file_path = file_path
        self.file_size = file_size
        self.progress = None
        self._last = 0

    def __enter__(self):
        file_size = os.path.getsize(self.file_path) if self.file_size is None else self.file_size
        self.progress = Bar('{}:'.format(self.file_path), max=file_size)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.finish()

    def __call__(self, transferred: int, total: int):
        self.progress.next(transferred - self._last)
        self._last = transferred


def upload_local_files(sftp, local_path):
    for root, dirs, files in os.walk(local_path):
        root_remote = os.path.relpath(root, local_path)
        for name in files:
            local_file = os.path.join(root, name)
            with Progress(local_file) as progress:
                sftp.put(local_file, '/'.join([root_remote, name]), callback=progress)
        for name in dirs:
            sftp.mkdir('/'.join([root_remote, name]))


def wait_net_service(server, port, timeout=None):
    s = socket.socket()
    end = now() + timeout if timeout else None

    while True:
        try:
            if timeout:
                next_timeout = end - now()
                if next_timeout < 0:
                    return False
                else:
                    s.settimeout(next_timeout)

            s.connect((server, port))
        except socket.timeout:
            if timeout:
                return False
        except socket.error:
            pass
        else:
            s.close()
            return True


def wait(delay, char):
    for _ in range(delay):
        time.sleep(1)
        print(char, end='')
        sys.stdout.flush()


def wait_for_port(server, port, delay, char=None):
    char = char or '.'
    delay_before, delay_after = delay
    wait(delay_before, char)
    while not wait_net_service(server, port, 1):
        print(char, end='')
        sys.stdout.flush()
    wait(delay_after, char)
    print()
