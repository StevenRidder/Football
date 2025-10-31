"""
Phase 1 - Step 1: Collect PFF Data

This script provides instructions and templates for collecting PFF data.
Since PFF data requires a subscription, this script cannot automatically download it.

Manual Steps:
1. Sign up for PFF subscription: https://www.pff.com/subscribe
2. Navigate to NFL > Team Grades
3. Download the following for 2024 season:
   - Offensive Line Pass Blocking Grades (by week)
   - Defensive Line Pass Rush Grades (by week)
   - Quarterback Grades (clean pocket vs pressure splits)
   - Run Blocking Grades
   - Run Defense Grades

4. Save files to: simulation_engine/data/pff_raw/

Expected file format:
- pff_ol_pass_blocking_2024.csv
- pff_dl_pass_rush_2024.csv
- pff_qb_pressure_splits_2024.csv
- pff_ol_run_blocking_2024.csv
- pff_dl_run_defense_2024.csv

This script will then structure the data for analysis.
"""

import pandas as pd
import os
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
PFF_RAW_DIR = DATA_DIR / "pff_raw"
PFF_PROCESSED_DIR = DATA_DIR / "pff_processed"

# Create directories if they don't exist
PFF_RAW_DIR.mkdir(parents=True, exist_ok=True)
PFF_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def check_pff_files():
    """Check if PFF data files exist."""
    required_files = [
        "pff_ol_pass_blocking_2024.csv",
        "pff_dl_pass_rush_2024.csv",
        "pff_qb_pressure_splits_2024.csv",
    ]
    
    missing_files = []
    for file in required_files:
        if not (PFF_RAW_DIR / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing PFF data files:")
        for file in missing_files:
            print(f"   - {file}")
        print(f"\n📁 Expected location: {PFF_RAW_DIR}")
        print("\n📝 Instructions:")
        print("1. Sign up for PFF: https://www.pff.com/subscribe")
        print("2. Download team grades for 2024 season")
        print("3. Save to the directory above")
        return False
    
    print("✅ All PFF data files found!")
    return True


def process_ol_pass_blocking():
    """Process OL pass blocking grades."""
    print("\n📊 Processing OL Pass Blocking Grades...")
    
    # Load raw data
    df = pd.read_csv(PFF_RAW_DIR / "pff_ol_pass_blocking_2024.csv")
    
    # Expected columns: team, week, pass_block_grade, pressures_allowed, sacks_allowed
    # Adjust based on actual PFF export format
    
    # Standardize team names to match nfl_data_py
    team_mapping = {
        "Arizona Cardinals": "ARI",
        "Atlanta Falcons": "ATL",
        "Baltimore Ravens": "BAL",
        "Buffalo Bills": "BUF",
        "Carolina Panthers": "CAR",
        "Chicago Bears": "CHI",
        "Cincinnati Bengals": "CIN",
        "Cleveland Browns": "CLE",
        "Dallas Cowboys": "DAL",
        "Denver Broncos": "DEN",
        "Detroit Lions": "DET",
        "Green Bay Packers": "GB",
        "Houston Texans": "HOU",
        "Indianapolis Colts": "IND",
        "Jacksonville Jaguars": "JAX",
        "Kansas City Chiefs": "KC",
        "Las Vegas Raiders": "LV",
        "Los Angeles Chargers": "LAC",
        "Los Angeles Rams": "LAR",
        "Miami Dolphins": "MIA",
        "Minnesota Vikings": "MIN",
        "New England Patriots": "NE",
        "New Orleans Saints": "NO",
        "New York Giants": "NYG",
        "New York Jets": "NYJ",
        "Philadelphia Eagles": "PHI",
        "Pittsburgh Steelers": "PIT",
        "San Francisco 49ers": "SF",
        "Seattle Seahawks": "SEA",
        "Tampa Bay Buccaneers": "TB",
        "Tennessee Titans": "TEN",
        "Washington Commanders": "WAS",
    }
    
    # Apply mapping (adjust column name based on actual data)
    # df['team'] = df['team_name'].map(team_mapping)
    
    # Save processed data
    output_path = PFF_PROCESSED_DIR / "ol_pass_blocking_2024.csv"
    df.to_csv(output_path, index=False)
    print(f"✅ Saved to: {output_path}")
    
    return df


def process_dl_pass_rush():
    """Process DL pass rush grades."""
    print("\n📊 Processing DL Pass Rush Grades...")
    
    # Load raw data
    df = pd.read_csv(PFF_RAW_DIR / "pff_dl_pass_rush_2024.csv")
    
    # Expected columns: team, week, pass_rush_grade, pressures, sacks, hurries
    # Adjust based on actual PFF export format
    
    # Standardize team names (use same mapping as above)
    
    # Save processed data
    output_path = PFF_PROCESSED_DIR / "dl_pass_rush_2024.csv"
    df.to_csv(output_path, index=False)
    print(f"✅ Saved to: {output_path}")
    
    return df


def process_qb_pressure_splits():
    """Process QB pressure splits."""
    print("\n📊 Processing QB Pressure Splits...")
    
    # Load raw data
    df = pd.read_csv(PFF_RAW_DIR / "pff_qb_pressure_splits_2024.csv")
    
    # Expected columns: 
    # player, team, clean_completion_pct, clean_ypa, clean_epa_per_play,
    # pressure_completion_pct, pressure_ypa, pressure_epa_per_play
    
    # Calculate vulnerability metric
    # df['pressure_vulnerability'] = df['clean_epa_per_play'] - df['pressure_epa_per_play']
    
    # Save processed data
    output_path = PFF_PROCESSED_DIR / "qb_pressure_splits_2024.csv"
    df.to_csv(output_path, index=False)
    print(f"✅ Saved to: {output_path}")
    
    return df


def create_sample_data():
    """Create sample data for testing (if PFF data not available)."""
    print("\n🔧 Creating sample data for testing...")
    
    teams = ["KC", "BUF", "SF", "PHI", "DAL", "MIA", "BAL", "CIN"]
    weeks = list(range(1, 10))
    
    # Sample OL grades
    ol_data = []
    for team in teams:
        base_grade = 60 + (hash(team) % 30)  # 60-90 range
        for week in weeks:
            ol_data.append({
                "team": team,
                "week": week,
                "pass_block_grade": base_grade + (week % 5),
                "pressures_allowed": 15 + (week % 8),
                "sacks_allowed": 2 + (week % 3),
            })
    
    ol_df = pd.DataFrame(ol_data)
    ol_df.to_csv(PFF_PROCESSED_DIR / "ol_pass_blocking_2024.csv", index=False)
    print(f"✅ Sample OL data: {len(ol_df)} rows")
    
    # Sample DL grades
    dl_data = []
    for team in teams:
        base_grade = 65 + (hash(team + "D") % 25)  # 65-90 range
        for week in weeks:
            dl_data.append({
                "team": team,
                "week": week,
                "pass_rush_grade": base_grade + (week % 5),
                "pressures": 20 + (week % 10),
                "sacks": 3 + (week % 4),
            })
    
    dl_df = pd.DataFrame(dl_data)
    dl_df.to_csv(PFF_PROCESSED_DIR / "dl_pass_rush_2024.csv", index=False)
    print(f"✅ Sample DL data: {len(dl_df)} rows")
    
    # Sample QB splits
    qbs = [
        ("Patrick Mahomes", "KC", 0.25, -0.05),
        ("Josh Allen", "BUF", 0.22, -0.08),
        ("Brock Purdy", "SF", 0.20, -0.12),
        ("Jalen Hurts", "PHI", 0.18, -0.10),
        ("Dak Prescott", "DAL", 0.19, -0.15),
        ("Tua Tagovailoa", "MIA", 0.23, -0.10),
        ("Lamar Jackson", "BAL", 0.24, -0.05),
        ("Joe Burrow", "CIN", 0.21, -0.09),
    ]
    
    qb_data = []
    for name, team, clean_epa, pressure_epa in qbs:
        qb_data.append({
            "player": name,
            "team": team,
            "clean_epa_per_play": clean_epa,
            "pressure_epa_per_play": pressure_epa,
            "pressure_vulnerability": clean_epa - pressure_epa,
            "clean_completion_pct": 0.68 + (clean_epa * 0.5),
            "pressure_completion_pct": 0.50 + (pressure_epa * 0.3),
        })
    
    qb_df = pd.DataFrame(qb_data)
    qb_df.to_csv(PFF_PROCESSED_DIR / "qb_pressure_splits_2024.csv", index=False)
    print(f"✅ Sample QB data: {len(qb_df)} rows")
    
    print("\n⚠️  NOTE: This is SAMPLE data for testing only!")
    print("   Real PFF data will produce more accurate results.")


def main():
    """Main execution."""
    print("="*80)
    print("PHASE 1 - STEP 1: COLLECT PFF DATA")
    print("="*80)
    
    # Check if PFF files exist
    has_pff_data = check_pff_files()
    
    if has_pff_data:
        # Process real PFF data
        try:
            ol_df = process_ol_pass_blocking()
            dl_df = process_dl_pass_rush()
            qb_df = process_qb_pressure_splits()
            
            print("\n" + "="*80)
            print("✅ PFF DATA PROCESSING COMPLETE")
            print("="*80)
            print(f"📁 Output directory: {PFF_PROCESSED_DIR}")
            print(f"📊 OL data: {len(ol_df)} rows")
            print(f"📊 DL data: {len(dl_df)} rows")
            print(f"📊 QB data: {len(qb_df)} rows")
            
        except Exception as e:
            print(f"\n❌ Error processing PFF data: {e}")
            print("   Check that CSV files have expected column names.")
            print("   You may need to adjust the processing functions.")
    
    else:
        # Create sample data for testing
        print("\n" + "="*80)
        print("⚠️  PFF DATA NOT FOUND - CREATING SAMPLE DATA")
        print("="*80)
        create_sample_data()
        
        print("\n📝 Next Steps:")
        print("1. Sign up for PFF subscription")
        print("2. Download real data")
        print("3. Re-run this script to process real data")
        print("4. Or continue with sample data for testing")
    
    print("\n🚀 Next Script: calculate_matchup_metrics.py")


if __name__ == "__main__":
    main()

