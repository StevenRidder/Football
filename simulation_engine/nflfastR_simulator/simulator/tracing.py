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
        
        with path.open("w") as f:
            json.dump(summary, f, indent=2)

