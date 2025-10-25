#!/bin/bash
# Quick setup script for PostgreSQL database

echo "🏈 NFL Edge - Database Setup"
echo "=============================="
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL not found!"
    echo "   Install with: brew install postgresql@15"
    exit 1
fi

echo "✅ PostgreSQL found"

# Check if database exists
if psql -lqt | cut -d \| -f 1 | grep -qw nfl_edge; then
    echo "⚠️  Database 'nfl_edge' already exists"
    read -p "   Drop and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Dropping existing database..."
        dropdb nfl_edge 2>/dev/null || true
    else
        echo "   Keeping existing database"
    fi
fi

# Create database if it doesn't exist
if ! psql -lqt | cut -d \| -f 1 | grep -qw nfl_edge; then
    echo "📊 Creating database 'nfl_edge'..."
    createdb nfl_edge
    echo "✅ Database created"
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -q psycopg2-binary

# Run migration
echo ""
echo "🔄 Migrating data from JSON to PostgreSQL..."
python3 migrate_bets_to_db.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Update app_flask.py to use database routes (see app_flask_db.py)"
echo "   2. Restart Flask server"
echo "   3. Visit http://localhost:9876/bets"
echo ""
echo "📚 See DATABASE_SETUP.md for more details"

