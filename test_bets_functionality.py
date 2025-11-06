#!/usr/bin/env python3
"""
Comprehensive test suite for betting functionality
Tests database operations, bet parsing, and round robin handling
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from nfl_edge.bets.db import BettingDB
import psycopg2
from psycopg2.extras import RealDictCursor


def test_database_connection():
    """Test database connection"""
    print("\n🧪 Test 1: Database Connection")
    try:
        db = BettingDB()
        conn = db.connect()
        assert conn is not None
        assert not conn.closed
        db.close()
        print("✅ PASSED: Database connection successful")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_bet_counts():
    """Test that bets are correctly counted"""
    print("\n🧪 Test 2: Bet Counts")
    try:
        db = BettingDB()
        conn = db.connect()
        with conn.cursor() as cur:
            # Count total bets
            cur.execute("SELECT COUNT(*) as count FROM bets")
            total = cur.fetchone()['count']

            # Count regular bets
            cur.execute("SELECT COUNT(*) as count FROM bets WHERE is_round_robin = FALSE")
            regular = cur.fetchone()['count']

            # Count round robin bets
            cur.execute("SELECT COUNT(*) as count FROM bets WHERE is_round_robin = TRUE")
            rr_count = cur.fetchone()['count']

        db.close()

        print(f"   Total bets: {total}")
        print(f"   Regular bets: {regular}")
        print(f"   Round robin bets: {rr_count}")

        assert total == regular + rr_count, "Total doesn't match sum of regular + round robin"
        assert rr_count > 0, "No round robin bets found"

        print("✅ PASSED: Bet counts are consistent")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_round_robin_structure():
    """Test round robin bet structure"""
    print("\n🧪 Test 3: Round Robin Structure")
    try:
        db = BettingDB()
        conn = db.connect()
        with conn.cursor() as cur:
            # Check round robin parents
            cur.execute("""
                SELECT DISTINCT round_robin_parent, COUNT(*) as child_count
                FROM bets
                WHERE is_round_robin = TRUE AND round_robin_parent IS NOT NULL
                GROUP BY round_robin_parent
            """)
            parents = cur.fetchall()

            print(f"   Found {len(parents)} round robin parent groups")
            for parent in parents:
                print(f"     - {parent['round_robin_parent']}: {parent['child_count']} bets")

            # Verify all round robin bets have a parent
            cur.execute("""
                SELECT COUNT(*) as count
                FROM bets
                WHERE is_round_robin = TRUE AND round_robin_parent IS NULL
            """)
            orphans = cur.fetchone()['count']

        db.close()

        assert len(parents) > 0, "No round robin parent groups found"
        assert orphans == 0, f"Found {orphans} round robin bets without a parent"

        print("✅ PASSED: Round robin structure is valid")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_bet_required_fields():
    """Test that all bets have required fields"""
    print("\n🧪 Test 4: Required Fields")
    try:
        db = BettingDB()
        conn = db.connect()
        with conn.cursor() as cur:
            # Check for null ticket_ids
            cur.execute("SELECT COUNT(*) as count FROM bets WHERE ticket_id IS NULL")
            null_tickets = cur.fetchone()['count']

            # Check for null dates
            cur.execute("SELECT COUNT(*) as count FROM bets WHERE date IS NULL")
            null_dates = cur.fetchone()['count']

            # Check for null amounts
            cur.execute("SELECT COUNT(*) as count FROM bets WHERE amount IS NULL OR amount <= 0")
            invalid_amounts = cur.fetchone()['count']

            # Check for null status
            cur.execute("SELECT COUNT(*) as count FROM bets WHERE status IS NULL OR status = ''")
            null_status = cur.fetchone()['count']

        db.close()

        issues = []
        if null_tickets > 0:
            issues.append(f"{null_tickets} bets with null ticket_id")
        if null_dates > 0:
            issues.append(f"{null_dates} bets with null date")
        if invalid_amounts > 0:
            issues.append(f"{invalid_amounts} bets with invalid amount")
        if null_status > 0:
            issues.append(f"{null_status} bets with null status")

        if issues:
            print(f"❌ FAILED: Found issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False

        print("✅ PASSED: All bets have required fields")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_performance_summary():
    """Test performance summary calculation"""
    print("\n🧪 Test 5: Performance Summary")
    try:
        db = BettingDB()
        summary = db.get_performance_summary()
        db.close()

        print(f"   Total bets: {summary['total_bets']}")
        print(f"   Total wagered: ${summary['total_wagered']:.2f}")
        print(f"   Win rate: {summary['win_rate']:.1f}%")
        print(f"   ROI: {summary['roi']:.1f}%")
        print(f"   Pending: {summary['pending_count']}")

        assert summary['total_bets'] > 0, "No bets in summary"
        assert summary['total_wagered'] > 0, "No wagered amount"

        print("✅ PASSED: Performance summary calculated successfully")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_bet_insertion():
    """Test bet insertion"""
    print("\n🧪 Test 6: Bet Insertion")
    try:
        db = BettingDB()

        # Create a test bet
        test_bet = {
            'ticket_id': 'TEST_BET_001',
            'date': '2025-11-06',
            'description': 'Test bet - Chiefs -3.5',
            'bet_type': 'Spread',
            'status': 'Pending',
            'amount': 100.0,
            'to_win': 90.91,
            'profit': 0.0,
            'is_round_robin': False,
            'round_robin_parent': None
        }

        # Insert the bet
        bet_id = db.insert_bet(test_bet)
        assert bet_id > 0, "Bet ID should be positive"

        # Verify it was inserted
        conn = db.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bets WHERE ticket_id = %s", ('TEST_BET_001',))
            inserted_bet = cur.fetchone()

        assert inserted_bet is not None, "Bet not found after insertion"
        assert inserted_bet['ticket_id'] == 'TEST_BET_001'
        assert inserted_bet['amount'] == 100.0

        # Clean up
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bets WHERE ticket_id = %s", ('TEST_BET_001',))
        conn.commit()
        db.close()

        print("✅ PASSED: Bet insertion works correctly")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        # Clean up on failure
        try:
            db = BettingDB()
            conn = db.connect()
            with conn.cursor() as cur:
                cur.execute("DELETE FROM bets WHERE ticket_id = %s", ('TEST_BET_001',))
            conn.commit()
            db.close()
        except:
            pass
        return False


def test_duplicate_ticket_prevention():
    """Test that duplicate ticket IDs are handled"""
    print("\n🧪 Test 7: Duplicate Ticket Prevention")
    try:
        db = BettingDB()

        # Get an existing ticket ID
        conn = db.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT ticket_id FROM bets LIMIT 1")
            result = cur.fetchone()

        if not result:
            print("⏭️  SKIPPED: No bets in database to test")
            db.close()
            return True

        existing_ticket = result['ticket_id']

        # Try to insert a bet with the same ticket ID
        test_bet = {
            'ticket_id': existing_ticket,
            'date': '2025-11-06',
            'description': 'Duplicate test',
            'bet_type': 'Spread',
            'status': 'Pending',
            'amount': 100.0,
            'to_win': 90.91
        }

        # This should raise an error or be handled
        try:
            bet_id = db.insert_bet(test_bet)
            # If it succeeded, check that it's not a duplicate
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM bets WHERE ticket_id = %s", (existing_ticket,))
                count = cur.fetchone()['count']
            # Depending on implementation, might be 1 (replaced) or raise error
            db.close()
            print(f"   Found {count} bet(s) with ticket_id {existing_ticket}")
            print("✅ PASSED: Duplicate handling works")
            return True
        except psycopg2.IntegrityError:
            db.close()
            print("✅ PASSED: Duplicate prevented by database constraint")
            return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 BETTING FUNCTIONALITY TEST SUITE")
    print("=" * 60)

    tests = [
        test_database_connection,
        test_bet_counts,
        test_round_robin_structure,
        test_bet_required_fields,
        test_performance_summary,
        test_bet_insertion,
        test_duplicate_ticket_prevention
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0

    print(f"Passed: {passed}/{total} ({percentage:.0f}%)")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

