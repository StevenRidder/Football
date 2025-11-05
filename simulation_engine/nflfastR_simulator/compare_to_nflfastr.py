"""
Compare simulator outputs to NFLfastR actuals and generate calibration artifacts.

Reads simulator trace files (JSONL) and aggregates per-game metrics, then compares
to NFLfastR actuals via nfl_data_py.

Inputs:
  - artifacts/traces/*.jsonl (trace files with play-by-play events)
  - OR artifacts/backtest_*.csv (if traces not available, uses CSV output)

Outputs:
  artifacts/calibration/
    - summary_metrics.json
    - per_game_comparison.csv
    - per_team_bias.csv
    - per_week_metrics.csv
    - plots/
      - scores_scatter.png
      - epa_residual_hist.png
      - pressure_rate_bar.png
      - reliability_spread.png
      - reliability_total.png

Usage:
  python3 compare_to_nflfastr.py --season 2025 --weeks 1-8
  python3 compare_to_nflfastr.py --season 2025 --weeks 1,2,3,4,5,6,7,8
  python3 compare_to_nflfastr.py --season 2025 --weeks 1-8 --use-traces
"""

import argparse
import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import numpy as np
import pandas as pd

try:
    from nfl_data_py import import_pbp_data, import_schedules
except ImportError:
    print("⚠️  nfl-data-py not installed. Install with: pip install nfl-data-py")
    import_schedules = None
    import_pbp_data = None


def _parse_weeks(arg: str) -> List[int]:
    """Parse week argument (e.g., '1-8' or '1,2,3,4')."""
    arg = arg.strip()
    if "-" in arg:
        a, b = arg.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in arg.split(",") if x.strip()]


def _ensure_dirs() -> Tuple[Path, Path]:
    """Create output directories."""
    root = Path(__file__).parent / "artifacts" / "calibration"
    plots = root / "plots"
    root.mkdir(parents=True, exist_ok=True)
    plots.mkdir(parents=True, exist_ok=True)
    return root, plots


def _load_trace_file(trace_path: Path) -> Optional[Dict]:
    """Load a single trace file and extract game-level metrics."""
    try:
        events = []
        with trace_path.open() as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        if not events:
            return None
        
        # Find game summary event
        game_summary = None
        inputs_audit = None
        game_id = None
        
        for event in events:
            if event.get('kind') == 'game.summary':
                game_summary = event
            elif event.get('kind') == 'inputs.audit':
                inputs_audit = event
                game_id = event.get('game_id', '')
        
        if not game_summary or not inputs_audit:
            return None
        
        # Parse game_id: format is "YYYY_WW_AWAY_HOME" or "2025_09_ATL_NE"
        parts = game_id.split('_')
        if len(parts) >= 4:
            season = int(parts[0])
            week = int(parts[1])
            away_team = parts[2].upper()
            home_team = parts[3].upper()
        else:
            return None
        
        # Extract scores
        home_score = game_summary.get('home_score', 0)
        away_score = game_summary.get('away_score', 0)
        
        # Extract EPA from inputs (these are team inputs, not simulated EPA)
        # We need to calculate simulated EPA from play events
        home_epa_input = inputs_audit.get('home', {}).get('off_epa', 0)
        away_epa_input = inputs_audit.get('away', {}).get('off_epa', 0)
        
        # Calculate pressure rates from pass.pressure events
        pressure_events = [e for e in events if e.get('kind') == 'pass.pressure']
        home_pressure_events = []
        away_pressure_events = []
        
        # Determine which team was on offense for each pressure event
        # We need to track drive context - for now, use a simple heuristic
        # based on the game flow
        call_events = [e for e in events if e.get('kind') == 'call.pass_run']
        play_events = [e for e in events if e.get('kind') == 'play.result']
        
        # Count total dropbacks and pressures
        total_dropbacks = len([e for e in call_events if e.get('choice') == 'pass'])
        total_pressures = len([e for e in pressure_events if e.get('is_pressure', False)])
        pressure_rate = total_pressures / total_dropbacks if total_dropbacks > 0 else 0
        
        # For now, use same pressure rate for both teams (can refine later)
        # TODO: Split by team based on drive context
        
        # Calculate simulated EPA per play from play results
        # This is a proxy - we'd need drive-level EPA tracking for exact match
        # For now, use input EPA as proxy (simulated EPA should be close to input)
        home_epa_sim = home_epa_input  # TODO: Calculate from actual plays
        away_epa_sim = away_epa_input
        
        return {
            'season': season,
            'week': week,
            'home_team': home_team,
            'away_team': away_team,
            'home_score_sim': home_score,
            'away_score_sim': away_score,
            'home_epa_sim': home_epa_sim,
            'away_epa_sim': away_epa_sim,
            'home_pressure_rate_sim': pressure_rate,  # TODO: Split by team
            'away_pressure_rate_sim': pressure_rate,
        }
    except Exception as e:
        print(f"⚠️  Error loading trace {trace_path}: {e}")
        return None


def _load_sim_from_traces(traces_dir: Path, season: int, weeks: List[int]) -> pd.DataFrame:
    """Load simulator data from trace files."""
    traces_dir = Path(traces_dir)
    if not traces_dir.exists():
        return pd.DataFrame()
    
    results = []
    for trace_file in traces_dir.glob("*.jsonl"):
        data = _load_trace_file(trace_file)
        if data and data['season'] == season and data['week'] in weeks:
            results.append(data)
    
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    # Normalize team keys
    for col in ["home_team", "away_team"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.upper()
    
    return df


def _load_sim_from_csv(csv_path: Path) -> pd.DataFrame:
    """Load simulator data from CSV output."""
    if not csv_path.exists():
        return pd.DataFrame()
    
    df = pd.read_csv(csv_path)
    
    # Normalize team keys
    for col in ["home_team", "away_team"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.upper()
    
    # Map columns to expected format
    col_map = {
        'home_score_mean': 'home_score_sim',
        'away_score_mean': 'away_score_sim',
        'home_epa_mean': 'home_epa_sim',
        'away_epa_mean': 'away_epa_sim',
    }
    
    for old, new in col_map.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]
    
    # Require minimal keys
    required = {"season", "week", "home_team", "away_team"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")
    
    return df


def _load_actuals(season: int, weeks: List[int]) -> pd.DataFrame:
    """Pull actual game data from NFLfastR."""
    if import_schedules is None or import_pbp_data is None:
        raise ImportError("nfl-data-py not installed. Install with: pip install nfl-data-py")
    
    # Pull schedule to align team roles and final scores
    sched = import_schedules([season])
    sched = sched[sched["week"].isin(weeks)].copy()
    sched = sched[["game_id", "season", "week", "home_team", "away_team",
                   "home_score", "away_score"]].copy()
    
    # Pull play-by-play once, then aggregate per game/team
    pbp = import_pbp_data([season], downcast=True)
    pbp = pbp[pbp["week"].isin(weeks)].copy()
    
    # EPA/play per offense
    off = (
        pbp.groupby(["game_id", "posteam"], dropna=False)
           .agg(epa_mean=("epa", "mean"),
                plays=("play_id", "count"),
                dropbacks=("pass", "sum"),
                sacks=("sack", "sum"),
                qb_hits=("qb_hit", "sum"))
           .reset_index()
           .rename(columns={"posteam": "team"})
    )
    
    # Pressure proxy: sacks + QB hits per dropback (if dropbacks>0)
    off["pressure_rate_real"] = np.where(off["dropbacks"] > 0,
                                         (off["sacks"] + off["qb_hits"]) / off["dropbacks"],
                                         np.nan)
    
    # Pivot to home/away to match sim row shape
    # First, attach home/away role via schedule
    role_map = sched[["game_id", "home_team", "away_team"]].copy()
    role_map = role_map.melt(id_vars=["game_id"],
                             value_vars=["home_team", "away_team"],
                             var_name="role", value_name="team")
    role_map["role"] = role_map["role"].str.replace("_team", "", regex=False)
    
    off = off.merge(role_map, on=["game_id", "team"], how="inner")
    
    # Wide format per game
    def _wide(df_role: pd.DataFrame, side: str) -> pd.DataFrame:
        sub = df_role[df_role["role"] == side].copy()
        sub = sub[["game_id", "epa_mean", "pressure_rate_real"]]
        sub = sub.rename(columns={
            "epa_mean": f"{side}_epa_real",
            "pressure_rate_real": f"{side}_pressure_rate_real",
        })
        return sub
    
    home_w = _wide(off, "home")
    away_w = _wide(off, "away")
    
    actual = sched.merge(home_w, on="game_id", how="left").merge(away_w, on="game_id", how="left")
    
    # Normalize team abbreviations to uppercase to match sim
    for col in ["home_team", "away_team"]:
        actual[col] = actual[col].str.strip().str.upper()
    
    return actual


def _merge_sim_actual(sim: pd.DataFrame, actual: pd.DataFrame) -> pd.DataFrame:
    """Merge simulator and actual data."""
    key_cols = ["season", "week", "home_team", "away_team"]
    merged = sim.merge(actual, on=key_cols, how="left", validate="m:1")
    
    # Track unmatched so you can fix inputs quickly
    unmatched = merged[merged["game_id"].isna()][key_cols].drop_duplicates()
    if len(unmatched) > 0:
        print("\n⚠️  Unmatched rows (check abbreviations or week/season):")
        print(unmatched.to_string(index=False))
    
    return merged


def _compute_metrics(df: pd.DataFrame) -> dict:
    """Compute calibration metrics."""
    out = {}
    
    # Score realism
    if {"home_score_sim", "away_score_sim", "home_score", "away_score"} <= set(df.columns):
        df["score_mae"] = (df["home_score_sim"] - df["home_score"]).abs() + \
                          (df["away_score_sim"] - df["away_score"]).abs()
        out["mean_score_mae"] = float(df["score_mae"].mean())
        out["score_rmse"] = float(np.sqrt((df["score_mae"]**2).mean()))
    
    # EPA residuals
    for side in ["home", "away"]:
        sim_col = f"{side}_epa_sim"
        real_col = f"{side}_epa_real"
        if {sim_col, real_col} <= set(df.columns):
            df[f"{side}_epa_resid"] = df[sim_col] - df[real_col]
            out[f"{side}_epa_resid_mean"] = float(df[f"{side}_epa_resid"].mean())
            out[f"{side}_epa_resid_std"] = float(df[f"{side}_epa_resid"].std())
    
    # Pressure realism
    for side in ["home", "away"]:
        sim_col = f"{side}_pressure_rate_sim"
        real_col = f"{side}_pressure_rate_real"
        if {sim_col, real_col} <= set(df.columns):
            valid = df[[sim_col, real_col]].dropna()
            if len(valid) >= 3:
                corr = float(np.corrcoef(valid[sim_col], valid[real_col])[0, 1])
            else:
                corr = float("nan")
            out[f"{side}_pressure_corr"] = corr
    
    return out


def _per_team_bias(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-team EPA bias."""
    # Offensive EPA residuals by team (home+away stacked)
    frames = []
    for side in ["home", "away"]:
        epa_resid = f"{side}_epa_resid"
        team_col = f"{side}_team"
        if epa_resid in df.columns:
            tmp = df[[team_col, epa_resid]].dropna().copy()
            tmp = tmp.rename(columns={team_col: "team", epa_resid: "epa_residual"})
            frames.append(tmp)
    
    if not frames:
        return pd.DataFrame(columns=["team", "count", "epa_residual_mean", "epa_residual_std"])
    
    stack = pd.concat(frames, ignore_index=True)
    agg = stack.groupby("team").agg(count=("epa_residual", "count"),
                                    epa_residual_mean=("epa_residual", "mean"),
                                    epa_residual_std=("epa_residual", "std")).reset_index()
    agg = agg.sort_values("epa_residual_mean", ascending=False)
    return agg


def _per_week_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-week metrics."""
    cols = []
    if "score_mae" in df.columns:
        cols.append("score_mae")
    for side in ["home", "away"]:
        if f"{side}_epa_resid" in df.columns:
            cols.append(f"{side}_epa_resid")
    
    if not cols:
        return pd.DataFrame()
    
    grp = df.groupby(["season", "week"])[cols].mean().reset_index()
    return grp


def _plots(df: pd.DataFrame, plots_dir: Path) -> None:
    """Generate calibration plots."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("⚠️  Skipping plots (matplotlib not available).")
        return
    
    # 1) Scores scatter
    if {"home_score_sim", "home_score"} <= set(df.columns):
        plt.figure(figsize=(8, 8))
        plt.scatter(df["home_score_sim"], df["home_score"], alpha=0.6, label="Home", s=50)
        if {"away_score_sim", "away_score"} <= set(df.columns):
            plt.scatter(df["away_score_sim"], df["away_score"], alpha=0.6, label="Away", s=50)
        lim = [0, max(10 + df[["home_score_sim", "away_score_sim", "home_score", "away_score"]].max().max(), 50)]
        plt.plot(lim, lim, linestyle="--", color="gray", linewidth=1, label="Perfect")
        plt.xlim(lim)
        plt.ylim(lim)
        plt.xlabel("Simulated points")
        plt.ylabel("Actual points")
        plt.title("Scores: Sim vs. Actual")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(plots_dir / "scores_scatter.png", dpi=160)
        plt.close()
    
    # 2) EPA residual histogram
    epa_cols = [c for c in ["home_epa_resid", "away_epa_resid"] if c in df.columns]
    if epa_cols:
        plt.figure(figsize=(10, 6))
        for c in epa_cols:
            s = df[c].dropna()
            if len(s) > 0:
                plt.hist(s, bins=30, alpha=0.5, label=c.replace("_resid", ""))
        plt.axvline(0, color="k", linestyle="--", linewidth=1)
        plt.title("EPA Residuals (Sim - Actual)")
        plt.xlabel("Residual")
        plt.ylabel("Count")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(plots_dir / "epa_residual_hist.png", dpi=160)
        plt.close()
    
    # 3) Pressure rate comparison
    for side in ["home", "away"]:
        sim_col = f"{side}_pressure_rate_sim"
        real_col = f"{side}_pressure_rate_real"
        if {sim_col, real_col} <= set(df.columns):
            valid = df[[sim_col, real_col]].dropna()
            if len(valid) >= 3:
                plt.figure(figsize=(10, 6))
                width = 0.35
                idx = np.arange(len(valid))
                plt.bar(idx - width/2, valid[real_col].values, width, label="Actual", alpha=0.7)
                plt.bar(idx + width/2, valid[sim_col].values, width, label="Sim", alpha=0.7)
                plt.title(f"Pressure Rate Comparison ({side.title()})")
                plt.xlabel("Game index")
                plt.ylabel("Pressure rate")
                plt.legend()
                plt.grid(True, alpha=0.3, axis='y')
                plt.tight_layout()
                plt.savefig(plots_dir / f"pressure_rate_bar_{side}.png", dpi=160)
                plt.close()
    
    # 4) Reliability curves (optional; needs point-level win probs)
    if {"p_home_cover", "spread_result"} <= set(df.columns):
        _reliability_plot(df, "p_home_cover", "spread_result", plots_dir / "reliability_spread.png")
    if {"p_over", "total_result"} <= set(df.columns):
        _reliability_plot(df, "p_over", "total_result", plots_dir / "reliability_total.png")


def _reliability_plot(df: pd.DataFrame, p_col: str, y_col: str, out_path: Path) -> None:
    """Plot reliability curve."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    
    d = df[[p_col, y_col]].dropna().copy()
    if len(d) < 10:
        return
    
    d[p_col] = d[p_col].clip(0.01, 0.99)
    d["bin"] = pd.qcut(d[p_col], q=10, duplicates="drop")
    cal = d.groupby("bin").agg(avg_p=(p_col, "mean"), emp_rate=(y_col, "mean"), n=("bin", "count")).reset_index()
    
    plt.figure(figsize=(8, 8))
    plt.plot(cal["avg_p"], cal["emp_rate"], marker="o", label="Empirical", linewidth=2)
    plt.plot([0, 1], [0, 1], linestyle="--", label="Ideal", color="gray")
    plt.xlabel("Predicted probability")
    plt.ylabel("Empirical win rate")
    plt.title(f"Reliability: {p_col} vs {y_col}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Compare simulator outputs to NFLfastR actuals")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--weeks", type=str, required=True, help="e.g. 1-8 or 1,2,3,4")
    parser.add_argument("--sim-csv", type=str, default=None, 
                       help="Path to simulator CSV output (if not using traces)")
    parser.add_argument("--use-traces", action="store_true",
                       help="Load from trace files instead of CSV")
    args = parser.parse_args()
    
    weeks = _parse_weeks(args.weeks)
    out_dir, plots_dir = _ensure_dirs()
    
    # Load simulator data
    if args.use_traces:
        traces_dir = Path(__file__).parent / "artifacts" / "traces"
        sim = _load_sim_from_traces(traces_dir, args.season, weeks)
        if sim.empty:
            print("⚠️  No trace files found. Try --sim-csv instead.")
            return
    else:
        if args.sim_csv:
            csv_path = Path(args.sim_csv)
        else:
            # Try to find backtest CSV
            csv_path = Path(__file__).parent / "artifacts" / "backtest_week9_10_predictions.csv"
            if not csv_path.exists():
                csv_path = Path(__file__).parent / "artifacts" / "results.csv"
        
        sim = _load_sim_from_csv(csv_path)
        if sim.empty:
            print(f"⚠️  No simulator data found at {csv_path}. Try --use-traces or specify --sim-csv.")
            return
    
    print(f"✅ Loaded {len(sim)} simulator games")
    
    # Load actuals
    try:
        actual = _load_actuals(args.season, weeks)
        print(f"✅ Loaded {len(actual)} actual games from NFLfastR")
    except Exception as e:
        print(f"❌ Error loading actuals: {e}")
        return
    
    # Merge
    merged = _merge_sim_actual(sim, actual)
    
    if merged.empty:
        print("❌ No games matched after merge. Check team abbreviations and weeks.")
        return
    
    # Compute metrics and tables
    metrics = _compute_metrics(merged)
    per_team = _per_team_bias(merged)
    per_week = _per_week_metrics(merged)
    
    # Save artifacts
    merged.to_csv(out_dir / "per_game_comparison.csv", index=False)
    per_team.to_csv(out_dir / "per_team_bias.csv", index=False)
    per_week.to_csv(out_dir / "per_week_metrics.csv", index=False)
    
    with open(out_dir / "summary_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    
    # Plots
    _plots(merged, plots_dir)
    
    # Console summary
    print("\n" + "="*60)
    print("CALIBRATION SUMMARY")
    print("="*60)
    for k, v in sorted(metrics.items()):
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")
    
    if len(per_team) > 0:
        print("\n📊 Top team biases (EPA residual mean):")
        print(per_team.head(10).to_string(index=False))
    
    print(f"\n✅ Artifacts written to: {out_dir}\n")


if __name__ == "__main__":
    main()

