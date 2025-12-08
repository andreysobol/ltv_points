from web3 import Web3
import argparse
import sys
from datetime import datetime, timedelta, timezone
import json

# Default configuration
#DEFAULT_PROVIDER_URL = "https://eth-sepolia-testnet.rpc.grove.city/v1/01fdb492"
DEFAULT_PROVIDER_URL = "https://mainnet.gateway.tenderly.co"

# Ethereum blocks per day heuristic: 5 blocks/min * 60 min/hour * 24 hours/day
BLOCKS_PER_DAY = 5 * 60 * 24  # 7200 blocks per day


def get_block_timestamp(w3, block_number):
    """Get the timestamp of a specific block"""
    try:
        block = w3.eth.get_block(block_number)
        return block.timestamp
    except Exception as e:
        print(f"Error getting block {block_number}: {e}")
        return None


def binary_search_block_by_timestamp(w3, target_timestamp, start_block, end_block, find_first=True):
    """
    Use binary search to find a block with a specific timestamp.
    
    Args:
        w3: Web3 instance
        target_timestamp: Target timestamp to find
        start_block: Starting block number for search
        end_block: Ending block number for search
        find_first: If True, find first block >= timestamp, else find last block <= timestamp
    
    Returns:
        Block number that matches the criteria
    """
    left = start_block
    right = end_block
    result = None
    
    while left <= right:
        mid = (left + right) // 2
        mid_timestamp = get_block_timestamp(w3, mid)
        
        if mid_timestamp is None:
            # If we can't get the block, try to narrow the search
            if find_first:
                left = mid + 1
            else:
                right = mid - 1
            continue
        
        if find_first:
            # Find first block with timestamp >= target
            if mid_timestamp >= target_timestamp:
                result = mid
                right = mid - 1
            else:
                left = mid + 1
        else:
            # Find last block with timestamp <= target
            if mid_timestamp <= target_timestamp:
                result = mid
                left = mid + 1
            else:
                right = mid - 1
    
    return result


def find_first_block_of_day(w3, day_start_timestamp, search_start_block, search_end_block):
    """Find the first block of a day (first block with timestamp >= day_start)"""
    return binary_search_block_by_timestamp(
        w3, day_start_timestamp, search_start_block, search_end_block, find_first=True
    )


def find_last_block_of_day(w3, day_end_timestamp, search_start_block, search_end_block):
    """Find the last block of a day (last block with timestamp <= day_end)"""
    return binary_search_block_by_timestamp(
        w3, day_end_timestamp, search_start_block, search_end_block, find_first=False
    )


def get_day_boundaries(date):
    """Get start and end timestamps for a given date (UTC)"""
    # Start of day (00:00:00 UTC)
    day_start = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
    # End of day (23:59:59 UTC)
    day_end = datetime.combine(date, datetime.max.time()).replace(tzinfo=timezone.utc)
    # Add 1 second to include the last second of the day
    day_end = day_end.replace(second=59, microsecond=999999)
    
    return int(day_start.timestamp()), int(day_end.timestamp())


def find_blocks_for_date_range(w3, start_date, end_date, latest_block, latest_block_timestamp):
    """
    Find first and last blocks for each day in a date range.
    
    Args:
        w3: Web3 instance
        start_date: Start date (datetime.date)
        end_date: End date (datetime.date)
        latest_block: Latest block number from blockchain
        latest_block_timestamp: Timestamp of the latest block
    
    Returns:
        List of dictionaries with date, first_block, and last_block
    """
    results = []
    current_date = start_date
    
    # Calculate estimated start block using heuristics
    # Get end date timestamp (end of day)
    _, end_date_ts = get_day_boundaries(end_date)
    days_between = (end_date - start_date).days + 1  # +1 to include both start and end dates
    
    # Estimate start block: latest_block - (days * blocks_per_day)
    # Add some margin for safety
    estimated_start_block = max(0, latest_block - (days_between * BLOCKS_PER_DAY * 2))
    
    # Get the actual start block by finding the block closest to start_date
    day_start_ts, _ = get_day_boundaries(start_date)
    
    # Binary search to find a block near the start date
    # Search from estimated_start_block to latest_block
    print(f"Estimating start block for {start_date}...")
    initial_start_block = binary_search_block_by_timestamp(
        w3, day_start_ts, estimated_start_block, latest_block, find_first=True
    )
    
    if initial_start_block is None:
        # Fallback: use estimated block
        initial_start_block = estimated_start_block
        print(f"Warning: Could not find exact start block, using estimated: {initial_start_block}")
    else:
        # Get a bit earlier to ensure we cover the start date
        initial_start_block = max(0, initial_start_block - BLOCKS_PER_DAY)
    
    initial_start_ts = get_block_timestamp(w3, initial_start_block)
    
    if initial_start_ts is None:
        print("Error: Could not get timestamp for initial start block")
        return results
    
    print(f"Block range: {initial_start_block} (ts: {initial_start_ts}, {datetime.fromtimestamp(initial_start_ts, tz=timezone.utc)}) to {latest_block} (ts: {latest_block_timestamp}, {datetime.fromtimestamp(latest_block_timestamp, tz=timezone.utc)})")
    
    # Track search bounds for optimization
    search_start = initial_start_block
    search_end = latest_block
    
    while current_date <= end_date:
        day_start_ts, day_end_ts = get_day_boundaries(current_date)
        
        # Skip if day is before or after our block range
        if day_end_ts < initial_start_ts:
            print(f"Skipping {current_date}: before block range")
            current_date += timedelta(days=1)
            continue
        if day_start_ts > latest_block_timestamp:
            print(f"Skipping {current_date}: after latest block")
            current_date += timedelta(days=1)
            continue
        
        print(f"\nFinding blocks for {current_date}...")
        print(f"  Day range: {datetime.fromtimestamp(day_start_ts, tz=timezone.utc)} to {datetime.fromtimestamp(day_end_ts, tz=timezone.utc)}")
        
        # Optimize search bounds: use heuristic to narrow search
        # Estimate block number based on blocks per day
        days_from_start = (current_date - start_date).days
        estimated_block = initial_start_block + (days_from_start * BLOCKS_PER_DAY)
        
        # Set search bounds with some margin
        day_search_start = max(initial_start_block, estimated_block - BLOCKS_PER_DAY)
        day_search_end = min(latest_block, estimated_block + BLOCKS_PER_DAY)
        
        # Use previous day's last block as a better starting point if available
        if results:
            day_search_start = max(day_search_start, results[-1]['last_block'])
        
        print(f"  Searching in block range: {day_search_start} to {day_search_end}")
        
        # Find first block of the day
        first_block = find_first_block_of_day(w3, day_start_ts, day_search_start, day_search_end)
        
        if first_block is None:
            print(f"  Warning: Could not find first block for {current_date}")
            current_date += timedelta(days=1)
            continue
        
        # Find last block of the day (search from first_block to end of day range)
        last_block = find_last_block_of_day(w3, day_end_ts, first_block, day_search_end)
        
        if last_block is None:
            print(f"  Warning: Could not find last block for {current_date}, using first_block")
            last_block = first_block
        
        # Verify the blocks
        first_ts = get_block_timestamp(w3, first_block)
        last_ts = get_block_timestamp(w3, last_block)
        
        print(f"  First block: {first_block} (timestamp: {first_ts}, {datetime.fromtimestamp(first_ts, tz=timezone.utc) if first_ts else 'N/A'})")
        print(f"  Last block: {last_block} (timestamp: {last_ts}, {datetime.fromtimestamp(last_ts, tz=timezone.utc) if last_ts else 'N/A'})")
        
        results.append({
            'date': current_date.isoformat(),
            'first_block': first_block,
            'last_block': last_block,
            'first_block_timestamp': first_ts,
            'last_block_timestamp': last_ts
        })
        
        # Update search bounds for next iteration
        search_start = last_block
        
        current_date += timedelta(days=1)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Find first and last blocks for each day using binary search',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python find_daily_blocks.py 2025-11-01 2025-11-30
  python find_daily_blocks.py 2025-11-01 2025-11-30 -o daily_blocks.json
  python find_daily_blocks.py 2025-11-01 2025-11-30 --rpc-url https://mainnet.gateway.tenderly.co
        """
    )
    parser.add_argument('start_date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('end_date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--rpc-url', type=str, default=DEFAULT_PROVIDER_URL,
                       help=f'RPC provider URL (default: {DEFAULT_PROVIDER_URL})')
    parser.add_argument('-o', '--output', type=str, default=None,
                       help='Output JSON file (default: daily_blocks_TIMESTAMP.json)')
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
    except ValueError as e:
        print(f"Error: Invalid date format. Use YYYY-MM-DD format. {e}")
        sys.exit(1)
    
    if start_date > end_date:
        print("Error: start_date must be before or equal to end_date")
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
    
    # Get latest block from blockchain
    print("Fetching latest block from blockchain...")
    try:
        latest_block = w3.eth.block_number
        latest_block_data = w3.eth.get_block(latest_block)
        latest_block_timestamp = latest_block_data.timestamp
        latest_block_date = datetime.fromtimestamp(latest_block_timestamp, tz=timezone.utc).date()
        
        print(f"Latest block: {latest_block}")
        print(f"Latest block timestamp: {latest_block_timestamp} ({datetime.fromtimestamp(latest_block_timestamp, tz=timezone.utc)})")
        print(f"Latest block date: {latest_block_date}")
    except Exception as e:
        print(f"Error getting latest block: {e}")
        sys.exit(1)
    
    # Check if end_date is in the future
    if end_date > latest_block_date:
        print(f"Warning: end_date ({end_date}) is after latest block date ({latest_block_date})")
        print(f"Using {latest_block_date} as the effective end date")
        end_date = min(end_date, latest_block_date)
    
    print(f"\nFinding blocks for date range: {start_date} to {end_date}")
    print(f"RPC URL: {args.rpc_url}")
    print(f"Using heuristic: ~{BLOCKS_PER_DAY} blocks per day\n")
    
    # Find blocks for each day
    results = find_blocks_for_date_range(
        w3, start_date, end_date, latest_block, latest_block_timestamp
    )
    
    if not results:
        print("\nNo blocks found for the specified date range")
        sys.exit(1)
    
    # Prepare output
    output_data = {
        'metadata': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'latest_block': latest_block,
            'latest_block_timestamp': latest_block_timestamp,
            'rpc_url': args.rpc_url,
            'total_days': len(results),
            'generated_at': datetime.now(timezone.utc).isoformat()
        },
        'daily_blocks': results
    }
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Summary: Found blocks for {len(results)} days")
    print(f"{'='*60}")
    print(f"{'Date':<12} {'First Block':<15} {'Last Block':<15} {'Blocks':<10}")
    print(f"{'-'*60}")
    for day_data in results:
        block_count = day_data['last_block'] - day_data['first_block'] + 1
        print(f"{day_data['date']:<12} {day_data['first_block']:<15} {day_data['last_block']:<15} {block_count:<10}")
    
    # Save to file
    output_file = args.output
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"daily_blocks_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()

