
import pandas as pd, numpy as np

def build_features(teamweeks: pd.DataFrame, recent_weight: float = 0.67) -> pd.DataFrame:
    df = teamweeks.sort_values(["team","week"]).copy()
    g = df.groupby("team", as_index=False)
    for col in ["off_epa_per_play","def_epa_per_play","off_success_rate","def_success_rate","points","points_allowed"]:
        if col not in df.columns: raise RuntimeError(f"Missing required column: {col}")
        df[f"{col}_season"] = g[col].transform(lambda s: s.expanding().mean())
        df[f"{col}_last4"]  = g[col].transform(lambda s: s.rolling(4, min_periods=1).mean())
    def blend(col): return recent_weight*df[f"{col}_last4"] + (1-recent_weight)*df[f"{col}_season"]
    out = df.sort_values(["team","week"]).groupby("team").tail(1).copy()
    out["OFF_EPA"] = blend("off_epa_per_play"); out["DEF_EPA"] = blend("def_epa_per_play")
    out["OFF_SR"]  = blend("off_success_rate");  out["DEF_SR"]  = blend("def_success_rate")
    out["PF_BLEND"] = blend("points");           out["PA_BLEND"] = blend("points_allowed")
    return out[["team","OFF_EPA","DEF_EPA","OFF_SR","DEF_SR","PF_BLEND","PA_BLEND"]]

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
            "home_PF": h["PF_BLEND"],     "away_PA": a["PA_BLEND"],})
    return pd.DataFrame(rows)

def apply_weather_and_injuries(matches: pd.DataFrame, weather_df: pd.DataFrame, injuries_df: pd.DataFrame):
    out = matches.merge(weather_df, on=["away","home"], how="inner")
    inj = injuries_df.set_index("team")["injury_index"] if not injuries_df.empty else {}
    out["away_injury"] = out["away"].map(inj).fillna(0.0); out["home_injury"] = out["home"].map(inj).fillna(0.0)
    wind_penalty = np.clip((out["wind_kph"] - 25)/20, 0, 0.15)
    out["home_PF_adj"] = out["home_PF"] * (1 - wind_penalty*(1 - out["is_dome"])) - 0.8*out["home_injury"]
    out["away_PF_adj"] = out["away_PF"] * (1 - wind_penalty*(1 - out["is_dome"])) - 0.8*out["away_injury"]
    return out
