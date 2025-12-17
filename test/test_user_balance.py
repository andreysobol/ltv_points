#!/usr/bin/env python3
import json
import random
import glob
from web3 import Web3
from utils.compare_state_and_onchain_data import compare_state_and_onchain_data

USER_BALANCE_TESTS_AMOUNT = 100

use_state_file = ["52.json"]
use_state_file_index = 0

use_users = ["0xa95584c820b5bc990a0572df4faba7fb9f4e210b"]
picked_users_amount = 0

# ERC20 ABI for balanceOf function
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    }
]

def state_file_has_users(state_file, state_key):
    """Check if a state file has users in pilot_vault.state_key"""
    try:
        with open(state_file, "r") as f:
            state_data = json.load(f)
        pilot_vault_state = state_data.get("pilot_vault", {}).get(state_key, {})
        return bool(pilot_vault_state)
    except Exception:
        return False


def get_random_state_file(state_key):
    """Pick a random state file from data/states directory that has users"""
    state_files = glob.glob("data/states/*.json")
    if not state_files:
        raise ValueError("No state files found in data/states directory")

    global use_state_file_index
    if use_state_file_index < len(use_state_file):
        state_file = use_state_file[use_state_file_index]
        use_state_file_index += 1
        return "data/states/" + state_file
    # Filter to only files with users
    files_with_users = [f for f in state_files if state_file_has_users(f, state_key)]

    if not files_with_users:
        raise ValueError("No state files found with users in pilot_vault.state_key")

    return random.choice(files_with_users)


def get_random_user_from_state(state_data, state_key):
    """Pick a random user from pilot_vault.end_state"""
    pilot_vault_state = state_data.get("pilot_vault", {}).get(state_key, {})
    if not pilot_vault_state:
        return None
    global picked_users_amount
    if picked_users_amount < len(use_users):
        user_address = use_users[picked_users_amount]
        picked_users_amount += 1
    else:
        user_address = random.choice(list(pilot_vault_state.keys()))
    stored_balance = pilot_vault_state[user_address]
    return (user_address, stored_balance)


def get_onchain_balance(w3, state_data, user_data, addresses, block_key):
    """Get balance from contract using balanceOf at specific block"""
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(addresses["pilot_vault"]), abi=ERC20_ABI
    )
    balance = contract.functions.balanceOf(Web3.to_checksum_address(user_data[0])).call(
        block_identifier=state_data[block_key]
    )
    return balance


def validate_balance(user_data, onchain_data, state_data, block_key):
    assert user_data[1] == onchain_data, (
        f"Balance mismatch for user {user_data[0]} at block {state_data[block_key]} (day {state_data['day_index']}):\n"
        f"  Stored balance: {user_data[1]}\n"
        f"  On-chain balance: {onchain_data}\n"
        f"  Difference: {abs(user_data[1] - onchain_data)}"
    )
    print(
        f"✓ Verified balance for user {user_data[0]} at block {state_data[block_key]} (day {state_data['day_index']}): {user_data[1]}"
    )


def test_random_user_balance_end_state():
    compare_state_and_onchain_data(
        USER_BALANCE_TESTS_AMOUNT,
        "test_random_user_balance_end_state",
        lambda *args: get_random_state_file(*args, "end_state"),
        lambda *args: get_random_user_from_state(*args, "end_state"),
        lambda *args: get_onchain_balance(*args, "end_block"),
        lambda user_data, onchain_data, state_data, _1, _2: validate_balance(user_data, onchain_data, state_data, "end_block"),
    )
    
def test_random_user_balance_start_state():
    compare_state_and_onchain_data(
        USER_BALANCE_TESTS_AMOUNT,
        "test_random_user_balance_start_state",
        lambda *args: get_random_state_file(*args, "start_state"),
        lambda *args: get_random_user_from_state(*args, "start_state"),
        lambda *args: get_onchain_balance(*args, "start_block"),
        lambda user_data, onchain_data, state_data, _1, _2: validate_balance(user_data, onchain_data, state_data, "start_block"),
    )
