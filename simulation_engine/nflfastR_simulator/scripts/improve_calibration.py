"""
Advanced calibration improvements:
1. Non-linear calibration (isotonic/spline)
2. Regime-specific models (indoor/outdoor, high/low totals)
3. Dynamic bet sizing (fractional Kelly)
4. Walk-forward refresh
"""
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import norm
from sklearn.isotonic import IsotonicRegression
from scipy.interpolate import UnivariateSpline
import warnings

class AdvancedProbabilityCalibrator:
    """
    Advanced probability calibration with:
    - Non-linear mapping (isotonic/spline)
    - Regime-specific models
    - Out-of-bounds handling
    """
    
    def __init__(self, method: str = 'isotonic', regime_col: str = None, z_cap: float = 3.0):
        """
        Args:
            method: 'isotonic' (monotone) or 'spline' (smooth curve)
            regime_col: Column to split by regime (e.g., 'is_dome', 'total_regime')
            z_cap: Cap |z| at this value
        """
        self.method = method
        self.regime_col = regime_col
        self.z_cap = z_cap
        self.calibrators = {}  # Dict of regime -> calibrator
        self.is_fitted = False
        
    def fit_from_historical(self,
                           sim_means: np.ndarray,
                           sim_sds: np.ndarray,
                           market_values: np.ndarray,
                           outcomes: np.ndarray,
                           regime_values: np.ndarray = None):
        """
        Fit calibrators on historical data.
        
        Args:
            sim_means: Raw simulator means (spread or total)
            sim_sds: Raw simulator standard deviations
            market_values: Market lines
            outcomes: Actual outcomes (1 = over/cover, 0 = under/no cover)
            regime_values: Optional regime labels for splitting
        """
        # Calculate z-scores
        z_scores = self._calculate_z_scores(sim_means, sim_sds, market_values)
        
        # Filter valid outcomes
        valid_mask = ~np.isnan(outcomes) & (outcomes != 0.5) & ~np.isnan(z_scores)
        z_scores = z_scores[valid_mask]
        outcomes = outcomes[valid_mask].astype(int)
        
        if len(z_scores) < 50:
            warnings.warn(f"Only {len(z_scores)} samples (minimum: 50)")
        
        # Split by regime if provided
        if regime_values is not None and self.regime_col is not None:
            regimes = regime_values[valid_mask]
            unique_regimes = np.unique(regimes[~pd.isna(regimes)])
            
            for regime in unique_regimes:
                regime_mask = regimes == regime
                if regime_mask.sum() < 20:
                    continue  # Need at least 20 samples per regime
                
                z_regime = z_scores[regime_mask]
                y_regime = outcomes[regime_mask]
                
                calibrator = self._fit_single(z_regime, y_regime)
                self.calibrators[regime] = calibrator
                print(f"✅ Fitted {self.method} calibrator for regime '{regime}': {len(z_regime)} samples")
        else:
            # Single global calibrator
            calibrator = self._fit_single(z_scores, outcomes)
            self.calibrators['global'] = calibrator
            print(f"✅ Fitted {self.method} calibrator (global): {len(z_scores)} samples")
        
        self.is_fitted = True
    
    def _fit_single(self, z_scores: np.ndarray, outcomes: np.ndarray):
        """Fit a single calibrator."""
        if self.method == 'isotonic':
            # Isotonic regression (monotone, data-driven)
            calibrator = IsotonicRegression(out_of_bounds='clip')
            calibrator.fit(z_scores, outcomes)
            return calibrator
        elif self.method == 'spline':
            # Smooth spline (allows slight non-monotonicity if data suggests it)
            # Sort by z-score for monotonicity
            sort_idx = np.argsort(z_scores)
            z_sorted = z_scores[sort_idx]
            y_sorted = outcomes[sort_idx]
            
            # Use smoothing spline
            spline = UnivariateSpline(z_sorted, y_sorted, s=len(z_sorted)*0.1, k=3)
            return spline
        else:
            raise ValueError(f"Unknown method: {self.method}")
    
    def predict(self, 
                sim_means: np.ndarray,
                sim_sds: np.ndarray,
                market_values: np.ndarray,
                regime_values: np.ndarray = None) -> np.ndarray:
        """
        Predict calibrated probabilities.
        
        Returns:
            Array of calibrated probabilities (0 to 1)
        """
        if not self.is_fitted:
            raise ValueError("Calibrator not fitted yet")
        
        z_scores = self._calculate_z_scores(sim_means, sim_sds, market_values)
        probs = np.zeros(len(z_scores))
        
        # Use regime-specific or global
        if regime_values is not None and self.regime_col is not None:
            for regime, calibrator in self.calibrators.items():
                if regime == 'global':
                    continue
                regime_mask = (regime_values == regime)
                if regime_mask.sum() > 0:
                    probs[regime_mask] = self._predict_single(calibrator, z_scores[regime_mask])
            
            # Fill remaining with global if available
            if 'global' in self.calibrators:
                remaining_mask = (probs == 0)
                probs[remaining_mask] = self._predict_single(
                    self.calibrators['global'], z_scores[remaining_mask]
                )
        else:
            # Use global calibrator
            probs = self._predict_single(self.calibrators['global'], z_scores)
        
        return np.clip(probs, 0.01, 0.99)
    
    def _predict_single(self, calibrator, z_scores: np.ndarray) -> np.ndarray:
        """Predict from a single calibrator."""
        if self.method == 'isotonic':
            return calibrator.predict(z_scores)
        elif self.method == 'spline':
            return np.clip(calibrator(z_scores), 0.0, 1.0)
    
    def _calculate_z_scores(self,
                            sim_means: np.ndarray,
                            sim_sds: np.ndarray,
                            market_values: np.ndarray) -> np.ndarray:
        """Calculate z-scores with capping."""
        deltas = sim_means - market_values
        sim_sds = np.maximum(sim_sds, 1e-6)
        z_scores = deltas / sim_sds
        z_scores = np.clip(z_scores, -self.z_cap, self.z_cap)
        return z_scores


class RegimeIdentifier:
    """Identify regime for splitting models."""
    
    @staticmethod
    def identify_total_regime(totals: np.ndarray) -> np.ndarray:
        """Split by high/low total threshold."""
        median = np.median(totals)
        return np.where(totals > median, 'high_total', 'low_total')
    
    @staticmethod
    def identify_dome_regime(is_dome: np.ndarray) -> np.ndarray:
        """Split by indoor/outdoor."""
        return np.where(is_dome, 'indoor', 'outdoor')
    
    @staticmethod
    def identify_combined_regime(totals: np.ndarray, is_dome: np.ndarray) -> np.ndarray:
        """Combine total and dome into 4 regimes."""
        total_regime = RegimeIdentifier.identify_total_regime(totals)
        dome_regime = RegimeIdentifier.identify_dome_regime(is_dome)
        return np.array([f"{d}_{t}" for d, t in zip(dome_regime, total_regime)])


class FractionalKelly:
    """
    Dynamic bet sizing using fractional Kelly criterion.
    
    Kelly fraction: f = (p * b - q) / b
    where p = win probability, q = 1-p, b = odds (decimal)
    
    Fractional Kelly: bet_size = f * bankroll * fraction
    
    For -110 odds: b = 0.909 (risk 1 to win 0.909)
    """
    
    def __init__(self, fraction: float = 0.25, bankroll: float = 1000.0, min_bet: float = 1.0, max_bet: float = 100.0):
        """
        Args:
            fraction: Kelly fraction multiplier (0.25 = quarter Kelly)
            bankroll: Starting bankroll
            min_bet: Minimum bet size
            max_bet: Maximum bet size (as % of bankroll)
        """
        self.fraction = fraction
        self.bankroll = bankroll
        self.min_bet = min_bet
        self.max_bet_pct = max_bet / 100.0  # Convert to decimal
    
    def calculate_bet_size(self, win_prob: float, edge: float) -> float:
        """
        Calculate bet size using fractional Kelly.
        
        Args:
            win_prob: Probability of winning
            edge: Edge percentage (win_prob - breakeven)
            
        Returns:
            Bet size in units
        """
        if edge <= 0:
            return 0.0  # No edge, no bet
        
        # For -110 odds (decimal odds = 0.909)
        decimal_odds = 0.909
        
        # Kelly formula: f = (p * b - q) / b
        # where p = win_prob, q = 1 - win_prob, b = decimal_odds
        kelly_fraction = (win_prob * decimal_odds - (1 - win_prob)) / decimal_odds
        
        # Apply fractional Kelly
        bet_pct = kelly_fraction * self.fraction
        
        # Convert to absolute bet size
        bet_size = bet_pct * self.bankroll
        
        # Apply limits
        max_bet = self.bankroll * self.max_bet_pct
        bet_size = np.clip(bet_size, self.min_bet, max_bet)
        
        return max(0.0, bet_size)
    
    def update_bankroll(self, bet_size: float, result: float):
        """
        Update bankroll after bet result.
        
        Args:
            bet_size: Amount wagered
            result: 1.0 = win, 0.0 = loss, 0.5 = push
        """
        if result == 1.0:
            # Win: get bet_size + winnings (0.909 * bet_size)
            self.bankroll += bet_size * 0.909
        elif result == 0.0:
            # Loss: lose bet_size
            self.bankroll -= bet_size
        # Push: no change


class WalkForwardRefresher:
    """
    Refit calibration every N weeks using walk-forward validation.
    """
    
    def __init__(self, refit_frequency: int = 4, min_samples: int = 50):
        """
        Args:
            refit_frequency: Refit every N weeks
            min_samples: Minimum samples needed to refit
        """
        self.refit_frequency = refit_frequency
        self.min_samples = min_samples
        self.refit_weeks = []
    
    def should_refit(self, current_week: int, historical_weeks: list) -> bool:
        """Determine if we should refit based on week."""
        if len(historical_weeks) < self.min_samples:
            return False
        
        # Refit every N weeks
        weeks_since_refit = current_week - (self.refit_weeks[-1] if self.refit_weeks else 0)
        return weeks_since_refit >= self.refit_frequency
    
    def get_training_window(self, current_week: int, lookback_weeks: int = 8) -> tuple:
        """
        Get training window for walk-forward.
        
        Returns:
            (start_week, end_week) for training data
        """
        end_week = current_week - 1  # Don't use current week
        start_week = max(1, end_week - lookback_weeks + 1)
        return (start_week, end_week)


if __name__ == "__main__":
    # Example usage
    print("="*70)
    print("ADVANCED CALIBRATION TOOLS")
    print("="*70)
    
    # Load backtest data
    backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_all_games_conviction.csv"
    if backtest_file.exists():
        df = pd.read_csv(backtest_file)
        print(f"\n✅ Loaded {len(df)} games")
        
        # Filter to completed games
        completed = df[df['actual_home_score'].notna()].copy()
        print(f"   {len(completed)} completed games")
        
        # Example: Fit isotonic calibrator for spreads
        print("\n📊 Fitting isotonic calibrator for spreads...")
        calibrator = AdvancedProbabilityCalibrator(method='isotonic')
        
        # Prepare data
        sim_spreads = completed['spread_raw'].values
        sim_sds = completed['spread_raw_sd'].values
        market_spreads = completed['spread_line'].values
        outcomes = (completed['actual_spread'] > completed['spread_line']).astype(float)
        outcomes[completed['actual_spread'] == completed['spread_line']] = 0.5  # Pushes
        
        calibrator.fit_from_historical(
            sim_spreads, sim_sds, market_spreads, outcomes
        )
        
        # Test predictions
        probs = calibrator.predict(sim_spreads, sim_sds, market_spreads)
        print(f"\n   Predicted probabilities:")
        print(f"      Mean: {probs.mean():.3f}")
        print(f"      Std: {probs.std():.3f}")
        print(f"      Range: [{probs.min():.3f}, {probs.max():.3f}]")
        
        print("\n✅ Calibration tools ready!")
    else:
        print(f"\n⚠️  Backtest file not found: {backtest_file}")
        print("   Run backtest first to generate data")

