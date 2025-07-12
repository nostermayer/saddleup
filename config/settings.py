import os

# Server Configuration
WEBSOCKET_HOST = os.getenv('WEBSOCKET_HOST', 'localhost')
WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT', 8765))

# Game Configuration
BETTING_DURATION = float(os.getenv('BETTING_DURATION', 30.0))  # seconds
RACING_DURATION = float(os.getenv('RACING_DURATION', 30.0))   # seconds  
RESULTS_DURATION = float(os.getenv('RESULTS_DURATION', 10.0)) # seconds
ODDS_UPDATE_INTERVAL = float(os.getenv('ODDS_UPDATE_INTERVAL', 0.25))  # seconds

# Race Configuration
NUM_HORSES = int(os.getenv('NUM_HORSES', 20))
RACE_DISTANCE = float(os.getenv('RACE_DISTANCE', 100.0))
STARTING_BALANCE = float(os.getenv('STARTING_BALANCE', 10.0))

# Bet Configuration  
WINNER_BET_AMOUNT = float(os.getenv('WINNER_BET_AMOUNT', 1.0))
PLACE_BET_AMOUNT = float(os.getenv('PLACE_BET_AMOUNT', 1.0))
TRIFECTA_BET_AMOUNT = float(os.getenv('TRIFECTA_BET_AMOUNT', 1.0))

# Performance Configuration
MAX_CONCURRENT_USERS = int(os.getenv('MAX_CONCURRENT_USERS', 1000))
LEADERBOARD_SIZE = int(os.getenv('LEADERBOARD_SIZE', 10))

# Horse Stats Ranges
HORSE_SPEED_MIN = float(os.getenv('HORSE_SPEED_MIN', 0.8))
HORSE_SPEED_MAX = float(os.getenv('HORSE_SPEED_MAX', 1.2))
HORSE_STAMINA_MIN = float(os.getenv('HORSE_STAMINA_MIN', 0.8))
HORSE_STAMINA_MAX = float(os.getenv('HORSE_STAMINA_MAX', 1.2))
HORSE_CONSISTENCY_MIN = float(os.getenv('HORSE_CONSISTENCY_MIN', 0.8))
HORSE_CONSISTENCY_MAX = float(os.getenv('HORSE_CONSISTENCY_MAX', 1.2))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Development Mode
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'