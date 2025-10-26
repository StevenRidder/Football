#!/bin/bash
# Export local PostgreSQL database to SQL file for Azure import

echo "📦 Exporting local database..."

# Get database credentials from your local setup
DB_NAME="football_bets"  # Update if different
DB_USER="postgres"       # Update if different
DB_HOST="localhost"

# Export to SQL file
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -f football_bets_export.sql

if [ $? -eq 0 ]; then
    echo "✅ Database exported to: football_bets_export.sql"
    echo ""
    echo "📤 To upload to Azure VM, run:"
    echo "   scp football_bets_export.sql azureuser@YOUR_STATIC_IP:~/Football/"
    echo ""
    echo "📥 Then on the Azure VM, import with:"
    echo "   psql -h YOUR_DB_HOST -U footballadmin -d postgres -f ~/Football/football_bets_export.sql"
else
    echo "❌ Export failed. Check your database credentials."
fi

