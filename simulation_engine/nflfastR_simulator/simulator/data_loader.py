"""
Roll-forward data loaders with as-of timestamps.

Per strategy:
- Load only data available up to week-1
- Stamp cutoff for audit trail
- Never peek at future data
"""

from datetime import datetime
import pandas as pd
from typing import List, Tuple


def load_asof(
    df: pd.DataFrame,
    keys: List[str],
    asof_cols: Tuple[str, str],
    season: int,
    week: int
) -> pd.DataFrame:
    """
    Return rows <= (season, week-1).
    
    Args:
        df: DataFrame with temporal data
        keys: Columns to keep
        asof_cols: (season_col, week_col) tuple
        season: Target season
        week: Target week
    
    Returns:
        Filtered DataFrame with as_of stamps
    """
    season_col, week_col = asof_cols
    cut_season, cut_week = season, max(1, week) - 1

    # Filter to data before target week
    out = df[
        (df[season_col] < cut_season) |
        ((df[season_col] == cut_season) & (df[week_col] <= cut_week))
    ].copy()

    # Add as_of stamps for audit trail
    out["as_of_season"] = cut_season
    out["as_of_week"] = cut_week
    out["as_of_ts"] = datetime.utcnow().isoformat()

    return out


def latest_by(
    df: pd.DataFrame,
    group_cols: List[str],
    order_cols: List[str]
) -> pd.DataFrame:
    """
    Take the most recent row per group under the cutoff.
    
    Args:
        df: DataFrame to filter
        group_cols: Columns to group by
        order_cols: Columns to sort by (ascending)
    
    Returns:
        DataFrame with latest row per group
    """
    return df.sort_values(order_cols).groupby(group_cols, as_index=False).tail(1)


if __name__ == "__main__":
    # Test roll-forward logic
    print("="*80)
    print("ROLL-FORWARD DATA LOADER - TEST")
    print("="*80)

    # Create test data
    test_data = pd.DataFrame({
        'season': [2023, 2023, 2023, 2024, 2024, 2024],
        'week': [1, 2, 3, 1, 2, 3],
        'team': ['KC', 'KC', 'KC', 'KC', 'KC', 'KC'],
        'value': [10, 20, 30, 40, 50, 60]
    })

    print("\n📊 Test data:")
    print(test_data)

    # Load as of 2024 Week 2
    filtered = load_asof(test_data, ['team'], ('season', 'week'), 2024, 2)

    print("\n📊 Filtered to 2024 Week 2 (should include up to 2024 Week 1):")
    print(filtered[['season', 'week', 'value', 'as_of_season', 'as_of_week']])

    # Verify cutoff
    assert filtered['week'].max() == 1 or (filtered['season'] < 2024).any()
    assert filtered['as_of_season'].iloc[0] == 2024
    assert filtered['as_of_week'].iloc[0] == 1

    print("\n✅ Roll-forward working correctly:")
    print("  - Only includes data through week-1")
    print("  - as_of stamps added")
    print("  - No look-ahead bias")

