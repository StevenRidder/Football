# bias_calibration.py

"""

Bias tracking, calibration curves, and weekly ROI for the NFL simulator.



What this module provides

-------------------------

1) Residual logging (prediction vs. reality) by team and week:

   - Per-team residuals for points scored and allowed

   - Per-game residuals for spread and total

   - Rolling and EWMA bias estimates

   - CSV artifact: artifacts/bias_history.csv



2) Calibration curves (reliability plots):

   - For spreads: uses the chosen side's predicted win prob vs. actual result

   - For totals: uses the chosen side's predicted prob vs. actual result

   - PIT "PIT" is only an example; you can pass any team or "ALL"



3) Weekly ROI tracking:

   - Computes per-week and cumulative ROI using -110 pricing

   - CSV artifact: artifacts/weekly_roi.csv



4) Bias correction helpers:

   - get_score_adjustment(team, season, week, ...) returns a bounded per-team

     point tweak you can add to predicted team scores before grading bets.

   - Default bounds: ±2.0 points, built from recent residuals with decay.



Assumptions about your backtest DataFrame

-----------------------------------------

The DataFrame produced by your backtest script should contain (already true in your code):

- 'season', 'week', 'home_team', 'away_team'

- 'home_score_mean', 'away_score_mean'            # model predicted means (post-calibration)

- 'actual_home_score', 'actual_away_score'        # final scores

- 'spread_line', 'total_line'

- 'spread_bet' in {'HOME','AWAY', None}

- 'total_bet'  in {'OVER','UNDER', None}

- 'p_home_cover', 'p_away_cover', 'p_over', 'p_under'

- 'spread_result' and 'total_result' in {1.0, 0.0, NaN}



You can call the public functions right after you build and grade your DataFrame.

"""



from __future__ import annotations

import os
import warnings

from pathlib import Path

import numpy as np

import pandas as pd

import matplotlib.pyplot as plt

from typing import Optional, Tuple, Literal, Dict



ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)



BIAS_HISTORY_CSV = ARTIFACTS_DIR / "bias_history.csv"

WEEKLY_ROI_CSV = ARTIFACTS_DIR / "weekly_roi.csv"





# ----------------------------

# 1) RESIDUAL LOGGING

# ----------------------------



def _game_level_residuals(df: pd.DataFrame) -> pd.DataFrame:

    """Compute per-game residuals for spread and total and attach to df copy."""

    out = df.copy()



    # Predicted means

    out['pred_home_pts'] = out['home_score_mean']

    out['pred_away_pts'] = out['away_score_mean']

    out['pred_spread']   = out['pred_home_pts'] - out['pred_away_pts']      # home - away

    out['pred_total']    = out['pred_home_pts'] + out['pred_away_pts']



    # Actuals

    out['act_home_pts'] = out['actual_home_score']

    out['act_away_pts'] = out['actual_away_score']

    out['act_spread']   = out['act_home_pts'] - out['act_away_pts']

    out['act_total']    = out['act_home_pts'] + out['act_away_pts']



    # Residuals (actual - predicted). Positive means model was too low.

    out['res_home_pts'] = out['act_home_pts'] - out['pred_home_pts']

    out['res_away_pts'] = out['act_away_pts'] - out['pred_away_pts']

    out['res_spread']   = out['act_spread']   - out['pred_spread']

    out['res_total']    = out['act_total']    - out['pred_total']



    return out





def _team_rows(game_row: pd.Series) -> Tuple[pd.Series, pd.Series]:

    """Return two team rows from a single game row: one for home, one for away."""

    common = {

        'season': game_row['season'],

        'week': game_row['week'],

        'game_id': game_row.get('game_id', np.nan),

    }

    home = {

        **common,

        'team': game_row['home_team'],

        'opponent': game_row['away_team'],

        'pred_points_for': game_row['pred_home_pts'],

        'pred_points_against': game_row['pred_away_pts'],

        'act_points_for': game_row['act_home_pts'],

        'act_points_against': game_row['act_away_pts'],

        'res_points_for': game_row['res_home_pts'],

        'res_points_against': game_row['res_away_pts'],

        'venue': 'home'

    }

    away = {

        **common,

        'team': game_row['away_team'],

        'opponent': game_row['home_team'],

        'pred_points_for': game_row['pred_away_pts'],

        'pred_points_against': game_row['pred_home_pts'],

        'act_points_for': game_row['act_away_pts'],

        'act_points_against': game_row['act_home_pts'],

        'res_points_for': game_row['res_away_pts'],

        'res_points_against': game_row['res_home_pts'],

        'venue': 'away'

    }

    return pd.Series(home), pd.Series(away)





def log_residuals(df_backtest: pd.DataFrame, save: bool = True) -> pd.DataFrame:

    """

    Build a per-team residual history long-table and save to artifacts/bias_history.csv.



    Returns the long-table with columns:

    ['season','week','game_id','team','opponent','venue',

     'pred_points_for','pred_points_against','act_points_for','act_points_against',

     'res_points_for','res_points_against',

     'res_spread','res_total']  # res_spread/res_total duplicated per side for convenience

    """

    g = _game_level_residuals(df_backtest)



    rows = []

    for _, r in g.iterrows():

        home, away = _team_rows(r)

        # Attach game-level residuals for convenience

        home['res_spread'] = r['res_spread']

        home['res_total']  = r['res_total']

        away['res_spread'] = r['res_spread']

        away['res_total']  = r['res_total']

        rows.append(home)

        rows.append(away)



    hist = pd.DataFrame(rows).sort_values(['season','week','team']).reset_index(drop=True)



    if save:

        if BIAS_HISTORY_CSV.exists():

            # append without dupes on (season, week, team)

            old = pd.read_csv(BIAS_HISTORY_CSV)

            key = ['season','week','team']

            merged = pd.concat([old, hist], ignore_index=True)

            merged = merged.sort_values(key).drop_duplicates(subset=key, keep='last')

            merged.to_csv(BIAS_HISTORY_CSV, index=False)

        else:

            hist.to_csv(BIAS_HISTORY_CSV, index=False)



    return hist





# ----------------------------

# 2) BIAS ESTIMATION + CORRECTION

# ----------------------------



def _compute_opponent_def_rating(bias_hist: pd.DataFrame) -> pd.Series:
    """
    Compute opponent defensive strength proxy: average points allowed by opponent.
    Uses a simple rolling average of opponent's defensive performance.
    """
    # For each opponent, compute their average points allowed (defensive strength)
    opp_def_rating = bias_hist.groupby('opponent')['act_points_against'].expanding().mean().reset_index(level=0, drop=True)
    return opp_def_rating


def _rolling_bias_table(

    bias_hist: pd.DataFrame,

    span_ewm: int = 2,  # Shorter memory: was 4

    clip_points: float = 1.0,  # Smaller cap: was 2.0

    venue_aware: bool = True,

    opponent_adjusted: bool = True

) -> pd.DataFrame:

    """

    Compute rolling bias metrics per team using EWMA on residuals.

    Now with venue-aware and opponent-adjusted features.

    Produces per-team metrics:

      - off_bias_pts[_home|_away]: EWMA of res_points_for (by venue)

      - def_bias_pts[_home|_away]: EWMA of res_points_against (by venue)

      - net_bias_pts[_home|_away]: EWMA of (res_points_for - res_points_against) by venue

      All clipped to ±clip_points for safety.

    """

    def _clip(s: pd.Series) -> pd.Series:

        return s.clip(lower=-clip_points, upper=clip_points)



    bias_hist = bias_hist.copy()

    bias_hist = bias_hist.sort_values(['team','season','week'])

    
    # Opponent adjustment: regress out opponent defensive strength
    if opponent_adjusted and 'opponent' in bias_hist.columns:
        # Compute opponent defensive rating (proxy: their avg points allowed)
        bias_hist['opp_def_rating'] = bias_hist.groupby('opponent')['act_points_against'].transform(
            lambda x: x.expanding().mean().shift(1).fillna(0)
        )
        
        # Initialize adjusted residuals column
        bias_hist['res_points_for_adj'] = bias_hist['res_points_for']
        
        # Regress res_points_for on opponent defensive strength
        for team, grp in bias_hist.groupby('team', sort=False):
            team_mask = bias_hist['team'] == team
            
            # Lower threshold: need at least 2 points for regression (was 4)
            # Early season we have fewer games, so be more lenient
            if team_mask.sum() >= 2:
                opp_rating = bias_hist.loc[team_mask, 'opp_def_rating'].fillna(0).values
                res_for = bias_hist.loc[team_mask, 'res_points_for'].fillna(0).values
                
                # Filter out NaN/inf values
                valid_mask = np.isfinite(opp_rating) & np.isfinite(res_for)
                opp_rating_clean = opp_rating[valid_mask]
                res_for_clean = res_for[valid_mask]
                
                # Check if we have enough data and variance for regression
                # Lower threshold to 2 points (was 3) - for early season
                if (len(opp_rating_clean) >= 2 and 
                    np.std(opp_rating_clean) > 1e-6 and 
                    np.std(res_for_clean) > 1e-6):
                    try:
                        # Suppress numpy warnings during regression
                        with warnings.catch_warnings():
                            warnings.filterwarnings('ignore', category=RuntimeWarning)
                            warnings.filterwarnings('ignore', category=np.RankWarning)
                            # Use np.polyfit with better error handling
                            coef = np.polyfit(opp_rating_clean, res_for_clean, 1)
                        
                        # Only apply if coefficient is reasonable (not extreme)
                        if np.isfinite(coef).all() and abs(coef[0]) < 10.0:
                            # Adjust residuals: remove opponent effect
                            bias_hist.loc[team_mask, 'res_points_for_adj'] = (
                                bias_hist.loc[team_mask, 'res_points_for'] - 
                                (coef[0] * bias_hist.loc[team_mask, 'opp_def_rating'] + coef[1])
                            )
                    except (np.linalg.LinAlgError, ValueError):
                        # Fallback: use original residuals if regression fails
                        pass
    else:
        bias_hist['res_points_for_adj'] = bias_hist['res_points_for']



    parts = []

    if venue_aware:
        # Group by team AND venue for venue-specific bias
        for (team, venue), grp in bias_hist.groupby(['team', 'venue'], sort=False):
            grp = grp.sort_values(['season','week'])
            
            # Use opponent-adjusted residuals if available
            res_for_col = 'res_points_for_adj' if 'res_points_for_adj' in grp.columns else 'res_points_for'
            
            grp[f'off_bias_pts_{venue}'] = grp[res_for_col].ewm(span=span_ewm, adjust=False).mean()
            grp[f'def_bias_pts_{venue}'] = grp['res_points_against'].ewm(span=span_ewm, adjust=False).mean()
            grp[f'net_bias_pts_{venue}'] = (
                (grp[res_for_col] - grp['res_points_against']).ewm(span=span_ewm, adjust=False).mean()
            )
            
            grp[f'off_bias_pts_{venue}'] = _clip(grp[f'off_bias_pts_{venue}'])
            grp[f'def_bias_pts_{venue}'] = _clip(grp[f'def_bias_pts_{venue}'])
            grp[f'net_bias_pts_{venue}'] = _clip(grp[f'net_bias_pts_{venue}'])
            
            parts.append(grp)
    else:
        # Original behavior: aggregate across venues
        for team, grp in bias_hist.groupby('team', sort=False):
            grp = grp.sort_values(['season','week'])
            
            res_for_col = 'res_points_for_adj' if 'res_points_for_adj' in grp.columns else 'res_points_for'
            
            grp['off_bias_pts'] = grp[res_for_col].ewm(span=span_ewm, adjust=False).mean()
            grp['def_bias_pts'] = grp['res_points_against'].ewm(span=span_ewm, adjust=False).mean()
            grp['net_bias_pts'] = (grp[res_for_col] - grp['res_points_against']).ewm(span=span_ewm, adjust=False).mean()

            grp['off_bias_pts'] = _clip(grp['off_bias_pts'])
            grp['def_bias_pts'] = _clip(grp['def_bias_pts'])
            grp['net_bias_pts'] = _clip(grp['net_bias_pts'])
            parts.append(grp)



    out = pd.concat(parts, ignore_index=True)

    return out





def get_score_adjustment(

    team: str,

    season: int,

    week: int,

    hist_csv: Path = BIAS_HISTORY_CSV,

    span_ewm: int = 2,  # Shorter memory: was 4

    mode: Literal['offense','defense','net','off_minus_def'] = 'net',

    clip_points: float = 1.0,  # Smaller cap: was 2.0

    venue: Optional[str] = None  # 'home' or 'away' for venue-aware adjustment

) -> float:

    """

    Return a bounded point adjustment for a team prior to sim prediction.



    Modes:

      - 'offense'       : add to predicted team points

      - 'defense'       : add to predicted opponent points (i.e., worse defense)

      - 'off_minus_def' : offense - defense

      - 'net'           : shorthand for margin-side bias (positive means model undershot margin)



    Suggested use:

       pred_home += get_score_adjustment(home_team, season, week, 'offense')

       pred_away += get_score_adjustment(away_team, season, week, 'offense')

       pred_home -= get_score_adjustment(away_team, season, week, 'defense')

       pred_away -= get_score_adjustment(home_team, season, week, 'defense')



    For a simpler single-number tweak per team, use 'net' and split it 60/40 to offense/defense.

    """

    if not hist_csv.exists():

        return 0.0



    hist = pd.read_csv(hist_csv)

    tbl = _rolling_bias_table(hist, span_ewm=span_ewm, clip_points=clip_points, venue_aware=(venue is not None))



    # Use all prior weeks for stability

    prior = tbl[(tbl['team'] == team) & ((tbl['season'] < season) | ((tbl['season'] == season) & (tbl['week'] < week)))]

    if prior.empty:

        return 0.0

    # Filter by venue if venue-aware
    if venue and f'venue' in prior.columns:
        prior = prior[prior['venue'] == venue]
        if prior.empty:
            # Fallback to any venue if no venue-specific data
            prior = tbl[(tbl['team'] == team) & ((tbl['season'] < season) | ((tbl['season'] == season) & (tbl['week'] < week)))]

    if prior.empty:

        return 0.0



    last = prior.sort_values(['season','week']).iloc[-1]

    # Use venue-specific columns if available
    if venue and f'off_bias_pts_{venue}' in last.index:
        if mode == 'offense':
            return float(last[f'off_bias_pts_{venue}'])
        elif mode == 'defense':
            return float(last[f'def_bias_pts_{venue}'])
        elif mode == 'off_minus_def':
            return float(last[f'off_bias_pts_{venue}'] - last[f'def_bias_pts_{venue}'])
        else:
            return float(last[f'net_bias_pts_{venue}'])
    else:
        # Fallback to non-venue-specific columns
        if mode == 'offense':
            return float(last.get('off_bias_pts', 0.0))
        elif mode == 'defense':
            return float(last.get('def_bias_pts', 0.0))
        elif mode == 'off_minus_def':
            off = last.get('off_bias_pts', 0.0)
            def_pts = last.get('def_bias_pts', 0.0)
            return float(off - def_pts)
        else:
            return float(last.get('net_bias_pts', 0.0))





def apply_bias_correction_to_scores(

    pred_home_pts: float,

    pred_away_pts: float,

    home_team: str,

    away_team: str,

    season: int,

    week: int,

    split: Tuple[float,float] = (0.5, 0.5),  # Split net bias: was (0.6, 0.4)

    clip_points: float = 1.0,  # Smaller cap: was 2.0

    span_ewm: int = 2  # Shorter memory: was 4

) -> Tuple[float, float]:

    """

    Apply a bounded net-bias correction to each team's predicted points.



    By default, take each team's 'net' bias and distribute:

      team_off_adj   = +split[0] * net_bias(team)

      opp_def_adj    = -split[1] * net_bias(opponent)

      corrected_team = pred + team_off_adj + opp_def_adj



    This gently corrects persistent team skew without overfitting.

    Now uses venue-aware and opponent-adjusted bias with shorter memory.

    """

    home_net = get_score_adjustment(home_team, season, week, mode='net', clip_points=clip_points, 
                                   span_ewm=span_ewm, venue='home')

    away_net = get_score_adjustment(away_team, season, week, mode='net', clip_points=clip_points, 
                                   span_ewm=span_ewm, venue='away')



    h = pred_home_pts + split[0]*home_net - split[1]*away_net

    a = pred_away_pts + split[0]*away_net - split[1]*home_net

    return float(h), float(a)





# ----------------------------

# 3) CALIBRATION CURVES

# ----------------------------



def _bucketify(probs: np.ndarray, outcomes: np.ndarray, bins: int = 10) -> pd.DataFrame:

    """Return reliability table with columns: ['bin_low','bin_high','count','pred','obs']"""

    probs = np.asarray(probs, dtype=float)

    outcomes = np.asarray(outcomes, dtype=float)

    mask = np.isfinite(probs) & np.isfinite(outcomes)

    probs = probs[mask]; outcomes = outcomes[mask]



    edges = np.linspace(0.0, 1.0, bins+1)

    idx = np.digitize(probs, edges, right=True)

    idx[idx == 0] = 1

    idx[idx > bins] = bins



    rows = []

    for b in range(1, bins+1):

        m = idx == b

        cnt = int(m.sum())

        if cnt == 0:

            rows.append((edges[b-1], edges[b], 0, np.nan, np.nan))

        else:

            rows.append((edges[b-1], edges[b], cnt, float(probs[m].mean()), float(outcomes[m].mean())))

    return pd.DataFrame(rows, columns=['bin_low','bin_high','count','pred','obs'])





def calibration_curve_spread(

    df: pd.DataFrame,

    team: Optional[str] = None,

    bins: int = 10,

    save_png: Optional[Path] = ARTIFACTS_DIR / "calibration_spread.png"

) -> pd.DataFrame:

    """

    Build and optionally plot a reliability curve for spread bets.



    Uses the chosen side's model probability:

      side_prob = p_home_cover if spread_bet=='HOME' else p_away_cover

      outcome   = 1.0 if spread_result==1.0 else 0.0



    If 'team' is provided, only include games where that team was the chosen side.

    """

    d = df.copy()

    d = d[d['spread_bet'].notna()].copy()



    # Map chosen side to probability and outcome

    d['side_prob'] = np.where(d['spread_bet'] == 'HOME', d['p_home_cover'], d['p_away_cover'])

    d['side_outcome'] = np.where(d['spread_result'] == 1.0, 1.0, 0.0)



    if team is not None:

        chosen_is_team = np.where(d['spread_bet'] == 'HOME', d['home_team'], d['away_team'])

        d = d[chosen_is_team == team]



    table = _bucketify(d['side_prob'].values, d['side_outcome'].values, bins=bins)



    # Plot if requested

    if save_png is not None:

        plt.figure(figsize=(5.2, 5.2))

        plt.plot([0,1],[0,1], linestyle='--', linewidth=1)

        plt.plot(table['pred'], table['obs'], marker='o')

        plt.xlabel('Predicted win probability (ATS)')

        plt.ylabel('Observed win rate')

        title = "Spread calibration"

        if team: title += f" – {team}"

        plt.title(title)

        plt.tight_layout()

        plt.savefig(save_png, dpi=150)

        plt.close()



    return table





def calibration_curve_total(

    df: pd.DataFrame,

    bins: int = 10,

    save_png: Optional[Path] = ARTIFACTS_DIR / "calibration_total.png"

) -> pd.DataFrame:

    """

    Reliability curve for totals using the chosen side's model probability:

      side_prob = p_over if total_bet=='OVER' else p_under

      outcome   = 1.0 if total_result==1.0 else 0.0

    """

    d = df.copy()

    d = d[d['total_bet'].notna()].copy()



    d['side_prob'] = np.where(d['total_bet'] == 'OVER', d['p_over'], d['p_under'])

    d['side_outcome'] = np.where(d['total_result'] == 1.0, 1.0, 0.0)



    table = _bucketify(d['side_prob'].values, d['side_outcome'].values, bins=bins)



    if save_png is not None:

        plt.figure(figsize=(5.2, 5.2))

        plt.plot([0,1],[0,1], linestyle='--', linewidth=1)

        plt.plot(table['pred'], table['obs'], marker='o')

        plt.xlabel('Predicted win probability (Totals)')

        plt.ylabel('Observed win rate')

        plt.title('Total calibration')

        plt.tight_layout()

        plt.savefig(save_png, dpi=150)

        plt.close()



    return table





# ----------------------------

# 4) WEEKLY ROI TRACKING

# ----------------------------



def _bet_outcome_to_roi(win: np.ndarray, price: float = -110.0) -> np.ndarray:

    """

    Convert W/L into ROI per bet at a given American price (default -110).

    Win returns +0.909, loss -1.0, push = 0. Assumes unit stakes.

    """

    # odds -110 -> risk 1 to win 0.909

    win_return = 0.909 if price == -110 else _price_to_payout(price)

    out = np.zeros_like(win, dtype=float)

    out[win == 1.0] = win_return

    out[win == 0.0] = -1.0

    return out





def _price_to_payout(price: float) -> float:

    """American odds to net payout per 1u risk."""

    if price < 0:

        return 100.0 / (-price)

    else:

        return price / 100.0





def weekly_roi(

    df: pd.DataFrame,

    include_spread: bool = True,

    include_total: bool = True,

    price_spread: float = -110.0,

    price_total: float = -110.0,

    save: bool = True

) -> pd.DataFrame:

    """

    Compute per-week ROI and cumulative ROI for the season across chosen bet types.

    Saves artifacts/weekly_roi.csv by default.

    """

    d = df.copy()



    bets = []

    if include_spread:

        sb = d[d['spread_bet'].notna()][['season','week','spread_result']].copy()

        sb['roi'] = _bet_outcome_to_roi(sb['spread_result'].values, price_spread)

        bets.append(sb.rename(columns={'spread_result':'result'}))

    if include_total:

        tb = d[d['total_bet'].notna()][['season','week','total_result']].copy()

        tb['roi'] = _bet_outcome_to_roi(tb['total_result'].values, price_total)

        bets.append(tb.rename(columns={'total_result':'result'}))



    all_bets = pd.concat(bets, ignore_index=True) if bets else pd.DataFrame(columns=['season','week','result','roi'])

    weekly = all_bets.groupby(['season','week']).agg(

        bets=('roi','size'),

        roi=('roi','mean')

    ).reset_index().sort_values(['season','week'])



    weekly['cum_bets'] = weekly['bets'].cumsum()

    weekly['cum_roi'] = (weekly['roi'] * weekly['bets']).cumsum() / weekly['cum_bets']



    if save:

        weekly.to_csv(WEEKLY_ROI_CSV, index=False)



    return weekly





# ----------------------------

# 5) ONE-CALL DRIVER

# ----------------------------



def run_bias_pipeline(

    df_backtest: pd.DataFrame,

    team_for_curve: Optional[str] = "PIT",

    save_artifacts: bool = True

) -> Dict[str, pd.DataFrame]:

    """

    Convenience function:

      - logs residuals

      - writes bias history

      - writes weekly ROI

      - saves calibration plots for spread and totals

    """

    hist = log_residuals(df_backtest, save=save_artifacts)

    weekly = weekly_roi(df_backtest, save=save_artifacts)



    # Save both "ALL teams" and focused team curves for spreads

    _ = calibration_curve_spread(df_backtest, team=None,

                                 save_png=ARTIFACTS_DIR / "calibration_spread_all.png" if save_artifacts else None)

    if team_for_curve:

        _ = calibration_curve_spread(df_backtest, team=team_for_curve,

                                     save_png=ARTIFACTS_DIR / f"calibration_spread_{team_for_curve}.png" if save_artifacts else None)



    _ = calibration_curve_total(df_backtest,

                                save_png=ARTIFACTS_DIR / "calibration_total_all.png" if save_artifacts else None)



    return {'bias_history': hist, 'weekly_roi': weekly}

