
import numpy as np
def monte_carlo(mu_away, mu_home, team_sd: float, n_sims: int, spread_home=None, total_line=None):
    mu_away = np.asarray(mu_away, dtype=float); mu_home = np.asarray(mu_home, dtype=float)
    n_games = len(mu_away)
    away = np.random.normal(mu_away, team_sd, (n_sims, n_games))
    home = np.random.normal(mu_home, team_sd, (n_sims, n_games))
    diff = home - away; total = home + away
    model_spread = diff.mean(axis=0); model_total = total.mean(axis=0)
    if spread_home is None or total_line is None:
        raise RuntimeError("Market lines required (no fallback).")
    over = (total > total_line).mean(axis=0); home_cover = (diff > -spread_home).mean(axis=0); home_win = (diff > 0).mean(axis=0)
    return {"model_spread_home": model_spread, "model_total": model_total,
            "spread_used": spread_home, "total_used": total_line,
            "over_prob": over, "home_cover_prob": home_cover, "home_win_prob": home_win}
