import json
import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(description='Calculate points from transfer events JSON file')
    parser.add_argument('input_file', help='Path to the transfer events JSON file')
    parser.add_argument('-o', '--output', default='points.json', help='Output file for points (default: points.json)')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: File '{args.input_file}' not found.")
        sys.exit(1)
    
    # Load the JSON file
    try:
        with open(args.input_file, 'r') as file:
            data = json.load(file)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    # calculate unique blocks

    blocks = set([event['blockNumber'] for event in data['events']])

    # create array of blocks from smallest to largest

    blocks = sorted(blocks)

    print("Number of blocks: ", len(blocks))

    print("Blocks: ")

    print(blocks)

    balances_after_blocks = {}

    state = {}

    for block in blocks:
        balances_after_blocks[block] = state.copy()

        # get all events for this block

        events = [event for event in data['events'] if event['blockNumber'] == block]

        # sort events by transactionIndex

        events = sorted(events, key=lambda x: x['transactionIndex'])

        for event in events:

            value = event['args']['value']

            t_to = event['args']['to']

            if t_to != '0x0000000000000000000000000000000000000000':
                # if not in balances_after_blocks[block], add the address and value
                if t_to not in balances_after_blocks[block]:
                    balances_after_blocks[block][t_to] = value
                else:
                    balances_after_blocks[block][t_to] += value

            t_from = event['args']['from']

            if t_from != '0x0000000000000000000000000000000000000000':

                # print event['args'] 

                print("event: ", event)

                print("block: ", block)
                print(event['args'])
                balances_after_blocks[block][t_from] -= value

        state = balances_after_blocks[block]

    for block in blocks:

        # get all balances for this block

        balances = balances_after_blocks[block]

        print("Balances for block ", block, ": ", balances)

    first_block = blocks[0]

    last_block = blocks[-1]

    print("First block: ", first_block)
    print("Last block: ", last_block)

    # calculate points for each block

    points = {}

    previous_active_block = None

    for block in range(first_block, last_block + 1):

        if block in blocks:
            state = balances_after_blocks[block]
            previous_active_block = block
        else:
            state = balances_after_blocks[previous_active_block]

        for address, value in state.items():

            if address not in points:
                points[address] = 0

            if value > 0:
                points[address] += value

            if value < 0:
                raise Exception("Value is negative")
        
        if block % 1000 == 0:
            print("Points for block calculated: ", block)

    print("Points: ", points)

    # save points to json file

    with open(args.output, 'w') as file:
        json.dump(points, file, indent=2)
    
    print(f"\nPoints saved to {args.output}")

if __name__ == "__main__":
    main()
