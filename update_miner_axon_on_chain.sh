#!/bin/bash

# change directory to where this script file is located
cd "$(dirname "$0")"

source .venv/bin/activate
python3 update_miner_axon_on_chain.py