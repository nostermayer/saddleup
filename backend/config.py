"""
Configuration management for SaddleUp horse racing game.
Centralizes all configuration values and environment variables.
"""

import os
from typing import Dict, Any


class GameConfig:
    """Configuration class for game settings"""
    
    # WebSocket Server Configuration
    WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "localhost")
    WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8765"))
    
    # Game Timing Configuration
    BETTING_DURATION = float(os.getenv("BETTING_DURATION", "30.0"))  # seconds
    RESULTS_DURATION = float(os.getenv("RESULTS_DURATION", "10.0"))  # seconds
    ODDS_UPDATE_INTERVAL = float(os.getenv("ODDS_UPDATE_INTERVAL", "1.0"))  # seconds
    RACE_UPDATE_INTERVAL = float(os.getenv("RACE_UPDATE_INTERVAL", "0.1"))  # seconds
    
    # Player Configuration
    STARTING_BALANCE = float(os.getenv("STARTING_BALANCE", "10.0"))
    MAX_CONCURRENT_USERS = int(os.getenv("MAX_CONCURRENT_USERS", "1000"))
    MAX_AI_PLAYERS = int(os.getenv("MAX_AI_PLAYERS", "1000"))
    
    # Rate Limiting Configuration
    MAX_CONNECTIONS_PER_IP = int(os.getenv("MAX_CONNECTIONS_PER_IP", "5"))
    RATE_LIMIT_WINDOW = float(os.getenv("RATE_LIMIT_WINDOW", "60.0"))  # seconds
    
    # Betting Configuration
    MIN_BET_AMOUNT = float(os.getenv("MIN_BET_AMOUNT", "1.0"))
    MAX_BET_AMOUNT = float(os.getenv("MAX_BET_AMOUNT", "1.0"))
    HOUSE_EDGE = float(os.getenv("HOUSE_EDGE", "0.15"))
    
    # Race Configuration
    RACE_DISTANCE = float(os.getenv("RACE_DISTANCE", "100.0"))
    HORSES_PER_RACE = int(os.getenv("HORSES_PER_RACE", "20"))
    MAX_RACE_DURATION = float(os.getenv("MAX_RACE_DURATION", "60.0"))  # seconds
    
    # Horse Statistics Configuration
    HORSE_SPEED_MIN = float(os.getenv("HORSE_SPEED_MIN", "0.6"))
    HORSE_SPEED_MAX = float(os.getenv("HORSE_SPEED_MAX", "1.4"))
    HORSE_STAMINA_MIN = float(os.getenv("HORSE_STAMINA_MIN", "0.6"))
    HORSE_STAMINA_MAX = float(os.getenv("HORSE_STAMINA_MAX", "1.4"))
    HORSE_CONSISTENCY_MIN = float(os.getenv("HORSE_CONSISTENCY_MIN", "0.6"))
    HORSE_CONSISTENCY_MAX = float(os.getenv("HORSE_CONSISTENCY_MAX", "1.4"))
    
    # Odds Configuration
    MIN_ODDS = float(os.getenv("MIN_ODDS", "1.01"))
    MAX_ODDS = float(os.getenv("MAX_ODDS", "50.0"))
    ODDS_BLENDING_POOL_WEIGHT = float(os.getenv("ODDS_BLENDING_POOL_WEIGHT", "0.7"))
    ODDS_BLENDING_INITIAL_WEIGHT = float(os.getenv("ODDS_BLENDING_INITIAL_WEIGHT", "0.3"))
    
    # AI Player Configuration
    AI_BET_PROBABILITY = float(os.getenv("AI_BET_PROBABILITY", "0.7"))
    AI_CONSERVATIVE_THRESHOLD = float(os.getenv("AI_CONSERVATIVE_THRESHOLD", "3.0"))
    AI_AGGRESSIVE_THRESHOLD = float(os.getenv("AI_AGGRESSIVE_THRESHOLD", "10.0"))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    @classmethod
    def get_all_config(cls) -> Dict[str, Any]:
        """Get all configuration values as a dictionary"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and not callable(getattr(cls, key))
        }
    
    @classmethod
    def validate_config(cls) -> None:
        """Validate configuration values"""
        errors = []
        
        # Validate timing values
        if cls.BETTING_DURATION <= 0:
            errors.append("BETTING_DURATION must be positive")
        
        if cls.RESULTS_DURATION <= 0:
            errors.append("RESULTS_DURATION must be positive")
        
        if cls.ODDS_UPDATE_INTERVAL <= 0:
            errors.append("ODDS_UPDATE_INTERVAL must be positive")
        
        # Validate player limits
        if cls.MAX_CONCURRENT_USERS <= 0:
            errors.append("MAX_CONCURRENT_USERS must be positive")
        
        if cls.MAX_AI_PLAYERS < 0:
            errors.append("MAX_AI_PLAYERS cannot be negative")
        
        # Validate betting values
        if cls.MIN_BET_AMOUNT <= 0:
            errors.append("MIN_BET_AMOUNT must be positive")
        
        if cls.MAX_BET_AMOUNT < cls.MIN_BET_AMOUNT:
            errors.append("MAX_BET_AMOUNT must be >= MIN_BET_AMOUNT")
        
        if not (0 <= cls.HOUSE_EDGE <= 1):
            errors.append("HOUSE_EDGE must be between 0 and 1")
        
        # Validate horse statistics
        if cls.HORSE_SPEED_MIN <= 0 or cls.HORSE_SPEED_MAX <= cls.HORSE_SPEED_MIN:
            errors.append("Invalid horse speed range")
        
        if cls.HORSE_STAMINA_MIN <= 0 or cls.HORSE_STAMINA_MAX <= cls.HORSE_STAMINA_MIN:
            errors.append("Invalid horse stamina range")
        
        if cls.HORSE_CONSISTENCY_MIN <= 0 or cls.HORSE_CONSISTENCY_MAX <= cls.HORSE_CONSISTENCY_MIN:
            errors.append("Invalid horse consistency range")
        
        # Validate odds configuration
        if cls.MIN_ODDS <= 0:
            errors.append("MIN_ODDS must be positive")
        
        if cls.MAX_ODDS <= cls.MIN_ODDS:
            errors.append("MAX_ODDS must be > MIN_ODDS")
        
        if not (0 <= cls.ODDS_BLENDING_POOL_WEIGHT <= 1):
            errors.append("ODDS_BLENDING_POOL_WEIGHT must be between 0 and 1")
        
        if not (0 <= cls.ODDS_BLENDING_INITIAL_WEIGHT <= 1):
            errors.append("ODDS_BLENDING_INITIAL_WEIGHT must be between 0 and 1")
        
        if abs(cls.ODDS_BLENDING_POOL_WEIGHT + cls.ODDS_BLENDING_INITIAL_WEIGHT - 1.0) > 0.01:
            errors.append("ODDS_BLENDING weights must sum to 1.0")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))


# Validate configuration on module import
GameConfig.validate_config()