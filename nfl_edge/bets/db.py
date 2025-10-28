"""
Database connection and operations for betting data
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
import os
from typing import List, Dict, Any, Optional
from .leg_parser import ParlayLegParser

class BettingDB:
    def __init__(self, db_url: Optional[str] = None):
        """Initialize database connection"""
        self.db_url = db_url or os.getenv('DATABASE_URL', 'postgresql://localhost/nfl_edge')
        self.conn = None
        
    def connect(self):
        """Establish database connection"""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def init_schema(self):
        """Initialize database schema"""
        schema_path = Path(__file__).parent / 'schema.sql'
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
    
    def insert_bet(self, bet: Dict[str, Any]) -> int:
        """Insert a single bet and return its ID. Automatically parses and persists parlay legs."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bets (
                    ticket_id, date, description, bet_type, status, 
                    amount, to_win, profit, is_round_robin, round_robin_parent
                ) VALUES (
                    %(ticket_id)s, %(date)s, %(description)s, %(bet_type)s, %(status)s,
                    %(amount)s, %(to_win)s, %(profit)s, %(is_round_robin)s, %(round_robin_parent)s
                )
                ON CONFLICT (ticket_id) DO UPDATE SET
                    date = EXCLUDED.date,
                    description = EXCLUDED.description,
                    bet_type = EXCLUDED.bet_type,
                    status = EXCLUDED.status,
                    amount = EXCLUDED.amount,
                    to_win = EXCLUDED.to_win,
                    profit = EXCLUDED.profit,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, {
                'ticket_id': bet['ticket_id'],
                'date': bet['date'],
                'description': bet.get('description', ''),
                'bet_type': bet.get('bet_type', bet.get('type', 'Unknown')),
                'status': bet['status'],
                'amount': bet['amount'],
                'to_win': bet.get('to_win', 0),
                'profit': bet.get('profit', 0),
                'is_round_robin': bet.get('is_round_robin', False),
                'round_robin_parent': bet.get('round_robin_parent')
            })
            bet_id = cur.fetchone()['id']
        conn.commit()
        
        # Auto-parse and persist parlay legs
        bet_type = bet.get('bet_type', bet.get('type', ''))
        description = bet.get('description', '')
        if 'parlay' in bet_type.lower() and description:
            legs = ParlayLegParser.parse_legs(description, bet_type)
            if legs:
                self.insert_parlay_legs(bet_id, legs)
        
        return bet_id
    
    def insert_parlay_legs(self, bet_id: int, legs: List[Dict[str, Any]]):
        """Insert parlay legs for a bet"""
        conn = self.connect()
        with conn.cursor() as cur:
            # Delete existing legs
            cur.execute("DELETE FROM parlay_legs WHERE bet_id = %s", (bet_id,))
            
            # Insert new legs
            for i, leg in enumerate(legs, 1):
                cur.execute("""
                    INSERT INTO parlay_legs (bet_id, leg_number, description, team, line, odds)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    bet_id,
                    i,
                    leg.get('description', ''),
                    leg.get('team'),
                    leg.get('line'),
                    leg.get('odds')
                ))
        conn.commit()
    
    def get_pending_bets(self) -> List[Dict[str, Any]]:
        """Get all pending bets"""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    b.*,
                    COALESCE(
                        (SELECT COUNT(*) FROM bets b2 WHERE b2.round_robin_parent = b.ticket_id),
                        0
                    ) as round_robin_count
                FROM bets b
                WHERE status = 'Pending'
                ORDER BY date DESC, ticket_id
            """)
            return cur.fetchall()
    
    def get_bet_with_legs(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get a bet with its parlay legs"""
        conn = self.connect()
        with conn.cursor() as cur:
            # Get bet
            cur.execute("SELECT * FROM bets WHERE ticket_id = %s", (ticket_id,))
            bet = cur.fetchone()
            
            if not bet:
                return None
            
            # Get legs if it's a parlay
            cur.execute("""
                SELECT * FROM parlay_legs 
                WHERE bet_id = %s 
                ORDER BY leg_number
            """, (bet['id'],))
            legs = cur.fetchall()
            
            bet_dict = dict(bet)
            bet_dict['legs'] = legs
            return bet_dict
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall betting performance summary"""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total_bets,
                    SUM(amount) as total_wagered,
                    SUM(CASE WHEN status = 'Won' THEN 1 ELSE 0 END) as won_count,
                    SUM(CASE WHEN status = 'Lost' THEN 1 ELSE 0 END) as lost_count,
                    SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_count,
                    SUM(CASE WHEN status = 'Pending' THEN amount ELSE 0 END) as pending_amount,
                    SUM(CASE WHEN status = 'Pending' THEN to_win ELSE 0 END) as pending_to_win,
                    SUM(profit) as total_profit,
                    CASE 
                        WHEN SUM(amount) > 0 THEN (SUM(profit) / SUM(amount) * 100)
                        ELSE 0
                    END as roi,
                    CASE 
                        WHEN SUM(CASE WHEN status IN ('Won', 'Lost') THEN 1 ELSE 0 END) > 0 
                        THEN (SUM(CASE WHEN status = 'Won' THEN 1 ELSE 0 END)::DECIMAL / 
                              SUM(CASE WHEN status IN ('Won', 'Lost') THEN 1 ELSE 0 END) * 100)
                        ELSE 0
                    END as win_rate
                FROM bets
                WHERE is_round_robin = FALSE OR round_robin_parent IS NULL
            """)
            return cur.fetchone()
    
    def get_performance_by_type(self) -> List[Dict[str, Any]]:
        """Get performance breakdown by bet type"""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM betting_performance ORDER BY total_wagered DESC")
            return cur.fetchall()
    
    def update_bet_status(self, ticket_id: str, status: str, profit: float = None):
        """Update bet status and profit"""
        conn = self.connect()
        with conn.cursor() as cur:
            if profit is not None:
                cur.execute("""
                    UPDATE bets 
                    SET status = %s, profit = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE ticket_id = %s
                """, (status, profit, ticket_id))
            else:
                cur.execute("""
                    UPDATE bets 
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE ticket_id = %s
                """, (status, ticket_id))
        conn.commit()

