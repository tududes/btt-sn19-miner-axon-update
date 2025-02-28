# Update miner axon ip on chain in a cron job

This script automatically updates your SN19 miner's axon IP address on the Bittensor network. It's useful when your IP changes or if you need to maintain your miner's registration with the correct IP. The script uses the Fiber API for improved compatibility and dependency management.

### Install dependencies
```bash
# Install python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv
```


### Clone the repo and set things up
```bash
cd $HOME
git clone https://github.com/tududes/btt-sn19-miner-axon-update
cd ./btt-sn19-miner-axon-update

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```


### Set up the env file for this script
```bash
cd $HOME/btt-sn19-miner-axon-update

# update the NINETEEN_REPO_DIRECTORY variable - this should point to your nineteen repository location
export NINETEEN_REPO_DIRECTORY=$HOME/nineteen
echo "NINETEEN_REPO_DIRECTORY=$NINETEEN_REPO_DIRECTORY" >> .env

# check the .env file visually
nano .env
```

### Set up the test environment (optional)
The repository includes a `.env.test` file that is used when running the script in test mode. You can modify this file to test with your specific network settings:

```bash
# Edit the test environment file if needed
nano .env.test
```

Default test settings:
```
NINETEEN_REPO_DIRECTORY=./test_dir
HOTKEY_NAME=test_hotkey
WALLET_NAME=test_wallet
SUBTENSOR_NETWORK=finney
SUBTENSOR_ADDRESS=wss://entrypoint-finney.opentensor.ai:443
NODE_PORT=8091
NETUID=19
```


### Required variables in your nineteen repo's .env files
Each miner configuration file in your nineteen repo folder must have the following variables:

```
HOTKEY_NAME          # The name of your hotkey
WALLET_NAME          # The name of your wallet 
SUBTENSOR_NETWORK    # Network name (e.g., finney, local)
SUBTENSOR_ADDRESS    # Subtensor endpoint (e.g., wss://entrypoint-finney.opentensor.ai:443)
NODE_PORT            # The port your node is running on
NETUID               # The subnet ID (e.g., 19)
```

You can verify these variables exist in your config files with:

```bash
# navigate to the nineteen repo folder
cd $HOME/nineteen

# check visually 
cat .*.env | grep -E 'HOTKEY_NAME|WALLET_NAME|SUBTENSOR_NETWORK|SUBTENSOR_ADDRESS|NODE_PORT|NETUID'
```


### Make the script executable
```bash
chmod +x $HOME/btt-sn19-miner-axon-update/update_miner_axon_on_chain.sh
```


### Testing the script
The script includes a test mode that allows you to verify it can successfully connect to the Bittensor network and retrieve metagraph data:

```bash
# Run in test mode
./update_miner_axon_on_chain.sh --test
```

This will:
- Connect to the network specified in your `.env.test` file
- Retrieve the metagraph for the specified subnet
- Display the first few nodes' information (UID, Hotkey, Axon IP)
- Verify that everything is working correctly without modifying any data on the chain


### Running the script
After testing, you can run the script normally:

```bash
./update_miner_axon_on_chain.sh
```

### Setting up a cron job
If the script runs successfully, you can set up a cron job to run it every 15 minutes:

```bash
# Append to the crontab:
(crontab -l; echo "*/15 * * * * $HOME/btt-sn19-miner-axon-update/update_miner_axon_on_chain.sh") | crontab -
```


### Script behavior
The script will:
1. Find all `.env` files in your nineteen repo directory
2. Load wallet and hotkey information for each miner
3. Check the current IP:PORT registration on the chain using Fiber
4. Update the IP:PORT if it differs from your current external IP (using the NODE_PORT from your env file)
5. Provide a summary of total hotkeys processed and updated


### Technical details
- The script uses only the Fiber API (no bittensor package) to avoid dependency conflicts
- Only essential data is retrieved from the metagraph (UID, AXON_IP, HOTKEY) for efficiency
- IP addresses are properly handled, including conversion from integer format
- Improved error handling and reporting throughout the process
- Test mode allows easy verification of connectivity and data retrieval


### Troubleshooting
If the script fails to update your IP on the chain, verify:
1. Your wallet and hotkey files exist and are accessible
2. The miner is actually registered on the chain
3. You have the proper permissions to access the nineteen repo directory
4. All required environment variables are set correctly
5. Your internet connection is stable
6. Both hot and cold keys are set up correctly in your wallet

For more detailed diagnostics, run the script in test mode with `--test` flag.


### If you need to cleanup and reinstall packages:
```bash
cd $HOME/btt-sn19-miner-axon-update
deactivate
rm -rf .venv
```