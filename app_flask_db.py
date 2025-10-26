"""
Flask routes using PostgreSQL database for betting data
Replace the /bets and /performance routes in app_flask.py with these
"""

from flask import render_template
from nfl_edge.bets.db import BettingDB

def setup_db_routes(app):
    """Setup database-backed routes for betting"""
    
    @app.route('/bets')
    def bets_db():
        """My Bets Dashboard - Database Version"""
        db = BettingDB()
        
        try:
            # Get pending bets (non-round-robin or round-robin parents only)
            pending_bets = db.get_pending_bets()
            
            # Format for template
            bets_data = []
            for bet in pending_bets:
                bet_dict = dict(bet)
                # Add sub_bets if it's a round robin parent
                if bet_dict.get('round_robin_count', 0) > 0:
                    # Get all sub-bets for this round robin
                    conn = db.connect()
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT * FROM bets 
                            WHERE round_robin_parent = %s 
                            ORDER BY ticket_id
                        """, (bet_dict['ticket_id'],))
                        sub_bets = cur.fetchall()
                    bet_dict['sub_bets'] = [dict(sb) for sb in sub_bets]
                
                bets_data.append(bet_dict)
            
            # Get summary
            summary = db.get_performance_summary()
            summary_data = {
                'total_bets': summary['total_bets'],
                'pending': summary['pending_count'],
                'won': summary['won_count'],
                'lost': summary['lost_count'],
                'total_risked': f"${summary['total_wagered']:.2f}",
                'total_to_win': f"${summary['pending_to_win']:.2f}",
                'total_profit': summary['total_profit'],
                'total_amount': summary['total_wagered'],
                'pending_amount': summary['pending_amount'],
                'potential_win': summary['pending_to_win'],
                'won_count': summary['won_count'],
                'lost_count': summary['lost_count'],
                'pending_count': summary['pending_count'],
                'win_rate': summary['win_rate']
            }
            
        finally:
            db.close()
        
        return render_template('bets.html', 
                             bets=bets_data,
                             summary=summary_data)
    
    @app.route('/performance')
    def performance_db():
        """Betting Performance Analytics - Database Version"""
        db = BettingDB()
        
        try:
            # Get overall stats
            summary = db.get_performance_summary()
            
            stats = {
                'total_profit': summary['total_profit'],
                'total_wagered': summary['total_wagered'],
                'roi': summary['roi'],
                'win_rate': summary['win_rate'],
                'total_bets': summary['total_bets'],
                'won_count': summary['won_count'],
                'lost_count': summary['lost_count'],
                'pending_count': summary['pending_count'],
                'pending_amount': summary['pending_amount']
            }
            
            # Performance by bet type
            by_type_list = db.get_performance_by_type()
            by_type = {}
            for bt in by_type_list:
                by_type[bt['bet_type']] = {
                    'count': bt['total_bets'],
                    'wagered': bt['total_wagered'],
                    'won': bt['won_count'],
                    'lost': bt['lost_count'],
                    'profit': bt['total_profit'],
                    'win_rate': bt['win_rate_percentage'],
                    'roi': bt['roi_percentage']
                }
            
            # Weekly P/L (from database)
            conn = db.connect()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        TO_CHAR(date, 'MM/DD') as week_key,
                        SUM(profit) as profit
                    FROM bets
                    WHERE status IN ('Won', 'Lost')
                    GROUP BY week_key
                    ORDER BY MIN(date)
                """)
                weekly_data = cur.fetchall()
            
            weekly_pl = {
                'weeks': [w['week_key'] for w in weekly_data],
                'values': [float(w['profit']) for w in weekly_data]
            }
            
            # Bet type distribution
            type_distribution = {
                'labels': list(by_type.keys()),
                'values': [by_type[k]['count'] for k in by_type.keys()]
            }
            
            # Recent settled bets
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM bets 
                    WHERE status IN ('Won', 'Lost')
                    AND (is_round_robin = FALSE OR round_robin_parent IS NULL)
                    ORDER BY date DESC, updated_at DESC
                    LIMIT 10
                """)
                recent_settled = [dict(b) for b in cur.fetchall()]
            
        finally:
            db.close()
        
        return render_template('performance.html',
                             stats=stats,
                             by_type=by_type,
                             weekly_pl=weekly_pl,
                             type_distribution=type_distribution,
                             recent_settled=recent_settled)

