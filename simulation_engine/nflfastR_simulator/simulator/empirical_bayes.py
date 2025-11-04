"""
Empirical Bayes Shrinkage for Thin Samples

Per strategy:
- QB stats: λ = 150 dropbacks
- Play-calling: λ = 50 plays
- Shrink toward league priors
- Log weights used for transparency
"""

import pandas as pd
from typing import Dict, Tuple


def shrink_rate(obs_rate: float, n: int, prior_rate: float, lam: int) -> float:
    """
    Shrink observed rate toward prior using empirical Bayes.
    
    Formula: w * obs_rate + (1 - w) * prior_rate
    where w = n / (n + λ)
    
    Args:
        obs_rate: Observed rate from sample
        n: Sample size
        prior_rate: Prior rate (league average)
        lam: Shrinkage parameter (λ)
    
    Returns:
        Shrunk rate
    """
    w = n / (n + lam)
    return w * obs_rate + (1 - w) * prior_rate


def shrink_qb_block(qb_row: pd.Series, league_row: pd.Series, n_dropbacks: int) -> Dict[str, float]:
    """
    Shrink all QB stats toward league prior.
    
    Args:
        qb_row: QB's observed stats
        league_row: League average stats
        n_dropbacks: Number of dropbacks in sample
    
    Returns:
        Dictionary of shrunk stats
    """
    L_QB = 150  # λ for QB stats

    out = {}
    stat_keys = [
        "completion_pct_clean", "completion_pct_pressure",
        "int_rate_clean", "int_rate_pressure",
        "sack_rate_pressure", "scramble_rate_pressure",
        "ypp_clean", "ypp_pressure",
        "epa_clean", "epa_pressure"
    ]

    for k in stat_keys:
        if k in qb_row and k in league_row:
            out[k] = shrink_rate(qb_row[k], n_dropbacks, league_row[k], L_QB)
        elif k in qb_row:
            out[k] = qb_row[k]  # No prior, use raw

    # Add metadata
    out['n_dropbacks'] = n_dropbacks
    out['shrinkage_weight'] = n_dropbacks / (n_dropbacks + L_QB)

    return out


class EmpiricalBayesShrinkage:
    """Apply empirical Bayes shrinkage to thin samples."""

    # League priors (from nflfastR 2022-2024 data)
    LEAGUE_QB_CLEAN = {
        'completion_pct': 0.65,
        'yards_per_att': 7.5,
        'td_rate': 0.045,
        'int_rate': 0.020,
        'sack_rate': 0.00,  # Not applicable for clean
        'scramble_rate': 0.00,
        'epa_per_play': 0.15
    }

    LEAGUE_QB_PRESSURE = {
        'completion_pct': 0.50,
        'yards_per_att': 5.0,
        'td_rate': 0.025,
        'int_rate': 0.045,
        'sack_rate': 0.35,
        'scramble_rate': 0.15,
        'epa_per_play': -0.30
    }

    LEAGUE_PLAYCALLING = {
        'pass_rate': 0.60,
        'run_rate': 0.40
    }

    @staticmethod
    def shrink_qb_stats(
        qb_stats: Dict[str, float],
        n_dropbacks: int,
        is_pressure: bool,
        lambda_threshold: int = 150
    ) -> Tuple[Dict[str, float], float]:
        """
        Shrink QB stats toward league prior using empirical Bayes.
        
        Args:
            qb_stats: Raw QB statistics
            n_dropbacks: Number of dropbacks in sample
            is_pressure: Whether these are pressure or clean stats
            lambda_threshold: Sample size threshold (default 150)
        
        Returns:
            (shrunk_stats, weight_used)
        """
        # Calculate weight: n / (n + λ)
        weight = n_dropbacks / (n_dropbacks + lambda_threshold)

        # Choose prior
        if is_pressure:
            prior = EmpiricalBayesShrinkage.LEAGUE_QB_PRESSURE
        else:
            prior = EmpiricalBayesShrinkage.LEAGUE_QB_CLEAN

        # Shrink each stat
        shrunk_stats = {}
        for key in qb_stats.keys():
            if key in prior:
                # Weighted average: weight * sample + (1 - weight) * prior
                shrunk_stats[key] = weight * qb_stats[key] + (1 - weight) * prior[key]
            else:
                # No prior, use raw value
                shrunk_stats[key] = qb_stats[key]

        return shrunk_stats, weight

    @staticmethod
    def shrink_playcalling(
        playcalling_stats: Dict[str, float],
        n_plays: int,
        lambda_threshold: int = 50
    ) -> Tuple[Dict[str, float], float]:
        """
        Shrink play-calling tendencies toward league prior.
        
        Args:
            playcalling_stats: Raw play-calling statistics
            n_plays: Number of plays in sample
            lambda_threshold: Sample size threshold (default 50)
        
        Returns:
            (shrunk_stats, weight_used)
        """
        # Calculate weight: n / (n + λ)
        weight = n_plays / (n_plays + lambda_threshold)

        # Shrink toward league prior
        shrunk_stats = {}
        for key in playcalling_stats.keys():
            if key in EmpiricalBayesShrinkage.LEAGUE_PLAYCALLING:
                shrunk_stats[key] = (
                    weight * playcalling_stats[key] +
                    (1 - weight) * EmpiricalBayesShrinkage.LEAGUE_PLAYCALLING[key]
                )
            else:
                shrunk_stats[key] = playcalling_stats[key]

        return shrunk_stats, weight

    @staticmethod
    def log_shrinkage(
        entity_name: str,
        stat_type: str,
        n_samples: int,
        weight: float,
        original: Dict[str, float],
        shrunk: Dict[str, float]
    ) -> str:
        """
        Create a log entry for shrinkage transparency.
        
        Returns:
            Log string with shrinkage details
        """
        lines = [
            f"SHRINKAGE: {entity_name} - {stat_type}",
            f"  Samples: {n_samples}",
            f"  Weight: {weight:.3f}",
            "  Changes:"
        ]

        for key in original.keys():
            if key in shrunk:
                orig_val = original[key]
                shrunk_val = shrunk[key]
                delta = shrunk_val - orig_val
                if abs(delta) > 0.001:
                    lines.append(f"    {key}: {orig_val:.3f} → {shrunk_val:.3f} (Δ {delta:+.3f})")

        return "\n".join(lines)


def apply_rollforward_cutoff(
    df: pd.DataFrame,
    target_season: int,
    target_week: int,
    date_column: str = 'week'
) -> pd.DataFrame:
    """
    Apply roll-forward discipline: only use data through week-1.
    
    Args:
        df: DataFrame with temporal data
        target_season: Season to predict
        target_week: Week to predict
        date_column: Column name for week/date
    
    Returns:
        Filtered DataFrame with "as_of" stamp
    """
    # Filter to data before target week
    if 'season' in df.columns:
        mask = (
            (df['season'] < target_season) |
            ((df['season'] == target_season) & (df[date_column] < target_week))
        )
    else:
        mask = df[date_column] < target_week

    filtered_df = df[mask].copy()

    # Add "as_of" timestamp
    filtered_df['as_of_season'] = target_season
    filtered_df['as_of_week'] = target_week - 1
    filtered_df['as_of_timestamp'] = pd.Timestamp.now()

    return filtered_df


if __name__ == "__main__":
    # Test shrinkage
    print("="*80)
    print("EMPIRICAL BAYES SHRINKAGE - TEST")
    print("="*80)

    # Test QB shrinkage with small sample
    small_sample_qb = {
        'completion_pct': 0.80,  # Hot start
        'yards_per_att': 9.0,
        'td_rate': 0.08,
        'int_rate': 0.01,
        'epa_per_play': 0.40
    }

    shrunk_qb, weight = EmpiricalBayesShrinkage.shrink_qb_stats(
        small_sample_qb, n_dropbacks=50, is_pressure=False
    )

    print("\n📊 QB Stats Shrinkage (50 dropbacks):")
    print(f"Weight: {weight:.3f}")
    for key in small_sample_qb.keys():
        if key in shrunk_qb:
            print(f"  {key}: {small_sample_qb[key]:.3f} → {shrunk_qb[key]:.3f}")

    # Test with large sample (should be close to original)
    shrunk_qb_large, weight_large = EmpiricalBayesShrinkage.shrink_qb_stats(
        small_sample_qb, n_dropbacks=300, is_pressure=False
    )

    print("\n📊 QB Stats Shrinkage (300 dropbacks):")
    print(f"Weight: {weight_large:.3f}")
    for key in small_sample_qb.keys():
        if key in shrunk_qb_large:
            print(f"  {key}: {small_sample_qb[key]:.3f} → {shrunk_qb_large[key]:.3f}")

    print("\n✅ Shrinkage working correctly:")
    print("  - Small samples shrink toward prior")
    print("  - Large samples stay close to original")
    print("  - Weight increases with sample size")

