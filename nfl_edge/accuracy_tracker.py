"""
NFL Prediction Accuracy Tracker
Records predictions and actual results to measure model performance
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class AccuracyTracker:
    """Track prediction accuracy across multiple models"""
    
    def __init__(self, data_dir: str = "data/predictions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.predictions_file = self.data_dir / "predictions_history.jsonl"
        self.results_file = self.data_dir / "actual_results.jsonl"
        
    def record_prediction(self, 
                         week: int,
                         season: int,
                         away: str,
                         home: str,
                         your_model: Dict,
                         fivethirtyeight: Optional[Dict] = None,
                         vegas: Optional[Dict] = None,
                         espn: Optional[Dict] = None):
        """
        Record predictions from all models for a game
        
        Args:
            week: Week number
            season: Season year
            away: Away team abbreviation
            home: Home team abbreviation
            your_model: Dict with away_win_prob, home_win_prob, spread, total
            fivethirtyeight: Optional 538 predictions
            vegas: Optional Vegas predictions
            espn: Optional ESPN predictions
        """
        prediction_record = {
            'timestamp': datetime.now().isoformat(),
            'season': season,
            'week': week,
            'away': away,
            'home': home,
            'your_model': your_model,
            'fivethirtyeight': fivethirtyeight,
            'vegas': vegas,
            'espn': espn
        }
        
        # Append to JSONL file
        with open(self.predictions_file, 'a') as f:
            f.write(json.dumps(prediction_record) + '\n')
    
    def record_result(self,
                     week: int,
                     season: int,
                     away: str,
                     home: str,
                     away_score: int,
                     home_score: int,
                     spread_line: float = None,
                     total_line: float = None):
        """
        Record actual game result
        
        Args:
            week: Week number
            season: Season year
            away: Away team abbreviation
            home: Home team abbreviation
            away_score: Away team final score
            home_score: Home team final score
            spread_line: Closing spread (home team perspective)
            total_line: Closing total
        """
        result_record = {
            'timestamp': datetime.now().isoformat(),
            'season': season,
            'week': week,
            'away': away,
            'home': home,
            'away_score': away_score,
            'home_score': home_score,
            'winner': 'away' if away_score > home_score else ('home' if home_score > away_score else 'tie'),
            'margin': home_score - away_score,
            'total': away_score + home_score,
            'spread_line': spread_line,
            'total_line': total_line,
            'spread_result': self._calculate_spread_result(away_score, home_score, spread_line) if spread_line else None,
            'total_result': 'over' if total_line and (away_score + home_score) > total_line else ('under' if total_line else None)
        }
        
        # Append to JSONL file
        with open(self.results_file, 'a') as f:
            f.write(json.dumps(result_record) + '\n')
    
    def _calculate_spread_result(self, away_score: int, home_score: int, spread_line: float) -> str:
        """Calculate if home team covered the spread"""
        home_cover_margin = (home_score - away_score) - spread_line
        if home_cover_margin > 0:
            return 'home_cover'
        elif home_cover_margin < 0:
            return 'away_cover'
        else:
            return 'push'
    
    def calculate_brier_score(self, predictions: List[float], outcomes: List[int]) -> float:
        """
        Calculate Brier score (lower is better)
        
        Args:
            predictions: List of predicted probabilities (0-1)
            outcomes: List of actual outcomes (0 or 1)
            
        Returns:
            Brier score (0 = perfect, 1 = worst)
        """
        if len(predictions) != len(outcomes):
            raise ValueError("Predictions and outcomes must have same length")
        
        brier = sum((p - o) ** 2 for p, o in zip(predictions, outcomes)) / len(predictions)
        return brier
    
    def get_accuracy_report(self, season: int = None, min_games: int = 5) -> Dict:
        """
        Generate accuracy report for all models
        
        Args:
            season: Filter to specific season (None = all seasons)
            min_games: Minimum games to include model in report
            
        Returns:
            Dictionary with accuracy metrics for each model
        """
        # Load predictions and results
        predictions = self._load_predictions(season)
        results = self._load_results(season)
        
        if not predictions or not results:
            return {
                'error': 'No data available',
                'predictions_count': len(predictions),
                'results_count': len(results)
            }
        
        # Match predictions with results
        matched = self._match_predictions_with_results(predictions, results)
        
        if len(matched) < min_games:
            return {
                'error': f'Not enough games (need {min_games}, have {len(matched)})',
                'matched_games': len(matched)
            }
        
        # Calculate metrics for each model
        report = {
            'total_games': len(matched),
            'season': season,
            'models': {}
        }
        
        # Your Model
        report['models']['your_model'] = self._calculate_model_accuracy(
            matched, 'your_model'
        )
        
        # FiveThirtyEight
        if any('fivethirtyeight' in p and p['fivethirtyeight'] for p in matched):
            report['models']['fivethirtyeight'] = self._calculate_model_accuracy(
                matched, 'fivethirtyeight'
            )
        
        # Vegas
        if any('vegas' in p and p['vegas'] for p in matched):
            report['models']['vegas'] = self._calculate_model_accuracy(
                matched, 'vegas'
            )
        
        return report
    
    def _calculate_model_accuracy(self, matched_data: List[Dict], model_name: str) -> Dict:
        """Calculate accuracy metrics for a specific model"""
        predictions = []
        outcomes = []
        correct_picks = 0
        total_picks = 0
        
        for game in matched_data:
            pred = game.get(model_name)
            if not pred:
                continue
            
            result = game.get('result')
            if not result:
                continue
            
            # Get home team win probability
            home_win_prob = pred.get('home_win_prob', 50) / 100
            actual_home_win = 1 if result['winner'] == 'home' else 0
            
            predictions.append(home_win_prob)
            outcomes.append(actual_home_win)
            
            # Count correct picks (>50% probability = pick)
            if (home_win_prob > 0.5 and actual_home_win == 1) or \
               (home_win_prob < 0.5 and actual_home_win == 0):
                correct_picks += 1
            total_picks += 1
        
        if not predictions:
            return {'error': 'No predictions for this model'}
        
        brier = self.calculate_brier_score(predictions, outcomes)
        accuracy = (correct_picks / total_picks * 100) if total_picks > 0 else 0
        
        return {
            'games': total_picks,
            'accuracy_pct': round(accuracy, 1),
            'brier_score': round(brier, 4),
            'correct_picks': correct_picks,
            'calibration': 'Good' if 0.15 <= brier <= 0.25 else ('Excellent' if brier < 0.15 else 'Needs improvement')
        }
    
    def _load_predictions(self, season: int = None) -> List[Dict]:
        """Load prediction history from file"""
        if not self.predictions_file.exists():
            return []
        
        predictions = []
        with open(self.predictions_file, 'r') as f:
            for line in f:
                pred = json.loads(line.strip())
                if season is None or pred.get('season') == season:
                    predictions.append(pred)
        
        return predictions
    
    def _load_results(self, season: int = None) -> List[Dict]:
        """Load actual results from file"""
        if not self.results_file.exists():
            return []
        
        results = []
        with open(self.results_file, 'r') as f:
            for line in f:
                result = json.loads(line.strip())
                if season is None or result.get('season') == season:
                    results.append(result)
        
        return results
    
    def _match_predictions_with_results(self, predictions: List[Dict], results: List[Dict]) -> List[Dict]:
        """Match predictions with actual results"""
        matched = []
        
        for pred in predictions:
            # Find matching result
            for result in results:
                if (pred['season'] == result['season'] and
                    pred['week'] == result['week'] and
                    pred['away'] == result['away'] and
                    pred['home'] == result['home']):
                    
                    matched.append({
                        **pred,
                        'result': result
                    })
                    break
        
        return matched
    
    def get_weekly_summary(self, season: int, week: int) -> Dict:
        """Get accuracy summary for a specific week"""
        predictions = self._load_predictions(season)
        results = self._load_results(season)
        
        week_preds = [p for p in predictions if p['week'] == week]
        week_results = [r for r in results if r['week'] == week]
        
        matched = self._match_predictions_with_results(week_preds, week_results)
        
        return {
            'season': season,
            'week': week,
            'games_predicted': len(week_preds),
            'games_completed': len(week_results),
            'matched': len(matched),
            'predictions': matched
        }


def create_tracker():
    """Create and return an AccuracyTracker instance"""
    return AccuracyTracker()

