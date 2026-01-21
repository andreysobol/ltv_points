from collections import defaultdict
from typing import Dict
from .utils.read_combined_sorted_events import read_combined_sorted_events
from .utils.process_event_above_user_state import (
    process_event_above_user_state,
)
from .utils.get_additional_data import (
    get_start_block_for_day,
    get_end_block_for_day,
    get_day_date,
)
from .utils.get_days_amount import get_days_amount
from .daily_points_v2 import LP_PROGRAM_DURATION_DAYS
from datetime import datetime
from .daily_points_v2 import (
    get_user_state_at_day,
)
from .utils.process_event_above_user_state import UserState
from .daily_points_v2 import load_lp_balances_snapshot_data
import sys


class LpIntegrityChecker:
    def __init__(
        self,
        lp_balances_snapshot: Dict[str, UserState],
        lp_balances_snapshot_start_block: int,
    ):
        self.lp_balances_snapshot = lp_balances_snapshot
        self.lp_balances_snapshot_start_block = lp_balances_snapshot_start_block

    def _validate_lp_integrity(self, users_state, date_unparsed) -> dict[str, bool]:
        date = datetime.fromisoformat(date_unparsed)
        result = defaultdict(bool)
        for address, user_state in users_state.items():
            user_balance = user_state.balance
            if user_state.last_positive_balance_update_day == "":
                if user_balance > 0:
                    raise ValueError(
                        f"User {address} has balance {user_balance} but no last positive balance update day"
                    )
                result[address] = False
                continue
            try:
                lp_entering_day = datetime.fromisoformat(
                    user_state.last_positive_balance_update_day
                )
            except:
                print(
                    f"Error converting {user_state.last_positive_balance_update_day} to datetime"
                )
                print(type(user_state.last_positive_balance_update_day))
                raise 1
            if (date - lp_entering_day).days > LP_PROGRAM_DURATION_DAYS:
                result[address] = False
                continue

            is_integrity_broken = (
                user_balance < self.lp_balances_snapshot[address].balance
            )
            result[address] = is_integrity_broken
        return result

    def _check_lp_integrity_at_day(
        self, day_index, user_to_first_broken_integrity_block
    ) -> Dict[str, int]:
        start_block = get_start_block_for_day(day_index)
        end_block = get_end_block_for_day(day_index)
        block_number_to_events = read_combined_sorted_events(day_index)
        user_state = get_user_state_at_day(day_index, "start_state")
        date_unparsed = get_day_date(day_index)

        # We only need to check blocks after the snapshot start block
        start_block = max(start_block, self.lp_balances_snapshot_start_block)
        for block_number in range(start_block, end_block + 1):
            events = block_number_to_events[block_number]
            for event in events:
                user_state = process_event_above_user_state(
                    event, user_state, date_unparsed
                )

            result = self._validate_lp_integrity(user_state, date_unparsed)
            for address, is_integrity_broken in result.items():
                if is_integrity_broken:
                    print(
                        f"Integrity broken for user {address} at block {block_number}"
                    )
                    if user_to_first_broken_integrity_block[address] == -1:
                        user_to_first_broken_integrity_block[address] = block_number

        return user_to_first_broken_integrity_block

    def _print_user_to_first_broken_integrity_block(
        self, user_to_first_broken_integrity_block
    ):
        if len(user_to_first_broken_integrity_block.keys()) > 0:
            print(
                f"Integrity broken for {len(user_to_first_broken_integrity_block.keys())} users"
            )
            for address, block in user_to_first_broken_integrity_block.items():
                print(
                    f"Integrity broken for user {address} first time at block {block}"
                )
            return 1
        else:
            print("No integrity broken")
            return 0

    def check_lp_integrity(self):
        user_to_first_broken_integrity_block = defaultdict(lambda: -1)
        for day_index in range(0, get_days_amount()):
            print(f"Checking day {day_index}")
            user_to_first_broken_integrity_block = self._check_lp_integrity_at_day(
                day_index, user_to_first_broken_integrity_block
            )
        return self._print_user_to_first_broken_integrity_block(
            user_to_first_broken_integrity_block
        )


if __name__ == "__main__":
    lp_balances_snapshot, lp_balances_snapshot_start_block = (
        load_lp_balances_snapshot_data()
    )
    checker = LpIntegrityChecker(lp_balances_snapshot, lp_balances_snapshot_start_block)
    exit_code = checker.check_lp_integrity()
    sys.exit(exit_code)
