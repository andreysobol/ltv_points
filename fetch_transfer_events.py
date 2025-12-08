from web3 import Web3
import time
import json
import argparse
import sys
from datetime import datetime

# Default configuration
DEFAULT_PROVIDER_URL = "https://eth-sepolia-testnet.rpc.grove.city/v1/01fdb492"
DEFAULT_CONTRACT_ADDRESS = "0xe2a7f267124ac3e4131f27b9159c78c521a44f3c"

# ABI for Transfer event
TRANSFER_EVENT_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    }
]

def get_latest_block(w3):
    """Get the latest block number"""
    try:
        return w3.eth.block_number
    except Exception as e:
        print(f"Error getting latest block: {e}")
        return None

def read_events_chunked(contract, event_name="Transfer", start_block=0, end_block=None, chunk_size=10000, w3=None):
    """
    Read events in chunks to avoid RPC limits
    """
    if end_block is None:
        if w3 is None:
            print("Error: w3 provider required when end_block is None")
            return None
        end_block = get_latest_block(w3)
        if end_block is None:
            print("Could not get latest block number")
            return None
    
    print(f"Reading {event_name} events from block {start_block} to {end_block}")
    
    event = getattr(contract.events, event_name)
    all_logs = []
    
    current_block = start_block
    
    while current_block <= end_block:
        chunk_end = min(current_block + chunk_size - 1, end_block)
        
        try:
            print(f"Fetching logs from block {current_block} to {chunk_end}...")
            logs = event().get_logs(from_block=current_block, to_block=chunk_end)
            all_logs.extend(logs)
            print(f"Found {len(logs)} events in this chunk")
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error fetching logs from block {current_block} to {chunk_end}: {e}")
            # Try smaller chunk size if we get an error
            if chunk_size > 1000:
                print(f"Retrying with smaller chunk size: {chunk_size // 2}")
                return read_events_chunked(contract, event_name, current_block, end_block, chunk_size // 2, w3)
            else:
                print("Skipping this chunk due to persistent error")
        
        current_block = chunk_end + 1
    
    return all_logs

def read_all_events(contract, contract_address, event_name="Transfer", start_block=0, end_block=None, output_file=None, w3=None, chunk_size=10000):
    """
    Read all events with proper error handling and save to JSON
    """
    try:
        logs = read_events_chunked(contract, event_name, start_block, end_block, chunk_size=chunk_size, w3=w3)
        if logs is None:
            return
            
        print(f"Total {event_name} events: {len(logs)}")

        # Prepare data for JSON output
        events_data = []
        for log in logs:
            event_data = {
                "blockNumber": log.blockNumber,
                "transactionHash": log.transactionHash.hex(),
                "logIndex": log.logIndex,
                "args": dict(log.args),
                "transactionIndex": log.transactionIndex
            }
            events_data.append(event_data)
            print(event_data)  # Still print for console output

        # Save to JSON file if output_file is specified
        if output_file:
            output_data = {
                "metadata": {
                    "contractAddress": contract_address,
                    "eventName": event_name,
                    "startBlock": start_block,
                    "endBlock": end_block,
                    "totalEvents": len(events_data),
                    "exportedAt": datetime.now().isoformat()
                },
                "events": events_data
            }
            
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"\nEvents saved to {output_file}")
            
    except Exception as e:
        print(f"Error reading events: {e}")

def main():
    parser = argparse.ArgumentParser(
        description='Fetch Transfer events from a blockchain contract',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fetch_transfer_events.py 7759278 8000000
  python fetch_transfer_events.py 7759278 --end-block 8000000
  python fetch_transfer_events.py 7759278 --output my_events.json
  python fetch_transfer_events.py 7759278 --rpc-url https://eth-sepolia-testnet.rpc.grove.city/v1/01fdb492
        """
    )
    parser.add_argument('start_block', type=int, help='Starting block number')
    parser.add_argument('--end-block', type=int, default=None, 
                       help='Ending block number (default: latest block)')
    parser.add_argument('--rpc-url', type=str, default=DEFAULT_PROVIDER_URL,
                       help=f'RPC provider URL (default: {DEFAULT_PROVIDER_URL})')
    parser.add_argument('--contract-address', type=str, default=DEFAULT_CONTRACT_ADDRESS,
                       help=f'Contract address (default: {DEFAULT_CONTRACT_ADDRESS})')
    parser.add_argument('-o', '--output', type=str, default=None,
                       help='Output JSON file (default: transfer_events_TIMESTAMP.json)')
    parser.add_argument('--chunk-size', type=int, default=10000,
                       help='Chunk size for fetching events (default: 10000)')
    
    args = parser.parse_args()
    
    # Validate start block
    if args.start_block < 0:
        print("Error: start_block must be non-negative")
        sys.exit(1)
    
    # Validate end block if provided
    if args.end_block is not None and args.end_block < args.start_block:
        print("Error: end_block must be greater than or equal to start_block")
        sys.exit(1)
    
    # Initialize Web3 connection
    try:
        w3 = Web3(Web3.HTTPProvider(args.rpc_url))
        if not w3.is_connected():
            print(f"Error: Could not connect to RPC provider at {args.rpc_url}")
            sys.exit(1)
    except Exception as e:
        print(f"Error connecting to RPC provider: {e}")
        sys.exit(1)
    
    # Setup contract
    try:
        contract_address = Web3.to_checksum_address(args.contract_address)
        contract = w3.eth.contract(address=contract_address, abi=TRANSFER_EVENT_ABI)
    except Exception as e:
        print(f"Error setting up contract: {e}")
        sys.exit(1)
    
    # Get end block if not provided
    end_block = args.end_block
    if end_block is None:
        end_block = get_latest_block(w3)
        if end_block is None:
            print("Could not get latest block number")
            sys.exit(1)
    
    print(f"Fetching Transfer events from block {args.start_block} to {end_block}")
    print(f"Contract address: {contract_address}")
    print(f"RPC URL: {args.rpc_url}")
    
    # Generate output filename if not provided
    output_file = args.output
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"transfer_events_{timestamp}.json"
    
    # Fetch events
    read_all_events(
        contract=contract,
        contract_address=contract_address,
        event_name="Transfer",
        start_block=args.start_block,
        end_block=end_block,
        output_file=output_file,
        w3=w3,
        chunk_size=args.chunk_size
    )

if __name__ == "__main__":
    main()