from test_states import load_states_sorted
from pathlib import Path
import json

DATA_DIR = Path("data")


def load_points_sorted():
    points_dir = DATA_DIR / "points"
    points = sorted(points_dir.glob("*.json"), key=lambda f: int(f.stem))
    return [json.loads(f.read_text()) for f in points]


class TestPoints:
    def test_points_borders_match_states_borders(self):
        points = load_points_sorted()
        states = load_states_sorted()
        for point, state in zip(points, states):
            assert (
                point["start_block"] == state["start_block"]
            ), f"Day {point['day_index']} point start block {point['start_block']} does not match state start block {state['start_block']}"
            assert (
                point["end_block"] == state["end_block"]
            ), f"Day {point['day_index']} point end block {point['end_block']} does not match state end block {state['end_block']}"
            assert (
                point["date"] == state["date"]
            ), f"Day {point['day_index']} point date {point['date']} does not match state date {state['date']}"

    def test_points_without_daily_change(self):
        points = load_points_sorted()
        states = load_states_sorted()

        point = points[51]
        state = states[51]

        user = "0x91a98fd033434adf63223f88064c95a89e08061c"
        points_per_one_wei = (point["end_block"] - point["start_block"] + 1) * 1000
        expected_points = state["pilot_vault"]["end_state"][user] * points_per_one_wei

        assert (
            expected_points == point["points"][user]
        ), f"Expected points for user {user} without nft and balance change does not match calculated points: {expected_points} != {point['points'][user]}"

    def test_user_balance_changed(self):
        points = load_points_sorted()
        states = load_states_sorted()

        point = points[51]
        state = states[51]

        user = "0x202065dfb813295d0b095a39e36e3b3296210505"

        event_block_number = 23799902
        user_balance_before = state["pilot_vault"]["start_state"][user]
        balance_increase = 611108746658861

        expected_points = (
            user_balance_before * 1000 * (event_block_number - state["start_block"])
        )
        expected_points += (
            (user_balance_before + balance_increase)
            * 1000
            * (point["end_block"] - event_block_number + 1)
        )

        assert (
            expected_points == point["points"][user]
        ), f"Expected points for user {user} without nft but with balance change does not match calculated points: {expected_points} != {point['points'][user]}"

    def test_nft_balance_changed(self):
        points = load_points_sorted()
        states = load_states_sorted()

        point = points[77]
        state = states[77]

        user = "0xC3cB47f1d74abc82Cc9acd748c9C6714F9c77EFF".lower()
        event_block_number = 23983629
        start_block = state["start_block"]
        end_block = state["end_block"]
        balance = state["pilot_vault"]["start_state"][user]
        expected_points = balance * 1000 * (event_block_number - start_block)
        expected_points += balance * 1420 * (end_block - event_block_number + 1)
        assert (
            expected_points == point["points"][user]
        ), f"Expected points for user {user} with nft balance change but without balance change does not match calculated points: {expected_points} != {point['points'][user]}"
