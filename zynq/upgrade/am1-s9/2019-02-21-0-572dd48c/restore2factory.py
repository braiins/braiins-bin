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

import argparse
import tarfile
import sys
import os

import upgrade.platform as platform
import upgrade.backup as backup

from upgrade.platform import PlatformStop
from upgrade.ssh import SSHManager, SSHError
from upgrade.transfer import wait_for_port
from tempfile import TemporaryDirectory
from glob import glob

USERNAME = 'root'
PASSWORD = None

REBOOT_DELAY = (3, 8)


class RestoreStop(Exception):
    pass


def detect_bos_mode(ssh):
    mode = backup.ssh_mode(ssh)
    print('Detected bOS mode: {}'.format(mode))
    return mode


def restore_firmware(args, ssh, backup_dir=None):
    mtdparts_params = platform.get_factory_mtdparts(args, ssh, backup_dir)
    mtdparts = list(backup.parse_mtdparts(mtdparts_params))

    with platform.prepare_restore(args, backup_dir):
        if args.mode != backup.MODE_NAND:
            # restore firmware from SD or recovery mode
            platform.restore_firmware(args, ssh, backup_dir, mtdparts)
            return

        # restart miner to recovery mode with target MTD parts
        ssh.run('fw_setenv', backup.RECOVERY_MTDPARTS[:-1], '"{}"'.format(mtdparts_params))
        ssh.run('miner', 'run_recovery')
        # continue after miner is in the recovery mode
        print('Rebooting...', end='')
        wait_for_port(args.hostname, 22, REBOOT_DELAY)
        print('Connecting to remote host...')
        # do not use host keys after restart because recovery mode has different keys for the same MAC
        with SSHManager(args.hostname, USERNAME, PASSWORD, load_host_keys=False) as ssh:
            args.mode = detect_bos_mode(ssh)
            if args.mode == backup.MODE_NAND:
                print('Could not reboot to recovery mode!')
                raise RestoreStop
            # restore firmware from recovery mode
            platform.restore_firmware(args, ssh, backup_dir, mtdparts)


def main(args):
    print('Connecting to remote host...')
    with SSHManager(args.hostname, USERNAME, PASSWORD) as ssh:
        args.mode = detect_bos_mode(ssh)

        backup_path = args.backup
        if not backup_path:
            mac = backup.ssh_mac(ssh)
            # try to find backup from default backup directory
            backup_path = backup.get_output_dir(mac, date=False, create=False)
            backup_path = sorted(glob('*{}*'.format(backup_path)), reverse=True)
            if not backup_path:
                # recover firmware without previous backup
                restore_firmware(args, ssh)
                return
            backup_path = backup_path[0]
            print('Found backup: {}'.format(backup_path))

        if os.path.isdir(backup_path):
            restore_firmware(args, ssh, backup_path)
        else:
            with TemporaryDirectory() as backup_dir:
                tar = tarfile.open(backup_path)
                print('Extracting backup tarball...')
                tar.extractall(path=backup_dir)
                tar.close()
                uenv_path = glob(os.path.join(backup_dir, '*', 'uEnv.txt'))
                if not uenv_path:
                    print('Invalid backup tarball!')
                    return
                backup_dir = os.path.split(uenv_path[0])[0]
                restore_firmware(args, ssh, backup_dir)


if __name__ == "__main__":
    # execute only if run as a script
    parser = argparse.ArgumentParser()

    parser.add_argument('backup', nargs='?',
                        help='path to directory or tgz file with data for miner restore')
    parser.add_argument('hostname',
                        help='hostname of miner with bOS firmware')

    platform.add_restore_arguments(parser)

    # parse command line arguments
    args = parser.parse_args(sys.argv[1:])

    try:
        main(args)
    except SSHError as e:
        print(str(e))
        sys.exit(1)
    except RestoreStop:
        sys.exit(2)
    except PlatformStop:
        sys.exit(3)
