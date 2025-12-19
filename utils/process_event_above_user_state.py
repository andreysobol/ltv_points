from typing import Dict
from utils.event_type import EventType

ZERO_ADDRESS = "0x" + "0" * 40


class UserState:
    def __init__(self, balance: int = 0, nft_ids: set[int] = None):
        self.balance = balance
        self.nft_ids = nft_ids if nft_ids is not None else set()
        self.last_positive_balance_update_block = 0
        self.last_negative_balance_update_block = 0


def process_transfer_event(event, user_state) -> UserState:
    value = event["args"]["value"]
    from_addr = event["args"]["from"].lower()
    to_addr = event["args"]["to"].lower()
    if from_addr != ZERO_ADDRESS:
        user_state[from_addr].balance -= value
        user_state[from_addr].last_negative_balance_update_block = event["blockNumber"]
    if to_addr != ZERO_ADDRESS:
        user_state[to_addr].balance += value
        user_state[to_addr].last_positive_balance_update_block = event["blockNumber"]
    return user_state


def process_nft_event(event, user_state) -> UserState:
    token_id = event["args"]["tokenId"]
    from_addr = event["args"]["from"].lower()
    to_addr = event["args"]["to"].lower()
    if from_addr != ZERO_ADDRESS:
        user_state[from_addr].nft_ids.discard(token_id)
    if to_addr != ZERO_ADDRESS:
        user_state[to_addr].nft_ids.add(token_id)
    return user_state


def process_event_above_user_state(event, user_state) -> UserState:
    if event["event_type"] == EventType.TRANSFER:
        return process_transfer_event(event, user_state)
    elif event["event_type"] == EventType.NFT:
        return process_nft_event(event, user_state)
    else:
        raise ValueError(f"Invalid event type: {event['event_type']}")
