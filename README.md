# Points Calculator

A Python toolset for fetching Transfer events from Ethereum smart contracts and calculating points based on token balances over time.

## Overview

This project consists of two main scripts:

1. **`fetch_transfer_events.py`** - Fetches Transfer events from a blockchain contract within a specified block range
2. **`calculate_points.py`** - Processes transfer events and calculates points based on token balances over time

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ltv_points
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Requirements

- Python 3.7+
- web3.py (>=6.0.0)

## Usage

### Fetching Transfer Events

The `fetch_transfer_events.py` script fetches Transfer events from a blockchain contract.

#### Basic Usage

```bash
# Fetch events from a specific block range
python fetch_transfer_events.py 7759278 8000000

# Fetch events from a start block to the latest block
python fetch_transfer_events.py 7759278

# Specify custom output file
python fetch_transfer_events.py 7759278 --end-block 8000000 -o my_events.json
```

#### Command-Line Arguments

- `start_block` (required): Starting block number
- `--end-block` (optional): Ending block number (defaults to latest block if not provided)
- `--rpc-url` (optional): RPC provider URL (default: Sepolia testnet RPC)
- `--contract-address` (optional): Contract address (default: configured contract)
- `-o, --output` (optional): Output JSON file (default: `transfer_events_TIMESTAMP.json`)
- `--chunk-size` (optional): Chunk size for fetching events (default: 10000)

#### Examples

```bash
# Use custom RPC endpoint
python fetch_transfer_events.py 7759278 --rpc-url https://your-rpc-url.com

# Use custom contract address
python fetch_transfer_events.py 7759278 --contract-address 0xYourContractAddress

# Adjust chunk size for rate limiting
python fetch_transfer_events.py 7759278 --chunk-size 5000
```

#### Output Format

The script generates a JSON file with the following structure:

```json
{
  "metadata": {
    "contractAddress": "0x...",
    "eventName": "Transfer",
    "startBlock": 7759278,
    "endBlock": 8000000,
    "totalEvents": 1234,
    "exportedAt": "2025-11-24T14:19:10"
  },
  "events": [
    {
      "blockNumber": 7759278,
      "transactionHash": "0x...",
      "logIndex": 0,
      "args": {
        "from": "0x...",
        "to": "0x...",
        "value": 1000000000000000000
      },
      "transactionIndex": 0
    }
  ]
}
```

### Calculating Points

The `calculate_points.py` script processes transfer events and calculates points based on token balances over time.

#### Basic Usage

```bash
# Calculate points from transfer events file
python calculate_points.py transfer_events_20251124_135052.json

# Specify custom output file
python calculate_points.py transfer_events_20251124_135052.json -o my_points.json
```

#### Command-Line Arguments

- `input_file` (required): Path to the transfer events JSON file
- `-o, --output` (optional): Output file for points (default: `points.json`)

#### How Points Are Calculated

1. The script processes all transfer events in chronological order (by block number and transaction index)
2. For each block, it calculates token balances for all addresses
3. Points are accumulated for each address based on their token balance in each block
4. The final points represent the sum of all token balances across all blocks

#### Output Format

The script generates a JSON file mapping addresses to their total points:

```json
{
  "0xAddress1": 1234567890000000000,
  "0xAddress2": 9876543210000000000
}
```

## Workflow Example

1. **Fetch transfer events:**
```bash
python fetch_transfer_events.py 7759278 8000000 -o events.json
```

2. **Calculate points:**
```bash
python calculate_points.py events.json -o points.json
```

## Configuration

### Default Settings

The scripts use the following defaults (configurable via command-line arguments):

- **RPC URL**: `https://eth-sepolia-testnet.rpc.grove.city/v1/01fdb492`
- **Contract Address**: `0xe2a7f267124ac3e4131f27b9159c78c521a44f3c`
- **Chunk Size**: 10000 blocks

## Error Handling

- The fetch script automatically retries with smaller chunk sizes if RPC limits are hit
- Both scripts validate input files and provide clear error messages
- Connection errors are handled gracefully with informative messages

## Notes

- JSON files are ignored by git (see `.gitignore`)
- The scripts include rate limiting to avoid overwhelming RPC providers
- Large block ranges may take significant time to process