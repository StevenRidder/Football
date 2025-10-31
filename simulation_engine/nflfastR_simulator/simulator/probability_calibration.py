"""
Probability Calibration: Convert raw simulator output to calibrated probabilities.

Uses z-scores (normalized by simulator SD) as features and isotonic/Platt scaling
for calibration. Completely separate from UI centering.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, Callable
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.base import BaseEstimator
import warnings


class PlattScaling:
    """
    Platt scaling (logistic regression) for probability calibration.
    
    Maps z-score to probability: P = sigmoid(β₀ + β₁·z)
    """
    
    def __init__(self, regularization: float = 1e-6):
        self.model: Optional[LogisticRegression] = None
        self.is_fitted: bool = False
        self.regularization = regularization
    
    def fit(self, z_scores: np.ndarray, outcomes: np.ndarray):
        """
        Fit Platt scaling.
        
        Args:
            z_scores: Normalized deltas (sim_mean - market) / sim_sd
            outcomes: Binary outcomes (1 = positive event, 0 = negative)
        """
        z_scores = np.asarray(z_scores).reshape(-1, 1)
        outcomes = np.asarray(outcomes).astype(int)
        
        self.model = LogisticRegression(
            fit_intercept=True,
            C=1.0 / self.regularization,
            max_iter=1000
        )
        self.model.fit(z_scores, outcomes)
        self.is_fitted = True
    
    def predict_proba(self, z_scores: np.ndarray) -> np.ndarray:
        """Predict probabilities from z-scores."""
        if not self.is_fitted:
            raise ValueError("Calibrator not fitted")
        
        z_scores = np.asarray(z_scores).reshape(-1, 1)
        prob = self.model.predict_proba(z_scores)[:, 1]
        return prob


class ProbabilityCalibrator:
    """
    Calibrate raw simulator probabilities using z-scores and isotonic/Platt scaling.
    
    Features: z = (sim_mean - market) / sim_sd
    Target: Binary outcome (cover/not cover)
    Method: Isotonic (preferred) or Platt (fallback)
    """
    
    def __init__(self, method: str = 'isotonic', z_cap: float = 3.0):
        """
        Args:
            method: 'isotonic' (monotone) or 'platt' (logistic)
            z_cap: Cap |z| at this value to avoid instability
        """
        self.method = method
        self.z_cap = z_cap
        self.isotonic: Optional[IsotonicRegression] = None
        self.platt: Optional[PlattScaling] = None
        self.is_fitted: bool = False
        
        if method == 'isotonic':
            self.isotonic = IsotonicRegression(out_of_bounds='clip')
        elif method == 'platt':
            self.platt = PlattScaling()
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def fit_from_historical(self,
                           sim_spreads: np.ndarray,
                           sim_sds: np.ndarray,
                           market_spreads: np.ndarray,
                           outcomes: np.ndarray):
        """
        Fit calibrator on historical data.
        
        Args:
            sim_spreads: Raw simulator spread means
            sim_sds: Raw simulator spread standard deviations
            market_spreads: Market spread lines
            outcomes: Actual outcomes (1 = home covered, 0 = away covered)
        """
        # Calculate z-scores
        z_scores = self._calculate_z_scores(sim_spreads, sim_sds, market_spreads)
        
        # Filter out pushes (0.5) and invalid outcomes
        valid_mask = ~np.isnan(outcomes) & (outcomes != 0.5)
        z_scores = z_scores[valid_mask]
        outcomes = outcomes[valid_mask].astype(int)
        
        if len(z_scores) < 50:
            warnings.warn(f"Only {len(z_scores)} samples for calibration (minimum recommended: 50)")
        
        # Fit calibrator
        if self.method == 'isotonic':
            self.isotonic.fit(z_scores, outcomes)
        else:
            self.platt.fit(z_scores, outcomes)
        
        self.is_fitted = True
        
        print(f"✅ Calibrator fitted ({self.method})")
        print(f"   Samples: {len(z_scores)}")
        print(f"   z-score range: [{z_scores.min():.2f}, {z_scores.max():.2f}]")
        print(f"   Outcome rate: {outcomes.mean():.1%}")
    
    def _calculate_z_scores(self,
                            sim_means: np.ndarray,
                            sim_sds: np.ndarray,
                            market_values: np.ndarray) -> np.ndarray:
        """Calculate z-scores with capping."""
        deltas = sim_means - market_values
        # Avoid division by zero
        sim_sds = np.maximum(sim_sds, 1e-6)
        z_scores = deltas / sim_sds
        
        # Cap extreme z-scores
        z_scores = np.clip(z_scores, -self.z_cap, self.z_cap)
        
        return z_scores
    
    def predict_proba(self,
                     sim_mean: float,
                     sim_sd: float,
                     market_value: float) -> float:
        """
        Predict calibrated probability from raw simulator output.
        
        Args:
            sim_mean: Raw simulator mean
            sim_sd: Raw simulator standard deviation
            market_value: Market line
        
        Returns:
            Calibrated probability
        """
        if not self.is_fitted:
            # Fallback: simple sigmoid
            delta = sim_mean - market_value
            sim_sd = max(sim_sd, 1e-6)
            z = np.clip(delta / sim_sd, -self.z_cap, self.z_cap)
            prob = 1.0 / (1.0 + np.exp(-0.5 * z))  # Rough approximation
            return float(prob)
        
        # Calculate z-score
        z = self._calculate_z_scores(
            np.array([sim_mean]),
            np.array([sim_sd]),
            np.array([market_value])
        )[0]
        
        # Predict probability
        if self.method == 'isotonic':
            prob = self.isotonic.predict([z])[0]
        else:
            prob = self.platt.predict_proba(np.array([z]))[0]
        
        return float(np.clip(prob, 0.0, 1.0))


class AdaptiveEnsemble:
    """
    Data-driven blending with adaptive α based on |z| and sample size.
    
    P_final = α(|z|) · P_model + (1 - α(|z|)) · P_neutral
    
    where P_neutral = 0.50 (not 0.524!)
    """
    
    def __init__(self, alpha_fn: Optional[Callable[[float], float]] = None):
        """
        Args:
            alpha_fn: Function mapping |z| to α. Default: linear from 0.6 to 0.9
        """
        if alpha_fn is None:
            # Default: α = 0.6 + 0.3 * min(|z| / 2.0, 1.0)
            # At |z|=0: α=0.6, at |z|≥2: α=0.9
            alpha_fn = lambda z: 0.6 + 0.3 * min(abs(z) / 2.0, 1.0)
        
        self.alpha_fn = alpha_fn
        self.neutral_prob = 0.50  # NOT 0.524!
    
    def blend(self, model_prob: float, z_score: float) -> float:
        """
        Blend model probability with neutral baseline.
        
        Args:
            model_prob: Calibrated model probability
            z_score: Z-score (for adaptive α)
        
        Returns:
            Blended probability
        """
        alpha = self.alpha_fn(z_score)
        blended = alpha * model_prob + (1 - alpha) * self.neutral_prob
        return float(np.clip(blended, 0.0, 1.0))


def calculate_z_scores(sim_means: np.ndarray,
                       sim_sds: np.ndarray,
                       market_values: np.ndarray,
                       z_cap: float = 3.0) -> np.ndarray:
    """
    Calculate z-scores for calibration features.
    
    Args:
        sim_means: Simulator means
        sim_sds: Simulator standard deviations
        market_values: Market lines
        z_cap: Cap |z| at this value
    
    Returns:
        Z-scores
    """
    deltas = sim_means - market_values
    sim_sds = np.maximum(sim_sds, 1e-6)  # Avoid division by zero
    z_scores = deltas / sim_sds
    z_scores = np.clip(z_scores, -z_cap, z_cap)
    return z_scores


def calibrate_probabilities(raw_spread_mean: float,
                           raw_spread_sd: float,
                           market_spread: float,
                           spread_calibrator: Optional[ProbabilityCalibrator] = None,
                           ensemble: Optional[AdaptiveEnsemble] = None) -> Dict:
    """
    Calibrate spread probabilities from raw simulator output.
    
    IMPORTANT: This uses raw simulator output, NOT centered distributions.
    
    Args:
        raw_spread_mean: Raw simulator spread mean
        raw_spread_sd: Raw simulator spread standard deviation
        market_spread: Market spread line
        spread_calibrator: Fitted ProbabilityCalibrator
        ensemble: Optional AdaptiveEnsemble for conservative blending
    
    Returns:
        Dict with calibrated probabilities
    """
    # Calculate z-score
    z_spread = calculate_z_scores(
        np.array([raw_spread_mean]),
        np.array([raw_spread_sd]),
        np.array([market_spread])
    )[0]
    
    # Get calibrated probability
    if spread_calibrator and spread_calibrator.is_fitted:
        p_home_cover = spread_calibrator.predict_proba(
            raw_spread_mean, raw_spread_sd, market_spread
        )
    else:
        # Fallback: simple sigmoid
        p_home_cover = 1.0 / (1.0 + np.exp(-0.5 * z_spread))
    
    # Optional ensemble blending
    if ensemble:
        p_home_cover = ensemble.blend(p_home_cover, z_spread)
    
    p_away_cover = 1.0 - p_home_cover
    
    return {
        'p_home_cover': float(p_home_cover),
        'p_away_cover': float(p_away_cover),
        'z_spread': float(z_spread),
        'raw_spread_mean': float(raw_spread_mean),
        'raw_spread_sd': float(raw_spread_sd),
        'market_spread': float(market_spread),
        'calibration_method': 'calibrated' if (spread_calibrator and spread_calibrator.is_fitted) else 'fallback',
        'ensemble_applied': ensemble is not None
    }


def calibrate_total_probabilities(raw_total_mean: float,
                                  raw_total_sd: float,
                                  market_total: float,
                                  total_calibrator: Optional[ProbabilityCalibrator] = None,
                                  ensemble: Optional[AdaptiveEnsemble] = None) -> Dict:
    """
    Calibrate total probabilities (same structure as spreads).
    
    Args:
        raw_total_mean: Raw simulator total mean
        raw_total_sd: Raw simulator total standard deviation
        market_total: Market total line
        total_calibrator: Fitted ProbabilityCalibrator for totals
        ensemble: Optional AdaptiveEnsemble
    
    Returns:
        Dict with calibrated probabilities
    """
    # Calculate z-score
    z_total = calculate_z_scores(
        np.array([raw_total_mean]),
        np.array([raw_total_sd]),
        np.array([market_total])
    )[0]
    
    # Get calibrated probability
    if total_calibrator and total_calibrator.is_fitted:
        p_over = total_calibrator.predict_proba(
            raw_total_mean, raw_total_sd, market_total
        )
    else:
        # Fallback: simple sigmoid
        p_over = 1.0 / (1.0 + np.exp(-0.5 * z_total))
    
    # Optional ensemble blending
    if ensemble:
        p_over = ensemble.blend(p_over, z_total)
    
    p_under = 1.0 - p_over
    
    return {
        'p_over': float(p_over),
        'p_under': float(p_under),
        'z_total': float(z_total),
        'raw_total_mean': float(raw_total_mean),
        'raw_total_sd': float(raw_total_sd),
        'market_total': float(market_total),
        'calibration_method': 'calibrated' if (total_calibrator and total_calibrator.is_fitted) else 'fallback',
        'ensemble_applied': ensemble is not None
    }


# Example usage and testing
if __name__ == "__main__":
    print("="*70)
    print("PROBABILITY CALIBRATION TEST (z-score based)")
    print("="*70)
    
    # Simulate data
    np.random.seed(42)
    n_samples = 200
    
    # Simulator thinks mean=5, sd=12
    sim_spreads = np.random.normal(5.0, 12.0, n_samples)
    sim_sds = np.full(n_samples, 12.0)
    market_spread = -3.0
    
    # Outcomes (home covers if sim > market roughly)
    outcomes = (sim_spreads - market_spread > np.random.normal(0, 8, n_samples)).astype(float)
    
    print(f"\nSimulated data:")
    print(f"  Sim spreads: mean={sim_spreads.mean():.1f}, sd={sim_spreads.std():.1f}")
    print(f"  Market spread: {market_spread:.1f}")
    print(f"  Outcome rate: {outcomes.mean():.1%}")
    
    # Test isotonic calibration
    print(f"\n1. ISOTONIC CALIBRATION:")
    calibrator_iso = ProbabilityCalibrator(method='isotonic', z_cap=3.0)
    calibrator_iso.fit_from_historical(sim_spreads, sim_sds, 
                                      np.full(n_samples, market_spread), outcomes)
    
    test_z = 0.5
    test_mean = market_spread + test_z * 12.0
    test_sd = 12.0
    prob_iso = calibrator_iso.predict_proba(test_mean, test_sd, market_spread)
    print(f"   z={test_z:.1f} → P(home cover)={prob_iso:.1%}")
    
    # Test Platt scaling
    print(f"\n2. PLATT SCALING:")
    calibrator_platt = ProbabilityCalibrator(method='platt', z_cap=3.0)
    calibrator_platt.fit_from_historical(sim_spreads, sim_sds,
                                        np.full(n_samples, market_spread), outcomes)
    prob_platt = calibrator_platt.predict_proba(test_mean, test_sd, market_spread)
    print(f"   z={test_z:.1f} → P(home cover)={prob_platt:.1%}")
    
    # Test ensemble
    print(f"\n3. ADAPTIVE ENSEMBLE:")
    ensemble = AdaptiveEnsemble()
    prob_blended = ensemble.blend(prob_iso, test_z)
    print(f"   Model: {prob_iso:.1%}, Blended: {prob_blended:.1%}")
    print(f"   α(|z|={test_z:.1f}) = {0.6 + 0.3 * min(test_z / 2.0, 1.0):.2f}")
    
    print("\n" + "="*70)
