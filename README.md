# SaddleUp.io - Horse Racing Gambling Game

A real-time WebSocket-based horse racing gambling game built with Python backend and HTML/JS frontend. Features intelligent AI players, stat-based odds, visual color coding, and comprehensive race analytics. Supports 1000+ concurrent users with in-memory storage for fast performance.

## Game Features

- **20 horses per race** with hidden stats (speed, stamina, consistency) that determine realistic odds
- **3 bet types**: Winner ($1), Place ($1), Box Trifecta ($1) with 15% house edge
- **Color-coded horses**: Visual odds indicators using blue (favorites) to red (longshots) both in betting and racing
- **Dynamic betting period** with real-time odds updates every 0.25 seconds
- **Live race simulation** ending 1 second after third place finishes
- **Comprehensive results** showing top 3 horses with odds, trifecta info, and top 10 race winners
- **Active bets display** during races showing player's current wagers
- **AI player system** with up to 1000 intelligent bots with realistic names and betting patterns
- **Continuous race cycles** with automatic progression
- **$10 starting balance** for all players (exactly $10.00 with 2 decimal place precision)
- **Real-time leaderboard** mixing human and AI players
- **Visual odds legend** explaining color coding system

## Technical Architecture

### Backend (Python)
- **WebSocket server** using `asyncio` and `websockets` library
- **In-memory data storage** for users, races, betting pools, and leaderboards
- **Real-time race simulation engine** with stat-based horse movement
- **Sophisticated odds calculation** based on horse stats and betting pools with 15% house edge
- **AI player management** with 1000 intelligent bots using realistic betting strategies
- **Concurrent user support** for 1000+ players
- **Stateless design** - all data stored in memory

### Frontend (HTML/JS)
- **Real-time WebSocket connection** for live updates
- **Responsive design** with mobile support
- **Color-coded betting interface** with visual odds indicators (blue to red scale)
- **Live race visualization** with color-coded animated horses matching odds (hidden during betting phase)
- **Active bets tracking** showing player's current race wagers
- **Real-time odds display** updating every 250ms with $X.XX format
- **Visual odds legend** with color-coded guide for all odds tiers
- **Persistent leaderboard sidebar** showing top 10 players
- **Comprehensive race results** with detailed analytics and top winners
- **Precision currency display** - all amounts rounded to exactly 2 decimal places

## Project Structure

```
saddleup/
├── backend/
│   ├── models.py           # Data models (Horse, Race, User, Bet, GameState)
│   ├── race_engine.py      # Race simulation and payout calculation
│   ├── websocket_server.py # WebSocket server and game loop
│   ├── ai_players.py       # AI player management and betting logic
│   ├── services.py         # Business logic services (betting, race, payout)
│   ├── utils.py            # Utility functions and error handling
│   ├── config.py           # Configuration management
│   ├── game_logger.py      # Discord webhook logging system
│   └── server.py           # Main server entry point
├── frontend/
│   ├── index.html          # Main HTML interface
│   ├── styles.css          # CSS styling and animations
│   └── script.js           # JavaScript WebSocket client
├── config/
│   └── settings.py         # Configuration settings
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Quick Start

### Prerequisites
- Python 3.7+ 
- Modern web browser with WebSocket support

### Installation

1. **Clone and setup:**
```bash
git clone <repository>
cd saddleup
pip install -r requirements.txt
```

2. **Start the server:**
```bash
cd backend
python server.py
```

3. **Open the game:**
   - Open `frontend/index.html` in your web browser
   - Or serve via HTTP server: `python -m http.server 8080` from frontend directory

4. **Play:**
   - Enter a username to join
   - Place bets during 30-second betting periods
   - Watch races and collect winnings!

## Development Commands

### Start Development Server
```bash
cd backend
python server.py
```

### Run with Custom Configuration
```bash
# Set environment variables
export WEBSOCKET_PORT=9000
export BETTING_DURATION=45
export MAX_CONCURRENT_USERS=2000

# Optional: Enable Discord webhook logging
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/your-webhook-url"
export ENVIRONMENT="production"

cd backend
python server.py
```

### Serve Frontend
```bash
cd frontend
python -m http.server 8080
# Open http://localhost:8080
```

## Configuration

All game settings can be configured via environment variables in `config/settings.py`:

- `WEBSOCKET_HOST` - Server host (default: localhost)
- `WEBSOCKET_PORT` - Server port (default: 8765)  
- `BETTING_DURATION` - Betting phase duration in seconds (default: 30)
- `RACING_DURATION` - Race duration in seconds (default: 30)
- `RESULTS_DURATION` - Results phase duration in seconds (default: 10)
- `ODDS_UPDATE_INTERVAL` - Odds update frequency in seconds (default: 0.25)
- `STARTING_BALANCE` - Player starting balance (default: $10)
- `MAX_CONCURRENT_USERS` - Maximum concurrent connections (default: 1000)

### Discord Webhook Logging

Optional Discord webhook integration for server monitoring:

- `DISCORD_WEBHOOK_URL` - Discord webhook URL for notifications
- `ENVIRONMENT` - Set to "production" to enable Discord notifications (default: development)

**Discord Features:**
- User connection/disconnection notifications
- Server status updates every 10 races
- Error logging and monitoring
- Rich embed formatting with colored messages
- Development mode logs to console instead of Discord

## Game Mechanics

### Betting Types
1. **Winner** - Pick the horse that finishes 1st place
2. **Place** - Pick a horse that finishes in top 3 (pays maximum 1/3 of win odds)
3. **Box Trifecta** - Pick 3 horses to finish in top 3 in any order (easier than exact trifecta)

### Advanced Odds System
- **Enhanced stat-based odds** with expanded horse stat ranges (0.6-1.4) for realistic diversity
- **Power-scaled probability** enhancement making favorites and longshots more distinct
- **Dynamic adjustment** as bets are placed with 15% house edge maintained
- **Realistic place odds** - Place odds calculated as maximum 1/3 of win odds for proper pari-mutuel betting
- **Realistic odds distribution** creating proper favorites ($1.20-$2.50) to longshots ($10.00+)
- **Visual color coding**: Blue (≤$1.50) → Green (≤$2.50) → Yellow (≤$4.00) → Orange (≤$8.00) → Red (>$8.00)
- **Live updates** every 1 second during betting phase with $X.XX format display

### Race Simulation
- **Stat-based performance** - Horse stats determine racing ability
- **Color-coded horses** - Racing horses display same color as their odds (blue=favorites, red=longshots)
- **Dynamic race duration** - Ends 1 second after third place finishes
- **Real-time position updates** with 100ms intervals for smooth animation
- **Fair randomization** ensures unpredictable but realistic outcomes

### AI Player System
- **Intelligent betting** - 4 personality types (Conservative, Aggressive, Balanced, Longshot)
- **Realistic names** - Generated from pools of common first/last names
- **Distributed betting** - Bets spread throughout 30-second betting period
- **Dynamic population** - Maintains up to 1000 total players (1000 minus humans)

## Performance Features

- **In-memory storage** for sub-millisecond data access
- **Concurrent WebSocket handling** with asyncio
- **Efficient broadcasting** to all connected clients
- **Automatic reconnection** on client disconnect
- **Memory-efficient** user session management
- **Optimized race simulation** with minimal CPU usage

## WebSocket API

### Client → Server Messages
```javascript
// Login
{type: "login", username: "player1"}

// Place bet
{type: "place_bet", bet_type: "winner", amount: 1.0, selection: [5]}
{type: "place_bet", bet_type: "trifecta", amount: 1.0, selection: [5, 12, 8]}

// Get race state
{type: "get_race_state"}

// Get leaderboard  
{type: "get_leaderboard"}
```

### Server → Client Messages
```javascript
// Race state update
{type: "race_state", race: {...}, odds: {...}}

// Live race updates
{type: "race_update", horses: [...]}

// Comprehensive race results
{type: "race_results", results: [...], trifecta_info: {...}, top_winners: [...], payouts: {...}}

// Live odds updates
{type: "odds_update", odds: {...}, time_remaining: 25}

// Phase updates
{type: "phase_update", phase: "results", time_remaining: 8}

// Leaderboard updates
{type: "leaderboard", leaders: [...]}
```

## Scaling Considerations

- **Horizontal scaling**: Multiple server instances with load balancer
- **Database integration**: Replace in-memory storage for persistence
- **Redis clustering**: Shared state across server instances  
- **CDN**: Serve static frontend assets
- **WebSocket proxy**: Handle connection management at scale

## Security & Performance Features

### Security
- **Comprehensive input validation** - All bet amounts, selections, and user data validated
- **Rate limiting** - IP-based connection limits (5 connections per IP per minute)
- **Session management** with unique user IDs
- **Error handling** with graceful degradation and recovery
- **No sensitive data exposure** in client communications

### Performance & Reliability
- **Optimized broadcasting** - Pre-serialized messages with batched delivery
- **Efficient rank updates** - Leaderboard calculations only during state changes, not during betting
- **Limited leaderboard display** - Only top 10 users transmitted to prevent network overload
- **Race condition prevention** - Atomic operations for AI player management
- **Overflow protection** - Safe odds calculations with bounds checking
- **Memory efficiency** - Automatic cleanup of disconnected players
- **Error recovery** - Game loop continues despite individual component failures
- **Precision handling** - All currency amounts rounded to exactly 2 decimal places