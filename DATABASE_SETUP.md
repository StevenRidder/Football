# PostgreSQL Database Setup for NFL Edge Betting

## Prerequisites

1. **Install PostgreSQL** (if not already installed):
   ```bash
   # macOS
   brew install postgresql@15
   brew services start postgresql@15
   
   # Or use Postgres.app from https://postgresapp.com/
   ```

2. **Install Python dependencies**:
   ```bash
   pip install psycopg2-binary
   ```

## Setup Steps

### 1. Create Database

```bash
# Connect to PostgreSQL
psql postgres

# Create database
CREATE DATABASE nfl_edge;

# Exit psql
\q
```

### 2. Set Database URL (Optional)

If your PostgreSQL is not on localhost with default settings, set the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/nfl_edge"
```

Default (if not set): `postgresql://localhost/nfl_edge`

### 3. Migrate Existing Data

Run the migration script to import your existing bets from JSON into PostgreSQL:

```bash
python3 migrate_bets_to_db.py
```

This will:
- Create all necessary tables and indexes
- Import all bets from `artifacts/betonline_bets.json`
- Properly group round robin bets
- Parse parlay legs into separate table
- Show a summary of migrated data

### 4. Update Flask App

The Flask app will automatically use the database once it's set up. No code changes needed!

## Database Schema

### Tables

1. **`bets`** - Main bets table
   - `id` - Primary key
   - `ticket_id` - Unique ticket identifier
   - `date` - Bet date
   - `description` - Bet description
   - `bet_type` - Type (Parlay, Spread, etc.)
   - `status` - Pending/Won/Lost/Push
   - `amount` - Stake amount
   - `to_win` - Potential winnings
   - `profit` - Actual profit/loss
   - `is_round_robin` - Whether this is part of a round robin
   - `round_robin_parent` - Parent ticket ID if round robin

2. **`parlay_legs`** - Individual legs of parlays
   - `id` - Primary key
   - `bet_id` - Foreign key to bets
   - `leg_number` - Leg order
   - `description` - Leg description
   - `team` - Team name
   - `line` - Betting line
   - `odds` - Odds for this leg

### Views

1. **`pending_bets_summary`** - Quick view of all pending bets
2. **`betting_performance`** - Performance metrics by bet type

## Querying the Database

### Get Pending Bets

```sql
SELECT * FROM pending_bets_summary;
```

### Get Performance Summary

```sql
SELECT * FROM betting_performance;
```

### Get Bet with Parlay Legs

```sql
SELECT 
    b.*,
    pl.leg_number,
    pl.description as leg_description,
    pl.team,
    pl.line,
    pl.odds
FROM bets b
LEFT JOIN parlay_legs pl ON b.id = pl.bet_id
WHERE b.ticket_id = '905966563-1'
ORDER BY pl.leg_number;
```

### Get Round Robin Details

```sql
-- Get parent round robin
SELECT * FROM bets WHERE ticket_id = '905768987-RR';

-- Get all sub-bets
SELECT * FROM bets WHERE round_robin_parent = '905768987-RR';
```

## Benefits of Database Approach

1. ✅ **Proper Data Structure** - Normalized schema with relationships
2. ✅ **Fast Queries** - Indexed for performance
3. ✅ **Data Integrity** - Constraints and validation
4. ✅ **Easy Reporting** - SQL views for common queries
5. ✅ **Scalability** - Can handle thousands of bets
6. ✅ **Historical Tracking** - Track updates with timestamps
7. ✅ **Parlay Details** - Separate table for individual legs

## Maintenance

### Backup Database

```bash
pg_dump nfl_edge > nfl_edge_backup.sql
```

### Restore Database

```bash
psql nfl_edge < nfl_edge_backup.sql
```

### Reset Database

```bash
psql postgres -c "DROP DATABASE IF EXISTS nfl_edge;"
psql postgres -c "CREATE DATABASE nfl_edge;"
python3 migrate_bets_to_db.py
```

