from datetime import datetime
from utils.process_event_above_user_state import (
    UserState,
    process_event_above_user_state,
)
from utils.read_combined_sorted_events import read_combined_sorted_events
import json
import glob
from collections import defaultdict
import os
import copy
from utils.get_days_amount import get_days_amount
from utils.get_additional_data import get_start_block_for_day, get_end_block_for_day, get_day_date

class DailyState:
    def __init__(
        self,
        day_index: int = None,
        date: datetime = None,
        start_block: int = None,
        end_block: int = None,
        user_state: dict[str, UserState] = None,
    ):
        self.day_index = day_index
        self.date = date
        self.start_block = start_block
        self.end_block = end_block
        self.user_state = user_state

def calculate_daily_state_after_end_block(
    day_index: int, users_state_before_start_block: dict[str, UserState]
):
    user_state = users_state_before_start_block

    block_number_to_events = read_combined_sorted_events(day_index)
    start_block = get_start_block_for_day(day_index)
    end_block = get_end_block_for_day(day_index)

    for block_number in range(start_block, end_block + 1):
        events = block_number_to_events[block_number]
        for event in events:
            user_state = process_event_above_user_state(event, user_state)
            
    return DailyState(
        day_index=day_index,
        date=get_day_date(day_index),
        start_block=start_block,
        end_block=end_block,
        user_state=user_state,
    )


def write_user_state_to_file(
    daily_state_after_end_block: DailyState,
    user_state_before_start_block: dict[str, UserState],
):
    daily_balances_after_end_block = {
        address.lower(): state.balance
        for address, state in daily_state_after_end_block.user_state.items() if state.balance > 0
    }
    daily_nft_ids_after_end_block = {
        address.lower(): list(state.nft_ids)
        for address, state in daily_state_after_end_block.user_state.items() if len(state.nft_ids) > 0
    }
    daily_balances_before_start_block = {
        address.lower(): state.balance
        for address, state in user_state_before_start_block.items() if state.balance > 0
    }
    daily_nft_ids_before_start_block = {
        address.lower(): list(state.nft_ids)
        for address, state in user_state_before_start_block.items() if len(state.nft_ids) > 0
    }

    os.makedirs(os.path.dirname(f"data/states2.0/"), exist_ok=True)
    with open(f"data/states/{daily_state_after_end_block.day_index}.json", "w") as f:
        json.dump(
            {
                "start_block": daily_state_after_end_block.start_block,
                "end_block": daily_state_after_end_block.end_block,
                "date": daily_state_after_end_block.date,
                "day_index": daily_state_after_end_block.day_index,
                "nft": {
                    "start_state": daily_nft_ids_before_start_block,
                    "end_state": daily_nft_ids_after_end_block,
                },
                "pilot_vault": {
                    "start_state": daily_balances_before_start_block,
                    "end_state": daily_balances_after_end_block,
                },
            },
            f,
            indent=2,
        )


def process_daily_states():
    days_amount = get_days_amount()
    user_state_before_start_block = defaultdict(UserState)
    for day_index in range(days_amount):
        daily_state = calculate_daily_state_after_end_block(
            day_index, copy.deepcopy(user_state_before_start_block)
        )
        write_user_state_to_file(daily_state, user_state_before_start_block)
        user_state_before_start_block = daily_state.user_state


process_daily_states()
