# NFL Betting Application - Server Management

## Quick Commands

### Start Server
```bash
./start_server.sh
```
Starts the Flask application on port 9876.

### Stop Server
```bash
./stop_server.sh
```
Stops all processes running on port 9876.

### Restart Server
```bash
./restart_server.sh
```
Stops and starts the server (useful after code changes).

### Check Status
```bash
./status_server.sh
```
Shows if server is running and displays recent logs.

## URLs

- **Main Page:** http://localhost:9876/
- **My Bets:** http://localhost:9876/bets
- **Performance:** http://localhost:9876/performance
- **Model Accuracy:** http://localhost:9876/accuracy

## Logs

View live logs:
```bash
tail -f flask.log
```

View last 50 lines:
```bash
tail -50 flask.log
```

## Troubleshooting

### Server won't start
1. Check if port 9876 is in use: `lsof -ti:9876`
2. Stop any existing processes: `./stop_server.sh`
3. Check logs: `tail -50 flask.log`
4. Try starting again: `./start_server.sh`

### Server is slow/unresponsive
```bash
./restart_server.sh
```

### Can't connect to database
Make sure PostgreSQL is running:
```bash
psql -d nfl_edge -U steveridder -c "SELECT 1"
```

## Files

- `start_server.sh` - Start the server
- `stop_server.sh` - Stop the server
- `restart_server.sh` - Restart the server
- `status_server.sh` - Check server status
- `flask.log` - Application logs
- `app_flask.py` - Main Flask application

## Notes

- Server runs in background (nohup)
- Logs are written to `flask.log`
- Debug mode is ON (auto-reloads on code changes)
- Port 9876 is the default port

