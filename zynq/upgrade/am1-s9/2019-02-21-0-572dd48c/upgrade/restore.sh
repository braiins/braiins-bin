#!/bin/sh

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

set -e

# write all images to NAND
mtd -e BOOT.bin-env-dts-kernel write ./BOOT.bin BOOT.bin-env-dts-kernel
mtd -np 0x1020000 write ./devicetree.dtb BOOT.bin-env-dts-kernel
mtd -np 0x1100000 write ./uImage BOOT.bin-env-dts-kernel
mtd -np 0x1040000 write ./upgrade-marker.bin BOOT.bin-env-dts-kernel

mtd -e upgrade-rootfs write ./rootfs.jffs2 upgrade-rootfs

mtd erase angstram-rootfs
sync

ubiattach -p /dev/mtd2
mount -t ubifs ubi0:rootfs /mnt

# restore configuration
tar xvzf ./config.tar.gz
mv ./config /mnt/home/usr_config

umount /mnt
ubidetach -p /dev/mtd2
sync
