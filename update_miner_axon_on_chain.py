import os
from pathlib import Path
import ujson as json
import pandas as pd
from substrateinterface import Keypair
import subprocess
import requests
from dotenv import load_dotenv, dotenv_values
import asyncio
from fiber.chain import chain_utils, interface, metagraph, post_ip_to_chain
from fiber.chain.fetch_nodes import get_nodes_for_netuid
import socket
import struct


def load_env_files():
    """Load environment variables"""
    load_dotenv()
    return os.environ.get("NINETEEN_REPO_DIRECTORY")


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


def int_to_ip(ip_int):
    """Convert an integer IP to a human-readable string"""
    try:
        if isinstance(ip_int, int) and ip_int > 0:
            return socket.inet_ntoa(struct.pack('!L', ip_int))
        return '0.0.0.0'
    except Exception:
        return '0.0.0.0'


def fetch_metagraph_using_fiber(subtensor_address, subtensor_network, netuid):
    """
    Fetch the metagraph information using fiber's APIs
    """
    try:
        print(f"Fetching metagraph for netuid {netuid} from subtensor network: {subtensor_address}")
        
        # Create substrate connection
        substrate = interface.get_substrate(
            subtensor_address=subtensor_address, 
            subtensor_network=subtensor_network
        )
        
        # Get nodes using fiber's get_nodes_for_netuid function
        nodes = get_nodes_for_netuid(substrate=substrate, netuid=int(netuid))
        print(f"Found {len(nodes)} nodes")
        
        # Extract only the data we actually need for our DataFrame
        data = {
            'UID': [],
            'AXON_IP': [],
            'HOTKEY': [],
        }
        
        # Extract information from each node
        for node in nodes:
            # We only need UID for display/debugging purposes
            data['UID'].append(getattr(node, 'node_id', 0))
            
            # For axon IP, get IP and port separately and format
            # Handle cases where IP might be an integer
            ip_raw = getattr(node, 'ip', 0)
            ip = int_to_ip(ip_raw) if isinstance(ip_raw, int) else ip_raw
            port = getattr(node, 'port', 0)
            data['AXON_IP'].append(f"{ip}:{port}")
            
            # Hotkey is needed for matching nodes with our local wallets
            data['HOTKEY'].append(str(getattr(node, 'hotkey', '')))
        
        # Create pandas DataFrame
        parsed_metagraph = pd.DataFrame(data)
        
        return parsed_metagraph
        
    except Exception as e:
        print(f"Error fetching metagraph using fiber: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_metagraph_retrieval():
    """
    Test function to verify metagraph retrieval is working
    """
    # Load environment variables from test file
    load_dotenv(".env.test")
    
    # Get test values
    subtensor_network = os.environ.get("SUBTENSOR_NETWORK")
    subtensor_address = os.environ.get("SUBTENSOR_ADDRESS")
    netuid = os.environ.get("NETUID")
    
    print(f"Testing metagraph retrieval with:")
    print(f"  Network: {subtensor_network}")
    print(f"  Address: {subtensor_address}")
    print(f"  NetUID: {netuid}")
    
    # Fetch metagraph
    try:
        metagraph_df = fetch_metagraph_using_fiber(
            subtensor_address=subtensor_address,
            subtensor_network=subtensor_network,
            netuid=netuid
        )
        
        # Print summary information
        print("\nMetagraph Summary:")
        print(f"Total nodes found: {len(metagraph_df)}")
        
        # Show the dataframe column names and a few rows
        print("\nDataFrame columns:", metagraph_df.columns.tolist())
        print("\nSample data (first 5 rows):")
        print(metagraph_df.head(5))
        
        # Print axon info for the first 5 nodes
        print("\nAxon info for sample nodes:")
        for idx, row in metagraph_df.head(5).iterrows():
            hotkey_str = str(row['HOTKEY'])
            # Truncate hotkey if it's longer than 10 chars
            hotkey_display = hotkey_str[:10] + "..." if len(hotkey_str) > 10 else hotkey_str
            print(f"UID: {row['UID']}, Hotkey: {hotkey_display}, Axon: {row['AXON_IP']}")
            
        print("\nTest completed successfully!")
        return True
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        return False


def main():
    """
    Main function to run the script
    """
    # Load environment variables
    NINETEEN_REPO_DIRECTORY = load_env_files()
    NODE_EXTERNAL_IP = requests.get('https://ipinfo.io/json').json()['ip']
    
    count_hotkeys = 0
    count_registered = 0
    count_updated = 0
    parsed_metagraph = None  # Initialize the parsed_metagraph
    
    # Check if NINETEEN_REPO_DIRECTORY exists
    if not NINETEEN_REPO_DIRECTORY:
        print("Error: NINETEEN_REPO_DIRECTORY environment variable not set")
        return
    
    if not os.path.exists(NINETEEN_REPO_DIRECTORY):
        print(f"Error: Directory {NINETEEN_REPO_DIRECTORY} does not exist")
        return
    
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
            try:
                keypair = load_hotkey_keypair(wallet_name=WALLET_NAME, hotkey_name=HOTKEY_NAME)
                hotkey = keypair.ss58_address
                if hotkey is None:
                    print(f"HOTKEY_NAME is not set in {filename}, skipping...")
                    continue
                print(f"Loaded hotkey: {hotkey}")
                count_hotkeys += 1
            except Exception as e:
                print(f"Error loading hotkey {HOTKEY_NAME} for wallet {WALLET_NAME}: {e}")
                continue

            # get the row from the parsed_metagraph dataframe that matches the hotkey
            if parsed_metagraph is None:
                parsed_metagraph = fetch_metagraph_using_fiber(SUBTENSOR_ADDRESS, SUBTENSOR_NETWORK, NETUID)
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


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update miner axon IP on chain")
    parser.add_argument('--test', action='store_true', help='Run in test mode to verify metagraph retrieval')
    
    args = parser.parse_args()
    
    if args.test:
        test_metagraph_retrieval()
    else:
        main()
