# Copyright (C) 2020  Braiins Systems s.r.o.
#
# This file is part of Braiins Open-Source Initiative (BOSI).
#
# BOSI is free software: you can redistribute it and/or modify
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
#
# Please, keep in mind that we may also license BOSI or any part thereof
# under a proprietary license. For more information on the terms and conditions
# of such proprietary license or if you have any other questions, please
# contact us at opensource@braiins.com.

# Add path to Vivado executables if necessary
# export PATH=$PATH:
# Set license file
# export XILINXD_LICENSE_FILE=

# --------------------------------------------------------------------------------------------------
# Exit immediately if a command exits with a non-zero status.
set -e

# List of supported miners
supported_miners=("S9" "S15" "S17")

# --------------------------------------------------------------------------------------------------
print_help() {
    echo ""
    echo "Usage: $0 MINER1 [MINER2 ...]"
    echo "  MINER - name of the Antminer miner, available values: ${supported_miners[@]}"
}

if [ "$1" == "--help" ]; then
    echo "Script for automatic generation of Xilinx FPGA bitstreams and prepare commit"
    print_help
    exit 0
fi

if [ "$#" -lt 1 ]; then
    echo "Wrong number of arguments!"
    echo "At least one miner must be defined"
    print_help
    exit 1
fi

# --------------------------------------------------------------------------------------------------
# Check input arguments
if [[ ! " ${supported_miners[@]} " =~ " $@ " ]]; then
    echo "Error: Input list contains unsupported miner!"
    echo "Supported miners are following: ${supported_miners[@]}"
    exit 1
fi

# Backup root directory
root=`pwd`

# --------------------------------------------------------------------------------------------------
# Check if submodule is initialized
if [ ! -d "zynq/bitstream/am2-s17/src/open" ]; then
    echo "Submodules are not initialized, trying download it ..."
    git submodule update --init --recursive
fi

# Pull repository
git pull origin master --recurse-submodules

# Create new branch
git checkout -b bos/xxx/new-bitstream-`date +%s`

# Iterate over all miners
for miner in "$@"
do
    echo "================================================================================"
    echo "Generating bitstream for miner $miner"

    # Prepare name of directory
    if [ "$miner" == "S9" ]; then
        dir=${root}/zynq/bitstream/am1-${miner,,}
    else
        dir=${root}/zynq/bitstream/am2-${miner,,}
    fi

    # ----------------------------------------------------------------------------------------------
    # Pull submodule
    cd $dir/src/
    git pull origin master

    # Save last commit message
    git_msg=`git log --oneline | head -n 1 | cut -d " " -f 2-`

    # ----------------------------------------------------------------------------------------------
    # Run synthesis
    cd open/hw/zynq-io-am1-s9/design/
    ./run.sh $miner

    # ----------------------------------------------------------------------------------------------
    # Check if bitstream exists
    echo "================================================================================"
    bitstream="build_$miner/results/system.bit"
    if [ ! -f $bitstream ]; then
        echo "Bitstream $bitstream doesn't exist!"
        exit 1
    fi

    cp $bitstream $dir

    # Get Build ID number as hex
    build_id=`grep "Build ID:" build_$miner/vivado.log | head -n 1 | cut -d " " -f 3`
    build_id_hex=`printf '0x%X' $build_id`

    # ----------------------------------------------------------------------------------------------
    # Copy and compress bitstream
    cd $dir
    rm -f system.bit.gz
    gzip system.bit

    # ----------------------------------------------------------------------------------------------
    # Create git commit
    git add system.bit.gz
    git add src/
    git commit -m "bosminer: $miner: New bitstream" -m "- $git_msg" -m "BUILD_ID $build_id_hex"

done

echo "===================================== Done ====================================="
echo "Check commit message and amend it if update is required"
echo "If commit is ready then rename branch, push commit and create merge request"
echo "================================================================================"
