
import pandas as pd, numpy as np

def build_features(teamweeks: pd.DataFrame, recent_weight: float = 0.67) -> pd.DataFrame:
    df = teamweeks.sort_values(["team","week"]).copy()
    g = df.groupby("team", as_index=False)
    for col in ["off_epa_per_play","def_epa_per_play","off_success_rate","def_success_rate","points","points_allowed","turnover_diff"]:
        if col not in df.columns: raise RuntimeError(f"Missing required column: {col}")
        df[f"{col}_season"] = g[col].transform(lambda s: s.expanding().mean())
        df[f"{col}_last4"]  = g[col].transform(lambda s: s.rolling(4, min_periods=1).mean())
    def blend(col): return recent_weight*df[f"{col}_last4"] + (1-recent_weight)*df[f"{col}_season"]
    out = df.sort_values(["team","week"]).groupby("team").tail(1).copy()
    out["OFF_EPA"] = blend("off_epa_per_play"); out["DEF_EPA"] = blend("def_epa_per_play")
    out["OFF_SR"]  = blend("off_success_rate");  out["DEF_SR"]  = blend("def_success_rate")
    out["PF_BLEND"] = blend("points");           out["PA_BLEND"] = blend("points_allowed")
    out["TO_DIFF"] = blend("turnover_diff")
    
    # Apply regression to mean: cap extreme EPA values at ±0.10 to prevent overestimation
    # This prevents teams with outlier 2024 seasons from being overestimated in 2025
    # 0.10 is ~1.5 standard deviations from the mean, catching true outliers like DAL
    EPA_CAP = 0.10
    out["OFF_EPA"] = out["OFF_EPA"].clip(-EPA_CAP, EPA_CAP)
    out["DEF_EPA"] = out["DEF_EPA"].clip(-EPA_CAP, EPA_CAP)
    
    return out[["team","OFF_EPA","DEF_EPA","OFF_SR","DEF_SR","PF_BLEND","PA_BLEND","TO_DIFF"]]

def join_matchups(feats: pd.DataFrame, sched):
    f = feats.set_index("team"); rows = []
    for away, home in sched:
        if away not in f.index or home not in f.index:
            raise RuntimeError(f"Missing features for matchup {away}@{home}")
        a, h = f.loc[away], f.loc[home]
        rows.append({"away": away, "home": home,
            "away_OFF_EPA": a["OFF_EPA"], "home_DEF_EPA": h["DEF_EPA"],
            "home_OFF_EPA": h["OFF_EPA"], "away_DEF_EPA": a["DEF_EPA"],
            "away_OFF_SR": a["OFF_SR"],   "home_DEF_SR": h["DEF_SR"],
            "home_OFF_SR": h["OFF_SR"],   "away_DEF_SR": a["DEF_SR"],
            "away_PF": a["PF_BLEND"],     "home_PA": h["PA_BLEND"],
            "home_PF": h["PF_BLEND"],     "away_PA": a["PA_BLEND"],
            "away_TO_DIFF": a["TO_DIFF"], "home_TO_DIFF": h["TO_DIFF"],})
    return pd.DataFrame(rows)

def apply_weather_and_injuries(matches: pd.DataFrame, weather_df: pd.DataFrame, injuries_df: pd.DataFrame, situational_df: pd.DataFrame = None):
    out = matches.merge(weather_df, on=["away","home"], how="inner")
    inj = injuries_df.set_index("team")["injury_index"] if not injuries_df.empty else {}
    out["away_injury"] = out["away"].map(inj).fillna(0.0); out["home_injury"] = out["home"].map(inj).fillna(0.0)
    
    # Merge situational features if provided
    if situational_df is not None and not situational_df.empty:
        out = out.merge(situational_df, on=["away", "home"], how="left")
        # Fill missing values
        for col in ['away_travel_miles', 'home_travel_miles', 'timezone_diff', 'is_divisional', 'is_conference', 'week_in_season', 'away_rest_days', 'home_rest_days']:
            if col in out.columns:
                out[col] = out[col].fillna(0.0 if 'miles' in col or 'timezone' in col or 'rest' in col else 0)
    
    wind_penalty = np.clip((out["wind_kph"] - 25)/20, 0, 0.15)
    
    # Enhanced adjustments with travel and rest penalties
    travel_penalty_away = 0.0
    rest_penalty_away = 0.0
    rest_penalty_home = 0.0
    divisional_chaos = 0.0
    
    if 'away_travel_miles' in out.columns:
        # Long travel (>1500 miles) = -0.5 points
        travel_penalty_away = np.clip((out["away_travel_miles"] - 1500) / 2000, 0, 0.5)
    
    if 'away_rest_days' in out.columns:
        # Short rest (<6 days) = -1.5 points
        rest_penalty_away = np.where(out["away_rest_days"] < 6, 1.5, 0.0)
    
    if 'home_rest_days' in out.columns:
        rest_penalty_home = np.where(out["home_rest_days"] < 6, 1.5, 0.0)
    
    # Removed divisional_chaos - it made predictions worse
    
    out["home_PF_adj"] = out["home_PF"] * (1 - wind_penalty*(1 - out["is_dome"])) - 0.8*out["home_injury"] - rest_penalty_home
    out["away_PF_adj"] = out["away_PF"] * (1 - wind_penalty*(1 - out["is_dome"])) - 0.8*out["away_injury"] - travel_penalty_away - rest_penalty_away
    
    return out
