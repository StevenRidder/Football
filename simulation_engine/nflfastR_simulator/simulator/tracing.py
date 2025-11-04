"""
Simulation Tracing: Complete transparency for debugging and validation.

Every decision, input, and outcome is logged to a trace file.
This enables:
- Reproducibility (same seed = same result)
- Debugging (why did this decision happen?)
- Validation (does this look like real football?)
- Auditing (what inputs were used?)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import time
from pathlib import Path
import numpy as np


def _convert_to_json_serializable(obj):
    """Recursively convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, dict):
        return {k: _convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_json_serializable(item) for item in obj]
    else:
        return obj


@dataclass
class SimTrace:
    """Game-wide trace for complete transparency."""

    game_id: str
    enable: bool = True
    buffer: List[Dict[str, Any]] = field(default_factory=list)
    out_path: Optional[Path] = None
    seed: Optional[int] = None

    def log(self, kind: str, payload: Dict[str, Any]):
        """Log an event to the trace.
        
        Args:
            kind: Event type (e.g., 'inputs.audit', 'call.pass_run', 'play.result')
            payload: Event data (dict of key-value pairs)
        """
        if not self.enable:
            return

        rec = {
            "t": time.time(),
            "kind": kind,
            "game_id": self.game_id,
            **payload
        }

        # Convert numpy types to native Python types for JSON serialization
        rec = _convert_to_json_serializable(rec)

        self.buffer.append(rec)

        # Write to file if path provided (JSONL format)
        if self.out_path:
            with self.out_path.open("a") as f:
                f.write(json.dumps(rec) + "\n")

    def flush(self):
        """Flush buffer to disk if using file output."""
        if self.out_path and self.buffer:
            # Already written incrementally, but ensure flush
            pass

    def get_events(self, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all events, optionally filtered by kind.
        
        Args:
            kind: Optional event type filter
            
        Returns:
            List of event dictionaries
        """
        if kind is None:
            return self.buffer.copy()
        return [e for e in self.buffer if e.get('kind') == kind]

    def clear(self):
        """Clear the trace buffer."""
        self.buffer.clear()

    def save_summary(self, path: Path):
        """Save a summary of the trace to JSON.
        
        Args:
            path: Path to save summary JSON
        """
        summary = {
            "game_id": self.game_id,
            "seed": self.seed,
            "total_events": len(self.buffer),
            "event_types": {},
            "events": self.buffer
        }

        # Count events by type
        for event in self.buffer:
            event_type = event.get('kind', 'unknown')
            summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1

        # Convert numpy types to native Python types for JSON serialization
        summary = _convert_to_json_serializable(summary)

        with path.open("w") as f:
            json.dump(summary, f, indent=2)

