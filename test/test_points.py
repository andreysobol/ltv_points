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