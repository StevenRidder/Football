"""
Kelly sizing and Expected Value calculations for NFL betting.
Converts model probabilities into actionable bet recommendations.
"""

import numpy as np
import pandas as pd


def american_to_decimal(american_odds: float) -> float:
    """Convert American odds (-110, +150) to decimal odds (1.91, 2.50)."""
    if american_odds < 0:
        return 1 + (100 / abs(american_odds))
    else:
        return 1 + (american_odds / 100)


def implied_prob_from_american(american_odds: float) -> float:
    """
    Convert American odds to implied probability.
    
    Examples:
        -110 → 52.4% (favorite)
        +150 → 40.0% (underdog)
    """
    if american_odds < 0:
        return abs(american_odds) / (abs(american_odds) + 100)
    else:
        return 100 / (american_odds + 100)


def calculate_ev(model_prob: float, american_odds: float = -110) -> float:
    """
    Calculate Expected Value (EV) for a bet.
    
    EV = (model_prob × net_win) - ((1 - model_prob) × stake)
    
    Args:
        model_prob: Your model's win probability (0.0 to 1.0)
        american_odds: Market odds (default -110, standard juice)
    
    Returns:
        EV as decimal (0.10 = 10% EV)
    
    Example:
        Model: 60% win probability
        Odds: -110 (need to risk $110 to win $100)
        EV = 0.60 × (100/110) - 0.40 × 1.0 = 0.145 (14.5% EV)
    """
    decimal_odds = american_to_decimal(american_odds)
    net_win_per_dollar = decimal_odds - 1
    ev = (model_prob * net_win_per_dollar) - ((1 - model_prob) * 1.0)
    return ev


def kelly_fraction(model_prob: float, american_odds: float = -110, 
                   max_fraction: float = 0.25) -> float:
    """
    Calculate Kelly Criterion bet size as fraction of bankroll.
    
    Full Kelly: f* = (p × b - (1-p)) / b
    where:
        p = model probability
        b = decimal odds - 1
    
    Args:
        model_prob: Model's win probability
        american_odds: Market odds
        max_fraction: Cap (0.25 = quarter Kelly for safety)
    
    Returns:
        Fraction of bankroll to bet (0.0 to max_fraction)
    
    Example:
        Model: 60% vs -110 odds
        Full Kelly: 14.5%
        Quarter Kelly (capped): 3.6%
    """
    decimal_odds = american_to_decimal(american_odds)
    b = decimal_odds - 1
    
    # Full Kelly formula
    full_kelly = (model_prob * b - (1 - model_prob)) / b
    
    # Cap at max_fraction and floor at 0
    capped_kelly = max(0.0, min(full_kelly, max_fraction))
    
    return capped_kelly


def calculate_confidence_level(predicted_margin: float) -> tuple:
    """
    Calculate confidence level based on predicted margin
    Returns (confidence_level, confidence_pct)
    
    Based on historical analysis:
    - 7-14 pts: 64% accuracy (HIGH confidence)
    - 5-7 or 14-17 pts: 54% accuracy (MEDIUM confidence)  
    - <5 or >17 pts: 46% accuracy (LOW confidence)
    """
    abs_margin = abs(predicted_margin)
    
    if 7 <= abs_margin <= 14:
        return ("HIGH", 64)
    elif (5 <= abs_margin < 7) or (14 < abs_margin <= 17):
        return ("MEDIUM", 54)
    else:
        return ("LOW", 46)


def add_betting_columns(df: pd.DataFrame, 
                       bankroll: float = 10000.0,
                       vig: int = -110,
                       min_ev: float = 0.02,
                       kelly_fraction_cap: float = 0.25) -> pd.DataFrame:
    """
    Add EV, Kelly sizing, confidence levels, and bet recommendations to projections.
    
    Args:
        df: Projections dataframe with probabilities
        bankroll: Starting bankroll for stake calculations
        vig: American odds (default -110)
        min_ev: Minimum EV to recommend a bet (default 2%)
        kelly_fraction_cap: Max Kelly fraction (default 25%)
    
    Returns:
        DataFrame with additional columns:
            - EV_spread: Expected value on spread bet
            - EV_total: Expected value on total bet
            - Kelly_spread_pct: Kelly % for spread
            - Kelly_total_pct: Kelly % for total
            - Stake_spread: Dollar amount for spread
            - Stake_total: Dollar amount for total
            - Rec_spread: Recommendation text
            - Rec_total: Recommendation text
            - Best_bet: Overall best play for this game
    """
    df = df.copy()
    
    # Convert percentages to probabilities
    home_cover_prob = df["Home cover %"] / 100.0
    away_cover_prob = 1.0 - home_cover_prob
    over_prob = df["Over %"] / 100.0
    under_prob = 1.0 - over_prob
    
    # Calculate EV for each bet type
    df["EV_home_cover"] = [calculate_ev(p, vig) for p in home_cover_prob]
    df["EV_away_cover"] = [calculate_ev(p, vig) for p in away_cover_prob]
    df["EV_over"] = [calculate_ev(p, vig) for p in over_prob]
    df["EV_under"] = [calculate_ev(p, vig) for p in under_prob]
    
    # Best spread side (home or away)
    df["EV_spread"] = np.maximum(df["EV_home_cover"], df["EV_away_cover"])
    df["Spread_side"] = ["HOME" if h > a else "AWAY" 
                         for h, a in zip(df["EV_home_cover"], df["EV_away_cover"])]
    df["Spread_prob"] = [h if h > a else a 
                         for h, a in zip(home_cover_prob, away_cover_prob)]
    
    # Best total side (over or under)
    df["EV_total"] = np.maximum(df["EV_over"], df["EV_under"])
    df["Total_side"] = ["OVER" if o > u else "UNDER" 
                        for o, u in zip(df["EV_over"], df["EV_under"])]
    df["Total_prob"] = [o if o > u else u 
                        for o, u in zip(over_prob, under_prob)]
    
    # Kelly sizing
    df["Kelly_spread_pct"] = [kelly_fraction(p, vig, kelly_fraction_cap) * 100 
                              for p in df["Spread_prob"]]
    df["Kelly_total_pct"] = [kelly_fraction(p, vig, kelly_fraction_cap) * 100 
                             for p in df["Total_prob"]]
    
    # Dollar stakes
    df["Stake_spread"] = (df["Kelly_spread_pct"] / 100.0) * bankroll
    df["Stake_total"] = (df["Kelly_total_pct"] / 100.0) * bankroll
    
    # Recommendations
    recs_spread = []
    recs_total = []
    
    for _, r in df.iterrows():
        # Spread recommendation
        if r["EV_spread"] >= min_ev:
            team = r["home"] if r["Spread_side"] == "HOME" else r["away"]
            line = r["Spread used (home-)"]
            if r["Spread_side"] == "AWAY":
                line = -line
            ev_pct = r["EV_spread"] * 100
            prob_pct = r["Spread_prob"] * 100
            recs_spread.append(
                f"BET {team} {line:+.1f} @ {r['Kelly_spread_pct']:.1f}% "
                f"(EV: {ev_pct:+.1f}%, Prob: {prob_pct:.1f}%)"
            )
        else:
            recs_spread.append("SKIP")
        
        # Total recommendation
        if r["EV_total"] >= min_ev:
            side = r["Total_side"]
            line = r["Total used"]
            ev_pct = r["EV_total"] * 100
            prob_pct = r["Total_prob"] * 100
            recs_total.append(
                f"BET {side} {line:.1f} @ {r['Kelly_total_pct']:.1f}% "
                f"(EV: {ev_pct:+.1f}%, Prob: {prob_pct:.1f}%)"
            )
        else:
            recs_total.append("SKIP")
    
    df["Rec_spread"] = recs_spread
    df["Rec_total"] = recs_total
    
    # Overall best bet for this game
    best_bets = []
    for _, r in df.iterrows():
        if r["EV_spread"] >= min_ev and r["EV_total"] >= min_ev:
            if r["EV_spread"] > r["EV_total"]:
                best_bets.append(f"SPREAD: {r['Rec_spread']}")
            else:
                best_bets.append(f"TOTAL: {r['Rec_total']}")
        elif r["EV_spread"] >= min_ev:
            best_bets.append(f"SPREAD: {r['Rec_spread']}")
        elif r["EV_total"] >= min_ev:
            best_bets.append(f"TOTAL: {r['Rec_total']}")
        else:
            best_bets.append("NO PLAY")
    
    df["Best_bet"] = best_bets
    
    # Add confidence levels based on predicted margin
    confidence_levels = []
    confidence_pcts = []
    
    for _, r in df.iterrows():
        predicted_margin = abs(r["Model spread home-"])
        conf_level, conf_pct = calculate_confidence_level(predicted_margin)
        confidence_levels.append(conf_level)
        confidence_pcts.append(conf_pct)
    
    df["confidence_level"] = confidence_levels
    df["confidence_pct"] = confidence_pcts
    
    return df


def generate_betting_card(df: pd.DataFrame, min_ev: float = 0.02) -> str:
    """
    Generate human-readable betting card with ranked recommendations.
    
    Args:
        df: Projections with betting columns added
        min_ev: Minimum EV to include (default 2%)
    
    Returns:
        Formatted text report
    """
    # Gather all bets with positive EV
    bets = []
    
    for _, r in df.iterrows():
        if r["EV_spread"] >= min_ev:
            bets.append({
                "game": f"{r['away']}@{r['home']}",
                "type": "SPREAD",
                "rec": r["Rec_spread"],
                "ev": r["EV_spread"],
                "stake": r["Stake_spread"]
            })
        
        if r["EV_total"] >= min_ev:
            bets.append({
                "game": f"{r['away']}@{r['home']}",
                "type": "TOTAL",
                "rec": r["Rec_total"],
                "ev": r["EV_total"],
                "stake": r["Stake_total"]
            })
    
    # Sort by EV descending
    bets.sort(key=lambda x: x["ev"], reverse=True)
    
    # Format report
    lines = []
    lines.append("=" * 80)
    lines.append("NFL WEEKLY BETTING CARD - Ranked by Expected Value")
    lines.append("=" * 80)
    lines.append(f"\nFound {len(bets)} plays with EV ≥ {min_ev*100:.0f}%\n")
    
    if not bets:
        lines.append("NO PLAYS meet minimum EV threshold. Stay disciplined.")
    else:
        total_stake = sum(b["stake"] for b in bets)
        lines.append(f"Total recommended stake: ${total_stake:,.0f}\n")
        
        for i, bet in enumerate(bets, 1):
            lines.append(f"\n{i}. {bet['game']} - {bet['type']}")
            lines.append(f"   {bet['rec']}")
            lines.append(f"   Stake: ${bet['stake']:,.0f}")
    
    lines.append("\n" + "=" * 80)
    
    return "\n".join(lines)


