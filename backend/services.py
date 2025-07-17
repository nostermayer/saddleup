"""
Service layer for SaddleUp horse racing game.
Contains business logic separated from WebSocket handling.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from models import User, Race, Bet, BetType, GameState

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class BettingService:
    """Handles all betting-related business logic"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
    
    def validate_bet_request(self, user: User, race: Race, bet_type: str, amount: float, selection: List[int]) -> Dict[str, Any]:
        """Validate a bet request and return validation result"""
        try:
            # Convert bet_type string to enum
            bet_type_enum = BetType(bet_type)
        except ValueError:
            return {"valid": False, "error": "Invalid bet type"}
        
        # Check if betting is open
        if not race or race.phase.value != 'betting':
            return {"valid": False, "error": "Betting is closed"}
        
        # Check user balance
        if user.balance < amount:
            return {"valid": False, "error": "Insufficient balance"}
        
        # Check for duplicate bets
        existing_bets = self.get_user_bets_for_race(user.id, race)
        if any(bet.bet_type == bet_type_enum for bet in existing_bets):
            return {"valid": False, "error": f"You can only place one {bet_type} bet per race"}
        
        # Validate selection based on bet type
        validation_result = self.validate_selection(bet_type_enum, selection, race)
        if not validation_result["valid"]:
            return validation_result
        
        return {"valid": True, "bet_type": bet_type_enum, "amount": amount, "selection": selection}
    
    def validate_selection(self, bet_type: BetType, selection: List[int], race: Race) -> Dict[str, Any]:
        """Validate bet selection based on bet type"""
        if not selection:
            return {"valid": False, "error": "No selection provided"}
        
        # Check if all horses exist in race
        horse_ids = [horse.id for horse in race.horses]
        for horse_id in selection:
            if horse_id not in horse_ids:
                return {"valid": False, "error": f"Horse {horse_id} not found in race"}
        
        # Validate based on bet type
        if bet_type in [BetType.WINNER, BetType.PLACE]:
            if len(selection) != 1:
                return {"valid": False, "error": f"{bet_type.value} bet requires exactly 1 horse"}
        elif bet_type == BetType.TRIFECTA:
            if len(selection) != 3:
                return {"valid": False, "error": "Trifecta bet requires exactly 3 horses"}
            if len(set(selection)) != 3:
                return {"valid": False, "error": "Trifecta bet requires 3 different horses"}
        
        return {"valid": True}
    
    def get_user_bets_for_race(self, user_id: str, race: Race) -> List[Bet]:
        """Get all bets placed by a user for a specific race"""
        bets = []
        
        # Check winner bets
        for horse_bets in race.betting_pool.winner_bets.values():
            bets.extend([bet for bet in horse_bets if bet.user_id == user_id])
        
        # Check place bets
        for horse_bets in race.betting_pool.place_bets.values():
            bets.extend([bet for bet in horse_bets if bet.user_id == user_id])
        
        # Check trifecta bets
        bets.extend([bet for bet in race.betting_pool.trifecta_bets if bet.user_id == user_id])
        
        return bets
    
    def place_bet(self, user: User, race: Race, bet_type: BetType, amount: float, selection: List[int]) -> Bet:
        """Place a bet and update user balance"""
        bet = Bet(
            user_id=user.id,
            bet_type=bet_type,
            amount=amount,
            selection=selection
        )
        
        # Add bet to race
        success = race.add_bet(bet)
        if not success:
            raise ValidationError("Failed to add bet to race")
        
        # Update user balance
        user.balance -= amount
        
        return bet


class RaceService:
    """Handles race management and state transitions"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
    
    def serialize_race_state(self, race: Race) -> Dict[str, Any]:
        """Serialize race state for client transmission"""
        return {
            "id": race.id,
            "phase": race.phase.value,
            "horses": [self.serialize_horse(horse) for horse in race.horses],
            "time_remaining": self.calculate_time_remaining(race),
            "odds": self.calculate_all_odds(race)
        }
    
    def serialize_horse(self, horse) -> Dict[str, Any]:
        """Serialize horse data for client transmission"""
        return {
            "id": horse.id,
            "name": horse.name,
            "position": horse.position,
            "finished": horse.finished,
            "finish_position": horse.finish_position
        }
    
    def calculate_time_remaining(self, race: Race) -> float:
        """Calculate remaining time for current race phase"""
        current_time = time.time()
        
        if race.phase.value == 'betting':
            return max(0, race.betting_end_time - current_time)
        elif race.phase.value == 'results':
            return max(0, race.results_end_time - current_time)
        else:
            return 0
    
    def calculate_all_odds(self, race: Race) -> Dict[int, Dict[str, float]]:
        """Calculate odds for all horses and bet types"""
        odds = {}
        for horse in race.horses:
            odds[horse.id] = {
                "winner": race.calculate_odds(horse.id, BetType.WINNER),
                "place": race.calculate_odds(horse.id, BetType.PLACE),
                "trifecta": race.calculate_odds(horse.id, BetType.TRIFECTA)
            }
        return odds


class PayoutService:
    """Handles payout calculations and distribution"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
    
    def calculate_payouts(self, race: Race) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Any]]:
        """Calculate payouts for all bet types"""
        payouts = {"winner": {}, "place": {}, "trifecta": {}}
        trifecta_info = {}
        
        if len(race.finished_horses) >= 3:
            # Calculate winner payouts
            winner_horse = race.finished_horses[0]
            winner_odds = race.calculate_odds(winner_horse.id, BetType.WINNER)
            
            if winner_horse.id in race.betting_pool.winner_bets:
                for bet in race.betting_pool.winner_bets[winner_horse.id]:
                    payouts["winner"][bet.user_id] = bet.amount * winner_odds
            
            # Calculate place payouts (top 3 horses)
            place_horses = race.finished_horses[:3]
            for horse in place_horses:
                place_odds = race.calculate_odds(horse.id, BetType.PLACE)
                if horse.id in race.betting_pool.place_bets:
                    for bet in race.betting_pool.place_bets[horse.id]:
                        payouts["place"][bet.user_id] = bet.amount * place_odds
            
            # Calculate trifecta payouts
            trifecta_result = self.calculate_trifecta_payouts(race)
            payouts["trifecta"] = trifecta_result["payouts"]
            trifecta_info = trifecta_result["info"]
        
        return payouts, trifecta_info
    
    def calculate_trifecta_payouts(self, race: Race) -> Dict[str, Any]:
        """Calculate trifecta payouts for box trifecta"""
        winning_trifecta = {race.finished_horses[0].id, race.finished_horses[1].id, race.finished_horses[2].id}
        winning_bets = [bet for bet in race.betting_pool.trifecta_bets if set(bet.selection) == winning_trifecta]
        
        total_pool = sum(bet.amount for bet in race.betting_pool.trifecta_bets)
        house_edge = 0.15
        payout_pool = total_pool * (1 - house_edge)
        
        payouts = {}
        winners_count = len(winning_bets)
        payout_per_dollar = 0
        
        if winners_count > 0:
            payout_per_dollar = payout_pool / sum(bet.amount for bet in winning_bets)
            for bet in winning_bets:
                payouts[bet.user_id] = bet.amount * payout_per_dollar
        
        return {
            "payouts": payouts,
            "info": {
                "winning_combination": list(winning_trifecta),
                "total_pool": total_pool,
                "winners_count": winners_count,
                "payout_per_dollar": payout_per_dollar
            }
        }
    
    def apply_payouts(self, payouts: Dict[str, Dict[str, float]]) -> None:
        """Apply payouts to user balances"""
        for bet_type, user_payouts in payouts.items():
            for user_id, payout in user_payouts.items():
                user = self.game_state.users.get(user_id)
                if user:
                    user.balance += payout
                    user.total_winnings += payout


class LeaderboardService:
    """Handles leaderboard management and ranking"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
    
    def update_leaderboard(self, ai_users: List[User] = None) -> List[Dict[str, Any]]:
        """Update leaderboard and return top 10 users"""
        # Include both human and AI players
        all_users = list(self.game_state.users.values())
        if ai_users:
            all_users.extend(ai_users)
        
        # Only include connected human players and all AI players
        eligible_users = [
            user for user in all_users 
            if (user.connected or user.id.startswith('ai_'))
        ]
        
        # Sort by balance and assign ranks
        eligible_users.sort(key=lambda x: x.balance, reverse=True)
        for i, user in enumerate(eligible_users):
            user.rank = i + 1
        
        # Update game state leaderboard
        self.game_state.leaderboard = eligible_users[:10]
        
        # Return serialized leaderboard
        return [self.serialize_user(user) for user in self.game_state.leaderboard]
    
    def serialize_user(self, user: User) -> Dict[str, Any]:
        """Serialize user data for client transmission"""
        return {
            "id": user.id,
            "username": user.username,
            "balance": user.balance,
            "rank": user.rank,
            "total_winnings": user.total_winnings,
            "races_played": user.races_played,
            "connected": user.connected
        }


class MessageService:
    """Handles message creation and serialization"""
    
    @staticmethod
    def create_error_message(error: str) -> str:
        """Create error message for client"""
        return json.dumps({
            "type": "error",
            "message": error
        })
    
    @staticmethod
    def create_bet_placed_message(bet: Bet, new_balance: float) -> str:
        """Create bet placed confirmation message"""
        return json.dumps({
            "type": "bet_placed",
            "bet": {
                "type": bet.bet_type.value,
                "amount": bet.amount,
                "selection": bet.selection
            },
            "new_balance": new_balance
        })
    
    @staticmethod
    def create_race_state_message(race_data: Dict[str, Any]) -> str:
        """Create race state message"""
        return json.dumps({
            "type": "race_state",
            "race": race_data
        })
    
    @staticmethod
    def create_odds_update_message(odds: Dict[int, Dict[str, float]], time_remaining: float) -> str:
        """Create odds update message"""
        return json.dumps({
            "type": "odds_update",
            "odds": odds,
            "time_remaining": time_remaining
        })
    
    @staticmethod
    def create_leaderboard_message(leaders: List[Dict[str, Any]], current_user_rank: int = None) -> str:
        """Create leaderboard message"""
        return json.dumps({
            "type": "leaderboard",
            "leaders": leaders,
            "current_user_rank": current_user_rank
        })