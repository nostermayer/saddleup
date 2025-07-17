import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class BetType(Enum):
    WINNER = "winner"
    PLACE = "place"
    TRIFECTA = "trifecta"


class RacePhase(Enum):
    BETTING = "betting"
    RACING = "racing"
    RESULTS = "results"


@dataclass
class Horse:
    id: int
    name: str
    speed: float = field(default_factory=lambda: random.uniform(0.6, 1.4))
    stamina: float = field(default_factory=lambda: random.uniform(0.6, 1.4))
    consistency: float = field(default_factory=lambda: random.uniform(0.6, 1.4))
    position: float = 0.0
    finished: bool = False
    finish_position: Optional[int] = None


@dataclass
class Bet:
    user_id: str
    bet_type: BetType
    amount: float
    selection: List[int]  # Horse IDs for the bet
    timestamp: float = field(default_factory=time.time)


@dataclass
class User:
    id: str
    username: str
    balance: float = 10.0
    rank: Optional[int] = None
    total_winnings: float = 0.0
    races_played: int = 0
    connected: bool = True


@dataclass
class BettingPool:
    winner_bets: Dict[int, List[Bet]] = field(default_factory=dict)
    place_bets: Dict[int, List[Bet]] = field(default_factory=dict)
    trifecta_bets: List[Bet] = field(default_factory=list)
    
    def get_total_pool(self, bet_type: BetType) -> float:
        if bet_type == BetType.WINNER:
            return sum(sum(bet.amount for bet in bets) for bets in self.winner_bets.values())
        elif bet_type == BetType.PLACE:
            return sum(sum(bet.amount for bet in bets) for bets in self.place_bets.values())
        elif bet_type == BetType.TRIFECTA:
            return sum(bet.amount for bet in self.trifecta_bets)
        return 0.0
    
    def get_horse_pool(self, horse_id: int, bet_type: BetType) -> float:
        if bet_type == BetType.WINNER:
            return sum(bet.amount for bet in self.winner_bets.get(horse_id, []))
        elif bet_type == BetType.PLACE:
            return sum(bet.amount for bet in self.place_bets.get(horse_id, []))
        elif bet_type == BetType.TRIFECTA:
            # For trifecta, return total pool since it's not horse-specific
            return sum(bet.amount for bet in self.trifecta_bets)
        return 0.0


@dataclass
class Race:
    id: int
    horses: List[Horse]
    phase: RacePhase = RacePhase.BETTING
    betting_pool: BettingPool = field(default_factory=BettingPool)
    start_time: float = field(default_factory=time.time)
    betting_end_time: float = 0.0
    racing_end_time: float = 0.0
    results_end_time: float = 0.0
    race_distance: float = 100.0
    finished_horses: List[Horse] = field(default_factory=list)
    
    def add_bet(self, bet: Bet) -> bool:
        if self.phase != RacePhase.BETTING:
            return False
            
        if bet.bet_type == BetType.WINNER:
            horse_id = bet.selection[0]
            if horse_id not in self.betting_pool.winner_bets:
                self.betting_pool.winner_bets[horse_id] = []
            self.betting_pool.winner_bets[horse_id].append(bet)
        elif bet.bet_type == BetType.PLACE:
            horse_id = bet.selection[0]
            if horse_id not in self.betting_pool.place_bets:
                self.betting_pool.place_bets[horse_id] = []
            self.betting_pool.place_bets[horse_id].append(bet)
        elif bet.bet_type == BetType.TRIFECTA:
            self.betting_pool.trifecta_bets.append(bet)
        
        return True
    
    def get_horse_strength(self, horse_id: int) -> float:
        """Calculate a horse's overall strength based on stats"""
        horse = next((h for h in self.horses if h.id == horse_id), None)
        if not horse:
            return 1.0
        return horse.speed * horse.stamina * horse.consistency
    
    def get_initial_odds(self, horse_id: int, bet_type: BetType) -> float:
        """Calculate initial odds based on horse stats before any betting"""
        try:
            horse_strength = self.get_horse_strength(horse_id)
            
            # Validate horse strength
            if not isinstance(horse_strength, (int, float)) or horse_strength <= 0:
                return 2.0  # Fallback odds
            
            # Get all horse strengths to calculate relative probability
            all_strengths = [self.get_horse_strength(h.id) for h in self.horses]
            
            # Filter out invalid strengths and ensure we have valid data
            valid_strengths = [s for s in all_strengths if isinstance(s, (int, float)) and s > 0]
            if not valid_strengths:
                return 2.0  # Fallback odds
            
            total_strength = sum(valid_strengths)
            if total_strength <= 0:
                return 2.0  # Fallback odds
            
            # Calculate base probability (higher strength = higher win chance)
            raw_probability = horse_strength / total_strength
            
            # Validate raw probability
            if not isinstance(raw_probability, (int, float)) or raw_probability <= 0 or raw_probability > 1:
                return 2.0  # Fallback odds
            
            # Enhance probability differences by applying power scaling
            # This makes stronger horses more favored and weaker horses longer shots
            enhanced_probability = pow(raw_probability, 0.7)  # Makes differences more pronounced
            
            if bet_type == BetType.WINNER:
                # For winner bets, use enhanced probability
                true_probability = enhanced_probability
            elif bet_type == BetType.PLACE:
                # For place bets (top 3), much higher chance
                true_probability = min(0.85, enhanced_probability * 4.0)  # Cap at 85%
            else:  # Box Trifecta
                # Box trifecta odds are lower than exact order but still challenging
                # For box trifecta, we need horse to be in top 3 (any order)
                true_probability = enhanced_probability * 0.8
            
            # Validate true probability
            if not isinstance(true_probability, (int, float)) or true_probability <= 0:
                return 2.0  # Fallback odds
            
            # Convert to fair odds first (1/probability)
            if true_probability <= 0:
                return 2.0  # Fallback odds
            
            fair_odds = 1 / true_probability
            
            # Apply house edge by reducing the odds payout (making them worse for players)
            house_edge = 0.15
            final_odds = fair_odds * (1 - house_edge)
            
            # Validate final odds
            if not isinstance(final_odds, (int, float)) or final_odds != final_odds or final_odds == float('inf'):
                return 2.0  # Fallback odds
            
            return round(max(1.01, min(final_odds, 50.0)), 2)  # Between 1.01:1 and 50:1, rounded to 2 decimal places
            
        except (ZeroDivisionError, OverflowError, ValueError, TypeError):
            return 2.0  # Fallback odds
    
    def calculate_odds(self, horse_id: int, bet_type: BetType) -> float:
        """Calculate current odds including betting pool adjustments"""
        try:
            total_pool = self.betting_pool.get_total_pool(bet_type)
            horse_pool = self.betting_pool.get_horse_pool(horse_id, bet_type)
            
            # Validate inputs to prevent overflow
            if not isinstance(total_pool, (int, float)) or not isinstance(horse_pool, (int, float)):
                return self.get_initial_odds(horse_id, bet_type)
            
            if total_pool < 0 or horse_pool < 0:
                return self.get_initial_odds(horse_id, bet_type)
            
            # If no betting yet, return initial odds
            if total_pool == 0 or total_pool < 0.01:
                return self.get_initial_odds(horse_id, bet_type)
            
            # If no bets on this horse, return high odds
            if horse_pool == 0 or horse_pool < 0.01:
                initial_odds = self.get_initial_odds(horse_id, bet_type)
                return min(initial_odds * 2, 50.0)  # Cap at 50:1
            
            # Calculate pool-based odds with 15% house edge
            house_edge = 0.15
            
            # Available payout pool after house edge (prevent division by zero)
            payout_pool = max(0.01, total_pool * (1 - house_edge))
            
            # Calculate fair odds based on betting pools with overflow protection
            if horse_pool > 0.01:
                pool_odds = min(50.0, payout_pool / horse_pool)  # Cap at 50:1
            else:
                pool_odds = 50.0
            
            # Validate pool_odds to prevent NaN/Infinity
            if not isinstance(pool_odds, (int, float)) or pool_odds != pool_odds or pool_odds == float('inf'):
                pool_odds = 50.0
            
            # Blend with initial odds to prevent extreme swings
            initial_odds = self.get_initial_odds(horse_id, bet_type)
            
            # Ensure both values are valid before blending
            if not isinstance(initial_odds, (int, float)) or initial_odds != initial_odds:
                return 2.0  # Fallback odds
            
            blended_odds = (pool_odds * 0.7) + (initial_odds * 0.3)
            
            # Final validation and bounds checking
            if not isinstance(blended_odds, (int, float)) or blended_odds != blended_odds:
                return 2.0  # Fallback odds
            
            return round(max(1.01, min(blended_odds, 50.0)), 2)  # Between 1.01:1 and 50:1, rounded to 2 decimal places
            
        except (ZeroDivisionError, OverflowError, ValueError, TypeError) as e:
            # Return safe fallback odds on any calculation error
            return self.get_initial_odds(horse_id, bet_type)


@dataclass
class GameState:
    users: Dict[str, User] = field(default_factory=dict)
    current_race: Optional[Race] = None
    race_counter: int = 0
    leaderboard: List[User] = field(default_factory=list)
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)
    
    def add_user(self, user: User):
        self.users[user.id] = user
        self.update_leaderboard()
    
    def update_leaderboard(self, ai_users=None):
        # Include both human and AI players in leaderboard
        all_users = list(self.users.values())
        if ai_users:
            all_users.extend(ai_users)
        
        # Only include connected human players and all AI players for leaderboard
        eligible_users = [
            user for user in all_users 
            if (user.connected or user.id.startswith('ai_'))
        ]

        eligible_users = sorted(eligible_users, key=lambda x: x.balance, reverse=True)
        for i, user in enumerate(eligible_users):
            user.rank = i + 1

        self.leaderboard = eligible_users[:10]