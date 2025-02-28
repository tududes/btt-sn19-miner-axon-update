#!/bin/bash

# change directory to where this script file is located
cd "$(dirname "$0")"

source .venv/bin/activate

# Check if test flag is provided
if [ "$1" == "--test" ]; then
    echo "Running in test mode..."
    python3 update_miner_axon_on_chain.py --test
else
    # Run in normal mode
    python3 update_miner_axon_on_chain.py
fi