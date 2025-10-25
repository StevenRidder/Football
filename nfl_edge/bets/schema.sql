-- NFL Edge Betting Database Schema

-- Main bets table
CREATE TABLE IF NOT EXISTS bets (
    id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(50) UNIQUE NOT NULL,
    date DATE NOT NULL,
    description TEXT,
    bet_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('Pending', 'Won', 'Lost', 'Push')),
    amount DECIMAL(10, 2) NOT NULL,
    to_win DECIMAL(10, 2),
    profit DECIMAL(10, 2) DEFAULT 0,
    is_round_robin BOOLEAN DEFAULT FALSE,
    round_robin_parent VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Parlay legs table (for detailed breakdown of parlays)
CREATE TABLE IF NOT EXISTS parlay_legs (
    id SERIAL PRIMARY KEY,
    bet_id INTEGER REFERENCES bets(id) ON DELETE CASCADE,
    leg_number INTEGER NOT NULL,
    description TEXT NOT NULL,
    team VARCHAR(50),
    line VARCHAR(50),
    odds VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bets_status ON bets(status);
CREATE INDEX IF NOT EXISTS idx_bets_date ON bets(date);
CREATE INDEX IF NOT EXISTS idx_bets_ticket_id ON bets(ticket_id);
CREATE INDEX IF NOT EXISTS idx_bets_round_robin_parent ON bets(round_robin_parent);
CREATE INDEX IF NOT EXISTS idx_parlay_legs_bet_id ON parlay_legs(bet_id);

-- View for pending bets summary
CREATE OR REPLACE VIEW pending_bets_summary AS
SELECT 
    ticket_id,
    date,
    description,
    bet_type,
    status,
    amount,
    to_win,
    CASE 
        WHEN is_round_robin THEN 
            (SELECT COUNT(*) FROM bets b2 WHERE b2.round_robin_parent = bets.ticket_id)
        ELSE NULL
    END as round_robin_count
FROM bets
WHERE status = 'Pending'
ORDER BY date DESC, ticket_id;

-- View for performance analytics
CREATE OR REPLACE VIEW betting_performance AS
SELECT 
    bet_type,
    COUNT(*) as total_bets,
    SUM(amount) as total_wagered,
    SUM(CASE WHEN status = 'Won' THEN 1 ELSE 0 END) as won_count,
    SUM(CASE WHEN status = 'Lost' THEN 1 ELSE 0 END) as lost_count,
    SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_count,
    SUM(profit) as total_profit,
    CASE 
        WHEN SUM(amount) > 0 THEN (SUM(profit) / SUM(amount) * 100)
        ELSE 0
    END as roi_percentage,
    CASE 
        WHEN SUM(CASE WHEN status IN ('Won', 'Lost') THEN 1 ELSE 0 END) > 0 
        THEN (SUM(CASE WHEN status = 'Won' THEN 1 ELSE 0 END)::DECIMAL / 
              SUM(CASE WHEN status IN ('Won', 'Lost') THEN 1 ELSE 0 END) * 100)
        ELSE 0
    END as win_rate_percentage
FROM bets
WHERE is_round_robin = FALSE OR round_robin_parent IS NULL
GROUP BY bet_type;

