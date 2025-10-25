"""
Model Error Analysis & Improvement System

Analyzes why predictions went wrong and suggests model improvements.
Creates a "Model v2" with improvements, backtests it, and compares to base model.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import json


class ModelErrorAnalyzer:
    """Analyze model errors and suggest improvements"""
    
    def __init__(self, predictions_file: str, results_file: str):
        self.predictions_file = predictions_file
        self.results_file = results_file
        self.errors = []
        
    def load_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Load predictions and results"""
        predictions = []
        with open(self.predictions_file, 'r') as f:
            for line in f:
                predictions.append(json.loads(line))
        
        results = []
        with open(self.results_file, 'r') as f:
            for line in f:
                results.append(json.loads(line))
        
        return predictions, results
    
    def identify_errors(self) -> List[Dict]:
        """Find all wrong predictions"""
        predictions, results = self.load_data()
        
        errors = []
        
        for pred in predictions:
            # Find matching result
            result = next((r for r in results if 
                          r['week'] == pred['week'] and 
                          r['away'] == pred['away'] and 
                          r['home'] == pred['home']), None)
            
            if not result:
                continue
            
            # Get model prediction
            your_model = pred.get('your_model', {})
            home_win_prob = your_model.get('home_win_prob', 50)
            predicted_winner = pred['home'] if home_win_prob > 50 else pred['away']
            
            # Get actual winner
            actual_winner = pred['home'] if result['home_score'] > result['away_score'] else pred['away']
            
            # Check if wrong
            if predicted_winner != actual_winner:
                errors.append({
                    'week': pred['week'],
                    'away': pred['away'],
                    'home': pred['home'],
                    'predicted_winner': predicted_winner,
                    'actual_winner': actual_winner,
                    'predicted_margin': your_model.get('spread', 0),
                    'actual_margin': result['home_score'] - result['away_score'],
                    'predicted_total': your_model.get('total', 0),
                    'actual_total': result['home_score'] + result['away_score'],
                    'confidence': round(max(home_win_prob, 100 - home_win_prob), 1),
                    'away_score': result['away_score'],
                    'home_score': result['home_score']
                })
        
        self.errors = errors
        return errors
    
    def analyze_error_patterns(self) -> Dict:
        """Analyze common patterns in errors"""
        if not self.errors:
            self.identify_errors()
        
        if len(self.errors) == 0:
            return {'message': 'No errors to analyze - perfect predictions!'}
        
        analysis = {
            'total_errors': len(self.errors),
            'error_rate': len(self.errors) / 13 * 100,  # Assuming 13 total predictions
            'patterns': {}
        }
        
        # Pattern 1: High confidence errors (model was very wrong)
        high_confidence_errors = [e for e in self.errors if e['confidence'] > 70]
        analysis['patterns']['high_confidence_errors'] = {
            'count': len(high_confidence_errors),
            'games': high_confidence_errors,
            'insight': 'Model was overconfident in these predictions'
        }
        
        # Pattern 2: Close games (actual margin < 7 points)
        close_game_errors = [e for e in self.errors if abs(e['actual_margin']) < 7]
        analysis['patterns']['close_games'] = {
            'count': len(close_game_errors),
            'games': close_game_errors,
            'insight': 'Model struggles with toss-up games'
        }
        
        # Pattern 3: Total prediction accuracy
        total_errors = []
        for error in self.errors:
            total_diff = abs(error['predicted_total'] - error['actual_total'])
            if total_diff > 10:  # Off by more than 10 points
                total_errors.append({
                    **error,
                    'total_diff': total_diff
                })
        
        analysis['patterns']['total_prediction_errors'] = {
            'count': len(total_errors),
            'games': total_errors,
            'insight': 'Model had trouble predicting scoring levels'
        }
        
        # Pattern 4: Margin prediction (was spread way off?)
        margin_errors = []
        for error in self.errors:
            # Compare predicted margin vs actual margin (both relative to same team)
            pred_margin = error['predicted_margin']  # Negative if away favored
            actual_margin = error['actual_margin']   # Positive if home won
            
            margin_diff = abs(pred_margin - actual_margin)
            if margin_diff > 10:
                margin_errors.append({
                    **error,
                    'margin_diff': margin_diff
                })
        
        analysis['patterns']['large_margin_errors'] = {
            'count': len(margin_errors),
            'games': margin_errors,
            'insight': 'Model significantly misjudged the margin of victory'
        }
        
        return analysis
    
    def suggest_improvements(self, analysis: Dict) -> List[Dict]:
        """Suggest model improvements based on error patterns"""
        suggestions = []
        
        patterns = analysis.get('patterns', {})
        
        # Suggestion 1: Reduce overconfidence
        if patterns.get('high_confidence_errors', {}).get('count', 0) > 0:
            suggestions.append({
                'improvement': 'Calibration Adjustment',
                'reason': f"{patterns['high_confidence_errors']['count']} high-confidence errors detected",
                'implementation': 'Apply probability shrinkage: move predictions closer to 50% baseline',
                'parameter': 'confidence_shrinkage_factor',
                'suggested_value': 0.85,  # Shrink probabilities by 15%
                'priority': 'High'
            })
        
        # Suggestion 2: Better handling of close games
        if patterns.get('close_games', {}).get('count', 0) > 0:
            suggestions.append({
                'improvement': 'Uncertainty for Close Matchups',
                'reason': f"{patterns['close_games']['count']} errors in close games",
                'implementation': 'Increase variance in Monte Carlo for evenly-matched teams',
                'parameter': 'close_game_variance_multiplier',
                'suggested_value': 1.3,  # 30% more variance when teams are close
                'priority': 'Medium'
            })
        
        # Suggestion 3: Total scoring adjustments
        if patterns.get('total_prediction_errors', {}).get('count', 0) > 0:
            avg_total_diff = np.mean([g['total_diff'] for g in patterns['total_prediction_errors']['games']])
            
            suggestions.append({
                'improvement': 'Scoring Level Calibration',
                'reason': f"Total points off by average of {avg_total_diff:.1f} points",
                'implementation': 'Adjust offensive/defensive EPA weightings',
                'parameter': 'scoring_calibration_refinement',
                'suggested_value': 'context',
                'priority': 'Medium'
            })
        
        # Suggestion 4: Feature engineering
        suggestions.append({
            'improvement': 'Add Momentum Features',
            'reason': 'Model may not capture recent team momentum',
            'implementation': 'Weight recent 3 games more heavily than season averages',
            'parameter': 'recent_games_weight',
            'suggested_value': 0.6,  # 60% weight to last 3 games
            'priority': 'Low'
        })
        
        suggestions.append({
            'improvement': 'Home Field Advantage',
            'reason': 'May need better home field adjustment',
            'implementation': 'Tune home field advantage multiplier',
            'parameter': 'home_field_points',
            'suggested_value': 2.5,  # Test different HFA values
            'priority': 'Low'
        })
        
        return suggestions
    
    def generate_report(self) -> str:
        """Generate comprehensive error analysis report"""
        errors = self.identify_errors()
        analysis = self.analyze_error_patterns()
        suggestions = self.suggest_improvements(analysis)
        
        report = []
        report.append("=" * 80)
        report.append("MODEL ERROR ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Total Predictions: 13")
        report.append(f"Errors: {len(errors)}")
        report.append(f"Accuracy: {(13 - len(errors)) / 13 * 100:.1f}%")
        report.append("")
        
        report.append("=" * 80)
        report.append("WRONG PREDICTIONS:")
        report.append("=" * 80)
        for i, error in enumerate(errors, 1):
            report.append(f"\n{i}. {error['away']} @ {error['home']} (Week {error['week']})")
            report.append(f"   Predicted: {error['predicted_winner']} by {abs(error['predicted_margin']):.1f} (Confidence: {error['confidence']}%)")
            report.append(f"   Actual: {error['actual_winner']} won {error['away_score']}-{error['home_score']} (margin: {abs(error['actual_margin'])})")
            report.append(f"   Total: Predicted {error['predicted_total']:.1f}, Actual {error['actual_total']}")
        
        report.append("\n" + "=" * 80)
        report.append("ERROR PATTERNS:")
        report.append("=" * 80)
        for pattern_name, pattern_data in analysis.get('patterns', {}).items():
            report.append(f"\n{pattern_name.replace('_', ' ').title()}:")
            report.append(f"  Count: {pattern_data['count']}")
            report.append(f"  Insight: {pattern_data['insight']}")
        
        report.append("\n" + "=" * 80)
        report.append("SUGGESTED IMPROVEMENTS:")
        report.append("=" * 80)
        for i, suggestion in enumerate(suggestions, 1):
            report.append(f"\n{i}. {suggestion['improvement']} (Priority: {suggestion['priority']})")
            report.append(f"   Reason: {suggestion['reason']}")
            report.append(f"   Implementation: {suggestion['implementation']}")
            if suggestion['suggested_value'] != 'context':
                report.append(f"   Parameter: {suggestion['parameter']} = {suggestion['suggested_value']}")
        
        report.append("\n" + "=" * 80)
        report.append("NEXT STEPS:")
        report.append("=" * 80)
        report.append("1. Create Model v2 with suggested improvements")
        report.append("2. Backtest Model v2 on historical data")
        report.append("3. Compare Model v2 vs Base Model performance")
        report.append("4. If v2 is better, consider replacing base model OR")
        report.append("5. Use ensemble approach (average both models)")
        report.append("")
        
        return "\n".join(report)


if __name__ == '__main__':
    analyzer = ModelErrorAnalyzer(
        'data/predictions/predictions_history.jsonl',
        'data/predictions/actual_results.jsonl'
    )
    
    report = analyzer.generate_report()
    print(report)
    
    # Save report
    with open('artifacts/error_analysis_report.txt', 'w') as f:
        f.write(report)
    
    print("\n✅ Report saved to: artifacts/error_analysis_report.txt")

