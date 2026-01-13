from collections import defaultdict
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

# Add parent directory to path to import modules
# sys.path.insert(0, str(Path(__file__).parent.parent))
from src.check_lp_integrity import LpIntegrityChecker
from src.utils.process_event_above_user_state import UserState
from src.daily_points_v2 import LP_PROGRAM_DURATION_DAYS


class TestValidateLpIntegrity:
    def test_balance_above_snapshot_no_integrity_issue(self):
        """Test that balance above snapshot does not indicate integrity issue"""
        snapshot_entry = UserState(balance=100)
        snapshot_entry.last_positive_balance_update_day = "2026-01-01"
        lp_balances_snapshot = {
            "0x1111111111111111111111111111111111111111": snapshot_entry
        }
        checker = LpIntegrityChecker(lp_balances_snapshot, 0)

        user_state = {
            "0x1111111111111111111111111111111111111111": UserState(balance=500)
        }
        user_state["0x1111111111111111111111111111111111111111"].last_positive_balance_update_day = "2026-01-01"
        date = "2026-01-15"  # Within 90 days

        result = checker._validate_lp_integrity(user_state, date)

        assert result["0x1111111111111111111111111111111111111111"] == False  # No integrity issue

    def test_balance_below_snapshot_integrity_broken(self):
        """Test that balance below snapshot indicates integrity issue"""
        snapshot_entry = UserState(balance=500)
        snapshot_entry.last_positive_balance_update_day = "2026-01-01"
        lp_balances_snapshot = {
            "0x2222222222222222222222222222222222222222": snapshot_entry
        }
        checker = LpIntegrityChecker(lp_balances_snapshot, 0)

        user_state = {
            "0x2222222222222222222222222222222222222222": UserState(balance=300)
        }
        user_state["0x2222222222222222222222222222222222222222"].last_positive_balance_update_day = "2026-01-01"
        date = "2026-01-15"  # Within 90 days

        result = checker._validate_lp_integrity(user_state, date)

        assert result["0x2222222222222222222222222222222222222222"] == True  # Integrity broken

    def test_balance_equal_to_snapshot_no_integrity_issue(self):
        """Test that balance equal to snapshot does not indicate integrity issue"""
        snapshot_entry = UserState(balance=300)
        snapshot_entry.last_positive_balance_update_day = "2026-01-01"
        lp_balances_snapshot = {
            "0x3333333333333333333333333333333333333333": snapshot_entry
        }
        checker = LpIntegrityChecker(lp_balances_snapshot, 0)

        user_state = {
            "0x3333333333333333333333333333333333333333": UserState(balance=300)
        }
        user_state["0x3333333333333333333333333333333333333333"].last_positive_balance_update_day = "2026-01-01"
        date = "2026-01-15"  # Within 90 days

        result = checker._validate_lp_integrity(user_state, date)

        assert result["0x3333333333333333333333333333333333333333"] == False  # No integrity issue

    def test_user_outside_90_day_period_not_checked(self):
        """Test that users outside 90-day period are not checked"""
        snapshot_entry = UserState(balance=100)
        snapshot_entry.last_positive_balance_update_day = "2026-01-01"
        lp_balances_snapshot = {
            "0x4444444444444444444444444444444444444444": snapshot_entry
        }
        checker = LpIntegrityChecker(lp_balances_snapshot, 0)

        user_state = {
            "0x4444444444444444444444444444444444444444": UserState(balance=50)  # Below snapshot
        }
        user_state["0x4444444444444444444444444444444444444444"].last_positive_balance_update_day = "2026-01-01"
        # Date is more than 90 days after last update
        last_update_date = datetime(2026, 1, 1).date()
        current_date = last_update_date + timedelta(days=LP_PROGRAM_DURATION_DAYS + 10)
        date = str(current_date)

        result = checker._validate_lp_integrity(user_state, date)

        # Should not be checked (returns False, meaning no integrity issue to check)
        assert result["0x4444444444444444444444444444444444444444"] == False

    def test_user_empty_last_update_day_with_balance_raises_error(self):
        """Test that user with empty last_positive_balance_update_day and balance > 0 raises error"""
        snapshot_entry = UserState(balance=100)
        snapshot_entry.last_positive_balance_update_day = "2026-01-01"
        lp_balances_snapshot = {
            "0x5555555555555555555555555555555555555555": snapshot_entry
        }
        checker = LpIntegrityChecker(lp_balances_snapshot, 0)

        user_state = {
            "0x5555555555555555555555555555555555555555": UserState(balance=200)
        }
        user_state["0x5555555555555555555555555555555555555555"].last_positive_balance_update_day = ""
        date = "2026-01-15"

        try:
            checker._validate_lp_integrity(user_state, date)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "balance" in str(e).lower()
            assert "last positive balance update day" in str(e).lower()

    def test_multiple_users_mixed_scenarios(self):
        """Test multiple users with different scenarios"""
        snapshot_entry1 = UserState(balance=100)
        snapshot_entry1.last_positive_balance_update_day = "2026-01-01"
        snapshot_entry2 = UserState(balance=500)
        snapshot_entry2.last_positive_balance_update_day = "2026-01-01"
        snapshot_entry3 = UserState(balance=200)
        snapshot_entry3.last_positive_balance_update_day = "2026-01-01"
        
        lp_balances_snapshot = {
            "0x1111111111111111111111111111111111111111": snapshot_entry1,  # Above snapshot
            "0x2222222222222222222222222222222222222222": snapshot_entry2,  # Below snapshot
            "0x3333333333333333333333333333333333333333": snapshot_entry3,  # Equal to snapshot
        }
        checker = LpIntegrityChecker(lp_balances_snapshot, 0)

        user_state = {
            "0x1111111111111111111111111111111111111111": UserState(balance=300),  # Above
            "0x2222222222222222222222222222222222222222": UserState(balance=400),  # Below
            "0x3333333333333333333333333333333333333333": UserState(balance=200),  # Equal
        }
        user_state["0x1111111111111111111111111111111111111111"].last_positive_balance_update_day = "2026-01-01"
        user_state["0x2222222222222222222222222222222222222222"].last_positive_balance_update_day = "2026-01-01"
        user_state["0x3333333333333333333333333333333333333333"].last_positive_balance_update_day = "2026-01-01"
        date = "2026-01-15"

        result = checker._validate_lp_integrity(user_state, date)

        assert result["0x1111111111111111111111111111111111111111"] == False  # No issue
        assert result["0x2222222222222222222222222222222222222222"] == True  # Integrity broken
        assert result["0x3333333333333333333333333333333333333333"] == False  # No issue

    def test_address_matching(self):
        """Test that addresses must match exactly between snapshot and user state"""
        snapshot_entry = UserState(balance=100)
        snapshot_entry.last_positive_balance_update_day = "2026-01-01"
        # Use lowercase consistently
        address = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        lp_balances_snapshot = {
            address: snapshot_entry
        }
        checker = LpIntegrityChecker(lp_balances_snapshot, 0)

        user_state = {
            address: UserState(balance=50)  # Below snapshot
        }
        user_state[address].last_positive_balance_update_day = "2026-01-01"
        date = "2026-01-15"

        result = checker._validate_lp_integrity(user_state, date)

        # Should detect integrity issue
        assert result[address] == True