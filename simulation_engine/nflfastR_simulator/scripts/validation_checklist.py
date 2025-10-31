"""
Validation checklist for model performance:
1. Reliability curve (predicted vs actual by bins)
2. Sharpness (distribution of predicted probabilities)
3. Log-loss / Brier score comparison
4. Out-of-sample test (2025 weeks only)
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import log_loss, brier_score_loss
import warnings

class ModelValidator:
    """Comprehensive model validation."""
    
    def __init__(self):
        self.results = {}
    
    def calculate_reliability(self,
                             predicted_probs: np.ndarray,
                             actual_outcomes: np.ndarray,
                             n_bins: int = 10) -> dict:
        """
        Calculate reliability (calibration) metrics.
        
        Returns:
            Dict with bin centers, predicted probs, actual rates, counts
        """
        # Filter out pushes (0.5) and invalid
        valid_mask = ~np.isnan(predicted_probs) & ~np.isnan(actual_outcomes) & (actual_outcomes != 0.5)
        pred = predicted_probs[valid_mask]
        actual = actual_outcomes[valid_mask].astype(int)
        
        # Bin probabilities
        bins = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(pred, bins[1:-1])  # Exclude endpoints
        
        bin_centers = []
        bin_predicted = []
        bin_actual = []
        bin_counts = []
        
        for i in range(n_bins):
            mask = bin_indices == i
            if mask.sum() == 0:
                continue
            
            bin_centers.append((bins[i] + bins[i+1]) / 2)
            bin_predicted.append(pred[mask].mean())
            bin_actual.append(actual[mask].mean())
            bin_counts.append(mask.sum())
        
        # Calculate calibration error (ECE)
        ece = np.mean([abs(p - a) * c for p, a, c in zip(bin_predicted, bin_actual, bin_counts)]) / len(pred)
        
        # Calculate slope (should be ~1 for good calibration)
        if len(bin_predicted) > 1:
            slope = np.polyfit(bin_predicted, bin_actual, 1)[0]
            intercept = np.polyfit(bin_predicted, bin_actual, 1)[1]
        else:
            slope = 1.0
            intercept = 0.0
        
        return {
            'bin_centers': np.array(bin_centers),
            'predicted': np.array(bin_predicted),
            'actual': np.array(bin_actual),
            'counts': np.array(bin_counts),
            'ece': ece,
            'slope': slope,
            'intercept': intercept
        }
    
    def calculate_sharpness(self, predicted_probs: np.ndarray) -> dict:
        """
        Calculate sharpness (how spread out predictions are).
        Good model should have predictions away from 0.5.
        """
        valid = predicted_probs[~np.isnan(predicted_probs)]
        
        # Metrics
        mean = valid.mean()
        std = valid.std()
        
        # Distance from 0.5 (neutral)
        dist_from_neutral = np.abs(valid - 0.5)
        mean_dist = dist_from_neutral.mean()
        
        # Concentration around 0.5 (bad if too high)
        concentration = ((valid >= 0.45) & (valid <= 0.55)).mean()
        
        return {
            'mean': mean,
            'std': std,
            'mean_dist_from_neutral': mean_dist,
            'concentration_around_05': concentration,
            'min': valid.min(),
            'max': valid.max()
        }
    
    def calculate_scoring_rules(self,
                               predicted_probs: np.ndarray,
                               actual_outcomes: np.ndarray) -> dict:
        """
        Calculate log-loss and Brier score.
        Lower is better.
        """
        # Filter valid
        valid_mask = ~np.isnan(predicted_probs) & ~np.isnan(actual_outcomes) & (actual_outcomes != 0.5)
        pred = predicted_probs[valid_mask]
        actual = actual_outcomes[valid_mask].astype(int)
        
        if len(pred) == 0:
            return {'log_loss': np.nan, 'brier_score': np.nan}
        
        # Log-loss
        log_loss_score = log_loss(actual, pred)
        
        # Brier score
        brier = brier_score_loss(actual, pred)
        
        # Baseline (always predict 0.524)
        baseline_log_loss = log_loss(actual, np.full_like(pred, 0.524))
        baseline_brier = brier_score_loss(actual, np.full_like(pred, 0.524))
        
        # Improvement vs baseline
        log_loss_improvement = (baseline_log_loss - log_loss_score) / baseline_log_loss * 100
        brier_improvement = (baseline_brier - brier) / baseline_brier * 100
        
        return {
            'log_loss': log_loss_score,
            'brier_score': brier,
            'baseline_log_loss': baseline_log_loss,
            'baseline_brier': baseline_brier,
            'log_loss_improvement_pct': log_loss_improvement,
            'brier_improvement_pct': brier_improvement
        }
    
    def validate_model(self,
                      predicted_probs: np.ndarray,
                      actual_outcomes: np.ndarray,
                      model_name: str = "Model") -> dict:
        """
        Run full validation suite.
        
        Returns:
            Dict with all validation metrics
        """
        results = {
            'model_name': model_name,
            'n_samples': len(predicted_probs),
            'reliability': self.calculate_reliability(predicted_probs, actual_outcomes),
            'sharpness': self.calculate_sharpness(predicted_probs),
            'scoring': self.calculate_scoring_rules(predicted_probs, actual_outcomes)
        }
        
        return results
    
    def plot_reliability(self, results: dict, save_path: Path = None):
        """Plot reliability curve."""
        rel = results['reliability']
        
        plt.figure(figsize=(8, 6))
        plt.plot(rel['predicted'], rel['actual'], 'o-', label='Calibration')
        plt.plot([0, 1], [0, 1], '--', label='Perfect', color='gray')
        plt.xlabel('Predicted Probability')
        plt.ylabel('Actual Frequency')
        plt.title(f'Reliability Curve (ECE={rel["ece"]:.3f}, Slope={rel["slope"]:.2f})')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path)
        else:
            plt.show()
    
    def print_validation_report(self, results: dict):
        """Print formatted validation report."""
        print("="*70)
        print(f"VALIDATION REPORT: {results['model_name']}")
        print("="*70)
        
        print(f"\n📊 Dataset:")
        print(f"   Samples: {results['n_samples']:,}")
        
        print(f"\n📈 Reliability (Calibration):")
        rel = results['reliability']
        print(f"   ECE (Expected Calibration Error): {rel['ece']:.4f}")
        print(f"   Slope: {rel['slope']:.3f} (target: ~1.0)")
        print(f"   Intercept: {rel['intercept']:.3f} (target: ~0.0)")
        print(f"   Status: {'✅ Good' if abs(rel['slope'] - 1.0) < 0.2 and abs(rel['intercept']) < 0.1 else '⚠️  Needs work'}")
        
        print(f"\n🎯 Sharpness:")
        sharp = results['sharpness']
        print(f"   Mean prediction: {sharp['mean']:.3f}")
        print(f"   Std: {sharp['std']:.3f}")
        print(f"   Mean distance from 0.5: {sharp['mean_dist_from_neutral']:.3f}")
        print(f"   Concentration around 0.5: {sharp['concentration_around_05']:.1%}")
        print(f"   Status: {'✅ Good' if sharp['concentration_around_05'] < 0.4 else '⚠️  Too compressed'}")
        
        print(f"\n📉 Scoring Rules:")
        score = results['scoring']
        print(f"   Log Loss: {score['log_loss']:.4f} (baseline: {score['baseline_log_loss']:.4f})")
        print(f"   Improvement: {score['log_loss_improvement_pct']:+.1f}%")
        print(f"   Brier Score: {score['brier_score']:.4f} (baseline: {score['baseline_brier']:.4f})")
        print(f"   Improvement: {score['brier_improvement_pct']:+.1f}%")
        print(f"   Status: {'✅ Good' if score['log_loss_improvement_pct'] >= 10 else '⚠️  Needs improvement (target: ≥10%)'}")
        
        print("\n" + "="*70)


if __name__ == "__main__":
    # Load backtest data
    backtest_file = Path(__file__).parent.parent / "artifacts" / "backtest_all_games_conviction.csv"
    
    if not backtest_file.exists():
        print(f"⚠️  Backtest file not found: {backtest_file}")
        print("   Run backtest first")
        exit(1)
    
    df = pd.read_csv(backtest_file)
    completed = df[df['actual_home_score'].notna()].copy()
    
    print(f"✅ Loaded {len(completed)} completed games")
    
    validator = ModelValidator()
    
    # Validate spread predictions
    print("\n" + "="*70)
    print("VALIDATING SPREAD PREDICTIONS")
    print("="*70)
    
    spread_outcomes = (completed['actual_spread'] > completed['spread_line']).astype(float)
    spread_outcomes[completed['actual_spread'] == completed['spread_line']] = 0.5  # Pushes
    
    spread_results = validator.validate_model(
        completed['p_home_cover'].values,
        spread_outcomes.values,
        "Spread (Linear Calibration)"
    )
    validator.print_validation_report(spread_results)
    
    # Validate total predictions
    print("\n" + "="*70)
    print("VALIDATING TOTAL PREDICTIONS")
    print("="*70)
    
    total_outcomes = (completed['actual_total'] > completed['total_line']).astype(float)
    total_outcomes[abs(completed['actual_total'] - completed['total_line']) < 0.5] = 0.5  # Pushes
    
    total_results = validator.validate_model(
        completed['p_over'].values,
        total_outcomes.values,
        "Total (Linear Calibration)"
    )
    validator.print_validation_report(total_results)
    
    # Out-of-sample test (2025 only)
    print("\n" + "="*70)
    print("OUT-OF-SAMPLE TEST (2025 ONLY)")
    print("="*70)
    
    df_2025 = completed[completed['season'] == 2025].copy()
    if len(df_2025) > 0:
        print(f"✅ Found {len(df_2025)} games from 2025")
        
        spread_2025 = validator.validate_model(
            df_2025['p_home_cover'].values,
            (df_2025['actual_spread'] > df_2025['spread_line']).astype(float).values,
            "Spread (2025 OOS)"
        )
        validator.print_validation_report(spread_2025)
    else:
        print("⚠️  No 2025 games found in backtest data")

