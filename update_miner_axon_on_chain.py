import os
from pathlib import Path
import ujson as json # pip install ujson
import pandas as pd # pip install pandas
import bittensor as bt # pip install bittensor
from substrateinterface import Keypair # pip install substrate-interface
import subprocess
import requests
from dotenv import load_dotenv, dotenv_values
import asyncio
from fiber.chain import chain_utils, interface, metagraph, post_ip_to_chain, weights
from fiber.chain.fetch_nodes import get_nodes_for_netuid


load_dotenv()
NINETEEN_REPO_DIRECTORY = os.environ.get("NINETEEN_REPO_DIRECTORY")
NODE_EXTERNAL_IP = requests.get('https://ipinfo.io/json').json()['ip']


def get_hotkey_file_path(wallet_name: str, hotkey_name: str) -> Path:
    file_path = Path.home() / ".bittensor" / "wallets" / wallet_name / "hotkeys" / hotkey_name
    return file_path

def load_hotkey_keypair(wallet_name, hotkey_name):
    file_path = get_hotkey_file_path(wallet_name, hotkey_name)
    try:
        with open(file_path, "r") as file:
            keypair_data = json.load(file)
        return Keypair.create_from_seed(keypair_data["secretSeed"])
    except Exception as e:
        raise ValueError(f"Failed to load keypair: {str(e)}") from e

def fetch_metagraph(subtensor_address, netuid):
    # Initialize subtensor connection
    try:
        print(f"Fetching metagraph for netuid {netuid} from subtensor network: {subtensor_address}")
        subtensor = bt.subtensor(network=f"{subtensor_address}")
    except Exception as e:
        print(f"Error connecting to subtensor network: {e}")


    netuid_int = int(netuid)
    try:
        metagraph = subtensor.metagraph(netuid=netuid_int)
    except Exception as e:
        print(f"Error fetching metagraph for netuid {netuid}: {e}")


    # Extract the first AxonInfo IP:PORT from each entry
    axon_ip_ports = []
    for axon_info in metagraph.axons:
        axon_ip, axon_port = None, None
        if hasattr(axon_info, 'ip') and hasattr(axon_info, 'port'):
            axon_ip = axon_info.ip
            axon_port = axon_info.port
        axon_ip_ports.append(f"{axon_ip}:{axon_port}")

    # Create the DataFrame with extracted Axon IP:PORT
    data = {
        'SUBNET': netuid_int,
        'UID': metagraph.uids,
        'STAKE()': metagraph.stake,
        'RANK': metagraph.ranks,
        'TRUST': metagraph.trust,
        'CONSENSUS': metagraph.consensus,
        'INCENTIVE': metagraph.incentive,
        'DIVIDENDS': metagraph.dividends,
        'EMISSION(ρ)': metagraph.emission,
        'VTRUST': metagraph.validator_trust,
        'VAL': metagraph.validator_permit,
        'UPDATED': metagraph.last_update,
        'ACTIVE': metagraph.active,
        'AXON_IP': axon_ip_ports,
        'HOTKEY': metagraph.hotkeys,
        'COLDKEY': metagraph.coldkeys
    }

    parsed_metagraph = pd.DataFrame(data)
    print(parsed_metagraph)

    return parsed_metagraph


count_hotkeys = 0
count_registered = 0
count_updated = 0
parsed_metagraph = None # Initialize the parsed_metagraph
subtensor = None # Initialize the subtensor
for filename in os.listdir(NINETEEN_REPO_DIRECTORY):
    if filename.endswith(".env"):

        print(f"Processing config file: {filename}")
        # load the config variables from the env 
        
        node_env_path = os.path.join(NINETEEN_REPO_DIRECTORY, filename)
        env_vars = dotenv_values(node_env_path)
        HOTKEY_NAME = env_vars.get('HOTKEY_NAME')
        WALLET_NAME = env_vars.get('WALLET_NAME')
        SUBTENSOR_NETWORK = env_vars.get('SUBTENSOR_NETWORK')
        SUBTENSOR_ADDRESS = env_vars.get('SUBTENSOR_ADDRESS')
        IS_VALIDATOR = env_vars.get('IS_VALIDATOR')
        NODE_PORT = env_vars.get('NODE_PORT')
        NETUID = env_vars.get('NETUID')    

        # load the bittensor key pair from the wallet name and hotkey name
        keypair = load_hotkey_keypair(wallet_name=WALLET_NAME, hotkey_name=HOTKEY_NAME)
        hotkey = keypair.ss58_address
        if hotkey is None:
            print(f"HOTKEY_NAME is not set in {filename}, skipping...")
            continue
        print(f"Loaded hotkey: {hotkey}")
        count_hotkeys += 1

        # get the row from the parsed_metagraph dataframe that matches the hotkey
        if parsed_metagraph is None:
            parsed_metagraph = fetch_metagraph(SUBTENSOR_ADDRESS, NETUID)
        hotkey_row = parsed_metagraph.loc[parsed_metagraph['HOTKEY'] == hotkey]
        print(hotkey_row) 
        
        # if the dataframe is empty then make a note about the hotkey being deregistered and continue
        if hotkey_row.empty:
            print(f"Hotkey: {hotkey} is deregistered")
            continue
        count_registered += 1

        if axon_ip_port := hotkey_row['AXON_IP'].values[0]:
            # Compare the AXON_IP value from the row with the external IP:PORT
            axon_port = NODE_PORT
            if axon_ip_port != f"{NODE_EXTERNAL_IP}:{axon_port}":
                print(f"Hotkey: {hotkey} updating metagraph from {axon_ip_port} to {NODE_EXTERNAL_IP}:{axon_port}")
                #quit() # for testing

                ### USING FIBER API DIRECTLY
                try:
                    print(f"Updating IP using fiber API for hotkey: {hotkey}")
                    
                    # Create substrate connection
                    substrate = interface.get_substrate(
                        subtensor_address=SUBTENSOR_ADDRESS, 
                        subtensor_network=SUBTENSOR_NETWORK
                    )
                    
                    # Load coldkey public key
                    coldkey_keypair_pub = chain_utils.load_coldkeypub_keypair(wallet_name=WALLET_NAME)
                    
                    # Post the IP to the chain
                    success = post_ip_to_chain.post_node_ip_to_chain(
                        substrate=substrate,
                        keypair=keypair,
                        netuid=int(NETUID),
                        external_ip=NODE_EXTERNAL_IP,
                        external_port=int(axon_port),
                        coldkey_ss58_address=coldkey_keypair_pub.ss58_address,
                    )
                    
                    if success:
                        print(f"Successfully updated IP and port on chain for {hotkey}")
                        count_updated += 1
                    else:
                        print(f"Failed to update IP and port on chain for {hotkey}")
                except Exception as e:
                    print(f"Exception occurred while updating IP and port on chain for {hotkey}: {e}")
            else:
                print(f"Hotkey: {hotkey} metagraph {axon_ip_port} matches!")
        else:
            print(f"No matching row found for hotkey: {hotkey}")

# Print the summary
print(f"Total hotkeys: {count_hotkeys}")
print(f"Total registered hotkeys: {count_registered}")
print(f"Total updated hotkeys: {count_updated}")
