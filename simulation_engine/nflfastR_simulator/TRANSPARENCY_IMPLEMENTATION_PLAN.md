# Transparency & Tracing Implementation Plan

## Overview

This document outlines the implementation of comprehensive tracing and transparency features based on the feedback. The goal is to make every decision, input, and outcome traceable and reproducible.

---

## ✅ Completed

### 1. Core Tracing Infrastructure
- **File**: `simulator/tracing.py`
- **Status**: ✅ Complete
- **Features**:
  - `SimTrace` class for game-wide event logging
  - JSONL output format (streaming to disk)
  - In-memory buffer for inspection
  - Event filtering by type
  - Summary export

### 2. Team Profile Audit Method
- **File**: `simulator/team_profile.py`
- **Status**: ✅ Complete
- **Method**: `as_dict_for_audit()`
- **Returns**: All inputs actually used by simulator (EPA, QB stats, PFF grades, situational factors, etc.)

---

## 🔄 In Progress / Next Steps

### 3. GameSimulator Integration
**File**: `simulator/game_simulator.py`

**Changes needed:**
1. Add `trace` parameter to `__init__`
2. Log input audit on initialization
3. Log drive summaries
4. Log game summary with realism guards
5. Add seed support for reproducibility

**Code to add:**
```python
def __init__(self, home_team: TeamProfile, away_team: TeamProfile, 
             game_id: str = None, season: int = None, week: int = None,
             trace: Optional[SimTrace] = None, seed: Optional[int] = None):
    # ... existing code ...
    
    # Initialize trace
    if trace is None:
        game_id_str = game_id or f"{season}_{week}_{away_team.team}_{home_team.team}"
        trace = SimTrace(game_id=game_id_str, seed=seed)
    self.trace = trace
    
    # Log input audit
    self.trace.log("inputs.audit", {
        "home": self.home_team.as_dict_for_audit(),
        "away": self.away_team.as_dict_for_audit(),
        "situational": {
            "is_dome": self.home_team.is_dome,
            "temp": self.home_team.temperature,
            "wind": self.home_team.wind,
            "home_rest_days": self.home_team.home_rest_days,
            "away_rest_days": self.away_team.away_rest_days
        },
        "seed": seed
    })
```

**Drive summary logging:**
```python
def _simulate_drive(self, game_state: GameState, offense: TeamProfile, defense: TeamProfile):
    drive_start_state = {
        "drive_num": game_state.drive_number,
        "team": game_state.possession,
        "start_yardline": game_state.yardline,
        "start_quarter": game_state.quarter
    }
    
    # ... existing drive simulation ...
    
    # Log drive summary
    self.trace.log("drive.summary", {
        "drive_no": game_state.drive_number,
        "team": game_state.possession,
        "plays": drive_plays,
        "points": points_this_drive,
        "time_used": seconds_used,
        "result": result_text,  # "TD", "FG", "Punt", "Turnover", etc.
        "start_state": drive_start_state,
        "end_state": {
            "yardline": game_state.yardline,
            "quarter": game_state.quarter
        }
    })
```

**Game summary with realism guards:**
```python
def simulate_game(self) -> Dict:
    # ... existing simulation ...
    
    # Log game summary
    self.trace.log("game.summary", {
        "home_score": game_state.home_score,
        "away_score": game_state.away_score,
        "spread": game_state.away_score - game_state.home_score,
        "total": game_state.home_score + game_state.away_score,
        "drives_per_team": game_state.drive_number / 2,  # Approximate
        # ... other metrics ...
    })
    
    # Run realism guards
    self._check_realism_guards(game_state)
    
    return result
```

---

### 4. PlaySimulator Integration
**File**: `simulator/play_simulator.py`

**Changes needed:**
1. Add `trace` parameter
2. Log pass/run decision with reasoning
3. Log pressure calculation
4. Log completion probability calculation
5. Log interception probability
6. Log explosive play detection
7. Log play result

**Code to add:**
```python
def decide_play_type(self, game_state: GameState) -> str:
    # ... existing decision logic ...
    
    self.trace.log("call.pass_run", {
        "quarter": game_state.quarter,
        "down": game_state.down,
        "to_go": game_state.ydstogo,
        "yardline": game_state.yardline,
        "score_diff": game_state.home_score - game_state.away_score,
        "team_pass_rate": float(pass_rate),
        "choice": choice,
        "reasoning": {
            "distance_bucket": distance_bucket,
            "score_diff_bucket": score_diff_bucket,
            "time_bucket": time_bucket
        }
    })
    
    return choice

def simulate_pass_play(self, game_state: GameState) -> Dict:
    # Log pressure calculation
    pressure_rate = self._calculate_pressure_rate()
    self.trace.log("pass.pressure", {
        "base": self.BASE_PRESSURE_RATE,
        "ol_grade": self.offense.ol_grade,
        "dl_grade": self.defense.dl_grade,
        "mismatch": float(self.defense.dl_grade - self.offense.ol_grade),
        "final": float(pressure_rate),
        "is_pressure": bool(is_pressure)
    })
    
    # Log completion probability
    completion_pct = self._calculate_completion_probability(is_pressure)
    self.trace.log("pass.completion_model", {
        "split": "pressure" if is_pressure else "clean",
        "qb_baseline": float(qb_stats['completion_pct']),
        "anya_advantage": float(anya_advantage),
        "after_anya": float(completion_pct_after_anya),
        "after_pff_vs_cov": float(completion_pct),
        "weather_penalty": float(weather_penalty if applied else 0.0),
        "rest_effect": float(rest_effect),
        "final_completion_pct": float(completion_pct)
    })
    
    # ... existing play simulation ...
    
    # Log play result
    self.trace.log("play.result", {
        "type": play_result['type'],
        "yards": play_result['yards'],
        "td": play_result.get('td', False),
        "turnover": play_result.get('turnover', False),
        "explosive": play_result.get('yards', 0) >= 15,
        "state_after": {
            "down": game_state.down,
            "to_go": game_state.ydstogo,
            "yardline": game_state.yardline,
            "home": game_state.home_score,
            "away": game_state.away_score,
            "quarter": game_state.quarter,
            "time_rem": game_state.time_remaining
        }
    })
    
    return play_result
```

---

### 5. Fourth-Down Decision Logging
**File**: `simulator/game_state.py`

**Changes needed:**
1. Make `should_attempt_fg()` and `should_punt()` return decision + reasoning
2. Log 4th down decisions

**Code to add:**
```python
def should_attempt_fg(self) -> tuple[bool, Dict]:
    """Return (decision, reasoning) for field goal attempt."""
    # ... existing logic ...
    
    reasoning = {
        "yardline": self.yardline,
        "distance": 100 - self.yardline + 17,  # FG distance
        "in_range": yardline >= 83,  # Inside 17-yard line
        "decision": "FG"
    }
    
    return decision, reasoning

def should_punt(self) -> tuple[bool, Dict]:
    """Return (decision, reasoning) for punt."""
    # ... existing logic ...
    
    reasoning = {
        "yardline": self.yardline,
        "to_go": self.ydstogo,
        "too_far": yardline < 83,  # Outside FG range
        "too_long": self.ydstogo > 5,
        "decision": "Punt"
    }
    
    return decision, reasoning
```

**In GameSimulator:**
```python
if game_state.down == 4:
    fg_decision, fg_reasoning = game_state.should_attempt_fg()
    self.trace.log("4thdown.decision", {
        "quarter": game_state.quarter,
        "time_remaining": game_state.time_remaining,
        "yardline": game_state.yardline,
        "to_go": game_state.ydstogo,
        "score_diff": game_state.home_score - game_state.away_score,
        **fg_reasoning
    })
    
    if fg_decision:
        # ... attempt FG ...
```

---

### 6. Realism Guards
**File**: `simulator/game_simulator.py`

**New method:**
```python
def _check_realism_guards(self, game_state: GameState):
    """Check if simulation output matches NFL reality."""
    
    # Calculate metrics from game state
    # (This requires tracking during simulation)
    
    guards = [
        ("plays_per_drive", avg_ppd, (5.5, 7.0)),
        ("drives_per_team", drives_per_team, (9.5, 12.5)),
        ("td_pct", td_pct, (0.18, 0.26)),
        ("fg_pct", fg_pct, (0.08, 0.12)),
        ("turnover_pct", to_pct, (0.09, 0.12)),
        ("explosive_rate", explosive_rate, (0.10, 0.12)),
        ("pass_rate", pass_rate, (0.58, 0.62)),
        ("total_points", game_state.home_score + game_state.away_score, (42, 46))
    ]
    
    violations = []
    for metric, observed, (min_val, max_val) in guards:
        if not (min_val <= observed <= max_val):
            violations.append({
                "metric": metric,
                "observed": observed,
                "target_range": (min_val, max_val),
                "violation": "too_low" if observed < min_val else "too_high"
            })
    
    if violations:
        self.trace.log("anchors.violation", {
            "violations": violations,
            "severity": "warning" if len(violations) <= 2 else "critical"
        })
    else:
        self.trace.log("anchors.pass", {
            "message": "All realism guards passed"
        })
```

---

### 7. Trace Viewer Tool
**File**: `tools/trace_view.py` (new file)

**Simple text viewer:**
```python
#!/usr/bin/env python3
"""View simulation traces in human-readable format."""

import json
import sys
from pathlib import Path
from typing import List, Dict

def load_trace(path: Path) -> List[Dict]:
    """Load trace from JSONL file."""
    events = []
    with path.open() as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events

def print_play_by_play(events: List[Dict], verbose: bool = False):
    """Print one-line per play feed."""
    for event in events:
        if event['kind'] == 'play.result':
            payload = event
            play = payload.get('type', 'unknown')
            yards = payload.get('yards', 0)
            td = payload.get('td', False)
            to = payload.get('turnover', False)
            
            line = f"Q{payload.get('quarter', '?')} | {play} | {yards:+d} yds"
            if td:
                line += " | TD"
            if to:
                line += " | TO"
            
            print(line)

def print_drive_table(events: List[Dict]):
    """Print drive summary table."""
    drives = [e for e in events if e['kind'] == 'drive.summary']
    
    print("\n" + "="*80)
    print("DRIVE SUMMARY")
    print("="*80)
    print(f"{'Drive':<8} {'Team':<6} {'Plays':<8} {'Points':<8} {'Result':<15}")
    print("-"*80)
    
    for drive in drives:
        payload = drive
        print(f"{payload.get('drive_no', '?'):<8} "
              f"{payload.get('team', '?'):<6} "
              f"{payload.get('plays', 0):<8} "
              f"{payload.get('points', 0):<8} "
              f"{payload.get('result', '?'):<15}")

def print_game_summary(events: List[Dict]):
    """Print game summary."""
    summary = [e for e in events if e['kind'] == 'game.summary']
    if summary:
        payload = summary[0]
        print("\n" + "="*80)
        print("GAME SUMMARY")
        print("="*80)
        print(f"Final Score: {payload.get('away_score', '?')} - {payload.get('home_score', '?')}")
        print(f"Total: {payload.get('total', '?')} points")
        print(f"Drives per team: {payload.get('drives_per_team', '?')}")
        # ... more metrics ...

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python trace_view.py <trace.jsonl> [--verbose]")
        sys.exit(1)
    
    trace_path = Path(sys.argv[1])
    verbose = "--verbose" in sys.argv
    
    events = load_trace(trace_path)
    
    print_play_by_play(events, verbose)
    print_drive_table(events)
    print_game_summary(events)
```

---

### 8. Integration with Production Scripts

**File**: `scripts/generate_week9_10_predictions.py`

**Add trace support:**
```python
# At top of simulate_one_game function
trace_path = Path("artifacts/traces") / f"{away}_{home}_{week}_{season}.jsonl"
trace_path.parent.mkdir(exist_ok=True)
trace = SimTrace(
    game_id=f"{season}_{week}_{away}_{home}",
    out_path=trace_path,
    seed=42  # Or random seed
)

simulator = GameSimulator(home_team, away_team, trace=trace, seed=42)

# ... run simulation ...

# Save one full trace per game (for 1 out of 2000 simulations)
if simulation_num == 0:  # First simulation gets full trace
    trace.enable = True
else:
    trace.enable = False  # Disable for other sims to save space

# Save summary
if simulation_num == 0:
    trace.save_summary(trace_path.with_suffix('.summary.json'))
```

---

## 📋 Implementation Checklist

- [x] 1. Core tracing infrastructure (`tracing.py`)
- [x] 2. Team profile audit method (`team_profile.as_dict_for_audit()`)
- [ ] 3. GameSimulator trace integration
- [ ] 4. PlaySimulator trace integration
- [ ] 5. Fourth-down decision logging
- [ ] 6. Realism guards
- [ ] 7. Trace viewer tool
- [ ] 8. Production script integration
- [ ] 9. Documentation (`TRANSPARENCY.md`)

---

## 🎯 Benefits

Once implemented, you'll be able to:

1. **Reproduce any game**: Use seed to rerun exact simulation
2. **Debug decisions**: See exactly why each play was called
3. **Validate realism**: Automatically check if output matches NFL
4. **Audit inputs**: Verify correct data was loaded
5. **Trace errors**: Find where things go wrong in complex simulations
6. **Compare runs**: Diff traces to see impact of changes

---

## 📝 Documentation

Create `TRANSPARENCY.md` documenting:

- **Data sources**: nflfastR (behavior), PFF (quality), Situational (context)
- **Calibration**: Market centering, linear calibration, league targets
- **Trace format**: JSONL structure, event types, field meanings
- **Reproducibility**: How to use seeds, rerun games
- **Viewing traces**: How to use trace viewer tools

---

## 🚀 Next Steps

1. **Priority 1**: Integrate tracing into GameSimulator and PlaySimulator
2. **Priority 2**: Add realism guards
3. **Priority 3**: Create trace viewer
4. **Priority 4**: Integrate with production scripts
5. **Priority 5**: Write documentation

