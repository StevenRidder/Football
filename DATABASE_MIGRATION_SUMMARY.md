# Database Migration Summary

## ✅ What I've Created

### 1. Database Schema (`nfl_edge/bets/schema.sql`)
- **`bets` table**: Main table for all bets with proper types and constraints
- **`parlay_legs` table**: Separate table for individual parlay legs with relationships
- **Indexes**: For fast queries on status, date, ticket_id
- **Views**: `pending_bets_summary` and `betting_performance` for common queries

### 2. Database Client (`nfl_edge/bets/db.py`)
- `BettingDB` class with all CRUD operations
- Methods for:
  - `insert_bet()` - Add/update bets
  - `insert_parlay_legs()` - Add parlay details
  - `get_pending_bets()` - Get all pending bets
  - `get_bet_with_legs()` - Get bet with full parlay details
  - `get_performance_summary()` - Overall stats
  - `get_performance_by_type()` - Breakdown by bet type
  - `update_bet_status()` - Update when bets settle

### 3. Migration Script (`migrate_bets_to_db.py`)
- Imports all bets from `artifacts/betonline_bets.json`
- Properly groups round robin bets
- Parses parlay legs into separate table
- Shows migration summary

### 4. Flask Routes (`app_flask_db.py`)
- Database-backed versions of `/bets` and `/performance` routes
- Drop-in replacement for current JSON-based routes
- Uses efficient SQL queries instead of parsing JSON

### 5. Setup Script (`setup_database.sh`)
- One-command setup: `./setup_database.sh`
- Creates database, runs migration, shows summary

### 6. Documentation
- `DATABASE_SETUP.md` - Complete setup guide
- `DATABASE_MIGRATION_SUMMARY.md` - This file

## 🎯 Benefits

### Current (JSON-based)
- ❌ Parses 352 bets from JSON on every page load
- ❌ Complex grouping logic in Python
- ❌ No parlay leg details
- ❌ Slow for large datasets
- ❌ No data integrity checks

### New (PostgreSQL-based)
- ✅ Fast indexed queries
- ✅ Proper data structure with relationships
- ✅ Parlay legs in separate table
- ✅ Scalable to thousands of bets
- ✅ Data integrity with constraints
- ✅ Easy reporting with SQL views
- ✅ Historical tracking with timestamps

## 📊 Data Structure

### Your Pending Bets (Example)
```
Ticket: 905966563-1
Date: 10/24/2025
Type: Parlay (12 Teams)
Amount: $15.00
To Win: $37,377.61
Status: Pending

Legs:
  1. Carolina Panthers +7 -105
  2. New York Giants +7½ -115
  3. Miami [team]
  4. Cincinnati Bengals -6½ -108
  5. New England Patriots -7 -105
  6. Chicago Bears +6½ -110
  7. Tampa Bay Buccaneers -3½ -112
  8. [team] 280
  9. Houston Texans -2½ -110
  10. Green Bay Packers -3 -105
  11. Washington Commanders +12½ -113
  12. Tennessee Titans +14½ -110
```

### Round Robin (Example)
```
Parent: 905768987-RR
Description: Round Robin (345 combinations)
Total Amount: $345.00
Total To Win: $2,683.12

Sub-bets: 345 individual parlays
  - 905768987-210: Parlay (3 Teams) - $1.00 → $5.74
  - 905768987-209: Parlay (3 Teams) - $1.00 → $5.89
  - ... (343 more)
```

## 🚀 Quick Start

### Option 1: Automated Setup
```bash
./setup_database.sh
```

### Option 2: Manual Setup
```bash
# 1. Create database
createdb nfl_edge

# 2. Install dependencies
pip install psycopg2-binary

# 3. Run migration
python3 migrate_bets_to_db.py

# 4. Update Flask app (see below)
```

## 🔧 Integrating with Flask

Replace the current `/bets` and `/performance` routes in `app_flask.py`:

```python
# At the top of app_flask.py
from nfl_edge.bets.db import BettingDB

# Replace @app.route('/bets') with the version from app_flask_db.py
# Replace @app.route('/performance') with the version from app_flask_db.py
```

Or simply copy the route functions from `app_flask_db.py` into `app_flask.py`.

## 📈 Example Queries

### Get All Pending Bets
```python
db = BettingDB()
pending = db.get_pending_bets()
db.close()
```

### Get Bet with Parlay Details
```python
db = BettingDB()
bet = db.get_bet_with_legs('905966563-1')
# bet['legs'] contains all 12 parlay legs
db.close()
```

### Get Performance Summary
```python
db = BettingDB()
summary = db.get_performance_summary()
# Returns: total_bets, total_wagered, won_count, lost_count, 
#          pending_count, total_profit, roi, win_rate
db.close()
```

### Update Bet Status (When Game Settles)
```python
db = BettingDB()
db.update_bet_status('905769168-1', 'Won', profit=95.24)
db.close()
```

## 🎨 UI Improvements

With the database, you can now:

1. **Show parlay legs in detail** - Each leg in a separate row with team, line, odds
2. **Filter by date range** - Fast SQL queries with indexes
3. **Search by team** - Find all bets involving a specific team
4. **Track historical performance** - See how your betting has evolved
5. **Compare bet types** - Which types are most profitable?
6. **Weekly P/L charts** - Accurate data from database aggregation

## 🔮 Future Enhancements

With this database structure, you can easily add:

- **Bet recommendations** - Compare your bets to model predictions
- **ROI tracking** - Track ROI over time
- **Team performance** - Which teams you bet on most/least successfully
- **Bet timing** - Early week vs. late week performance
- **Live bet tracking** - Separate analysis for live bets
- **Parlay builder** - Suggest optimal parlay combinations
- **Bankroll management** - Track units, Kelly sizing

## ✅ Verification

After migration, verify the data:

```bash
# Connect to database
psql nfl_edge

# Check bet counts
SELECT status, COUNT(*), SUM(amount) FROM bets GROUP BY status;

# Check round robins
SELECT * FROM bets WHERE ticket_id LIKE '%-RR';

# Check parlay legs
SELECT COUNT(*) FROM parlay_legs;

# Exit
\q
```

## 📝 Notes

- The database approach is **much more scalable** than JSON
- All your existing data is preserved
- The migration is **idempotent** (can run multiple times safely)
- Round robins are properly grouped with parent/child relationships
- Parlay legs are parsed and stored for detailed analysis

## 🆘 Troubleshooting

### "Database nfl_edge does not exist"
```bash
createdb nfl_edge
```

### "psycopg2 not found"
```bash
pip install psycopg2-binary
```

### "Connection refused"
```bash
# Start PostgreSQL
brew services start postgresql@15
# Or use Postgres.app
```

### Reset Everything
```bash
dropdb nfl_edge
createdb nfl_edge
python3 migrate_bets_to_db.py
```

