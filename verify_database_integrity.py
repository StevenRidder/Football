#!/usr/bin/env python3
"""
Database integrity verification script
Checks for data consistency, constraints, and potential issues
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from nfl_edge.bets.db import BettingDB


def check_referential_integrity():
    """Check referential integrity"""
    print("\n🔍 Checking Referential Integrity...")
    db = BettingDB()
    conn = db.connect()

    with conn.cursor() as cur:
        # Check for parlay legs without parent bets
        cur.execute("""
            SELECT COUNT(*) as count
            FROM parlay_legs pl
            LEFT JOIN bets b ON pl.bet_id = b.id
            WHERE b.id IS NULL
        """)
        orphan_legs = cur.fetchone()['count']

        if orphan_legs > 0:
            print(f"   ⚠️  Found {orphan_legs} parlay legs without parent bets")
        else:
            print(f"   ✅ All parlay legs have valid parent bets")

    db.close()
    return orphan_legs == 0


def check_data_consistency():
    """Check data consistency"""
    print("\n🔍 Checking Data Consistency...")
    db = BettingDB()
    conn = db.connect()
    issues = []

    with conn.cursor() as cur:
        # Check for negative amounts
        cur.execute("SELECT COUNT(*) as count FROM bets WHERE amount < 0")
        negative_amounts = cur.fetchone()['count']
        if negative_amounts > 0:
            issues.append(f"{negative_amounts} bets with negative amounts")

        # Check for invalid status values
        cur.execute("""
            SELECT COUNT(*) as count FROM bets
            WHERE status NOT IN ('Pending', 'Won', 'Lost', 'Push', 'Cancelled')
        """)
        invalid_status = cur.fetchone()['count']
        if invalid_status > 0:
            issues.append(f"{invalid_status} bets with invalid status")

        # Check profit consistency for won/lost bets
        cur.execute("""
            SELECT COUNT(*) as count FROM bets
            WHERE status = 'Won' AND profit <= 0
        """)
        won_no_profit = cur.fetchone()['count']
        if won_no_profit > 0:
            issues.append(f"{won_no_profit} Won bets with no profit")

        cur.execute("""
            SELECT COUNT(*) as count FROM bets
            WHERE status = 'Lost' AND profit >= 0
        """)
        lost_no_loss = cur.fetchone()['count']
        if lost_no_loss > 0:
            issues.append(f"{lost_no_loss} Lost bets with no loss")

    db.close()

    if issues:
        for issue in issues:
            print(f"   ⚠️  {issue}")
        return False
    else:
        print("   ✅ All data consistency checks passed")
        return True


def check_round_robin_consistency():
    """Check round robin bet consistency"""
    print("\n🔍 Checking Round Robin Consistency...")
    db = BettingDB()
    conn = db.connect()
    issues = []

    with conn.cursor() as cur:
        # All round robin bets should have a parent
        cur.execute("""
            SELECT COUNT(*) as count FROM bets
            WHERE is_round_robin = TRUE AND round_robin_parent IS NULL
        """)
        orphan_rr = cur.fetchone()['count']
        if orphan_rr > 0:
            issues.append(f"{orphan_rr} round robin bets without parent")

        # Non-round-robin bets should not have a parent
        cur.execute("""
            SELECT COUNT(*) as count FROM bets
            WHERE is_round_robin = FALSE AND round_robin_parent IS NOT NULL
        """)
        invalid_parent = cur.fetchone()['count']
        if invalid_parent > 0:
            issues.append(f"{invalid_parent} regular bets with round_robin_parent set")

    db.close()

    if issues:
        for issue in issues:
            print(f"   ⚠️  {issue}")
        return False
    else:
        print("   ✅ All round robin consistency checks passed")
        return True


def check_database_indexes():
    """Check database indexes"""
    print("\n🔍 Checking Database Indexes...")
    db = BettingDB()
    conn = db.connect()

    with conn.cursor() as cur:
        # Check for indexes on commonly queried columns
        cur.execute("""
            SELECT
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename IN ('bets', 'parlay_legs')
            ORDER BY tablename, indexname
        """)
        indexes = cur.fetchall()

        if indexes:
            print(f"   Found {len(indexes)} indexes:")
            for idx in indexes:
                print(f"     - {idx['tablename']}.{idx['indexname']}")
        else:
            print("   ⚠️  No indexes found (may impact performance)")

    db.close()
    return True


def check_summary_statistics():
    """Display summary statistics"""
    print("\n📊 Database Summary Statistics...")
    db = BettingDB()
    conn = db.connect()

    with conn.cursor() as cur:
        # Total bets by status
        cur.execute("""
            SELECT status, COUNT(*) as count, SUM(amount) as total_amount
            FROM bets
            GROUP BY status
            ORDER BY count DESC
        """)
        by_status = cur.fetchall()

        print("   Bets by Status:")
        for row in by_status:
            print(f"     - {row['status']}: {row['count']} bets (${row['total_amount']:.2f})")

        # Bets by type
        cur.execute("""
            SELECT bet_type, COUNT(*) as count
            FROM bets
            GROUP BY bet_type
            ORDER BY count DESC
            LIMIT 10
        """)
        by_type = cur.fetchall()

        print("\n   Top Bet Types:")
        for row in by_type:
            print(f"     - {row['bet_type']}: {row['count']} bets")

        # Date range
        cur.execute("""
            SELECT MIN(date) as earliest, MAX(date) as latest
            FROM bets
        """)
        date_range = cur.fetchone()
        print(f"\n   Date Range: {date_range['earliest']} to {date_range['latest']}")

    db.close()
    return True


def main():
    """Run all integrity checks"""
    print("=" * 60)
    print("🔍 DATABASE INTEGRITY VERIFICATION")
    print("=" * 60)

    checks = [
        check_referential_integrity,
        check_data_consistency,
        check_round_robin_consistency,
        check_database_indexes,
        check_summary_statistics
    ]

    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Check failed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("\n" + "=" * 60)
    print("📊 INTEGRITY CHECK SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if r)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if all(results):
        print("\n✅ DATABASE INTEGRITY VERIFIED")
        return 0
    else:
        print("\n⚠️  SOME ISSUES DETECTED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

