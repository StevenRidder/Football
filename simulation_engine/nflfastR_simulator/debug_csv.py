import pandas as pd
import numpy as np
from pathlib import Path

artifacts_dir = Path(__file__).parent.parent.parent / "artifacts"
df = pd.read_csv(artifacts_dir / "simulator_predictions.csv")
df_2025 = df[(df['season'] == 2025) & (df['is_completed'] == True) & (df['week'] <= 8)].copy()

print(f"Total rows: {len(df_2025)}")
print(f"Has our_home_score_raw: {'our_home_score_raw' in df_2025.columns}")
print(f"Has our_away_score_raw: {'our_away_score_raw' in df_2025.columns}")
print(f"Has closing_spread: {'closing_spread' in df_2025.columns}")
print(f"Has spread_std: {'spread_std' in df_2025.columns}")

if 'our_home_score_raw' in df_2025.columns:
    df_2025['spread_raw'] = df_2025['our_home_score_raw'] - df_2025['our_away_score_raw']
    df_2025['total_raw'] = df_2025['our_home_score_raw'] + df_2025['our_away_score_raw']
    print(f"\nspread_raw non-null: {df_2025['spread_raw'].notna().sum()}")
    print(f"total_raw non-null: {df_2025['total_raw'].notna().sum()}")
    print(f"closing_spread non-null: {df_2025['closing_spread'].notna().sum()}")
    print(f"spread_std non-null: {df_2025['spread_std'].notna().sum() if 'spread_std' in df_2025.columns else 0}")
    
    # Check valid mask
    sim_spreads = df_2025['spread_raw'].values
    sim_sds = df_2025.get('spread_std', np.full(len(df_2025), 11.0)).values
    market_spreads = df_2025['closing_spread'].values
    
    valid_mask = ~(np.isnan(sim_spreads) | np.isnan(sim_sds) | np.isnan(market_spreads))
    print(f"\nValid samples: {valid_mask.sum()}")
    print(f"NaN in spread_raw: {np.isnan(sim_spreads).sum()}")
    print(f"NaN in spread_std: {np.isnan(sim_sds).sum()}")
    print(f"NaN in closing_spread: {np.isnan(market_spreads).sum()}")

