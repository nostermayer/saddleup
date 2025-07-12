import random
import asyncio
import time
import uuid
import logging
from typing import List, Dict
from models import User, Bet, BetType

logger = logging.getLogger(__name__)


class AIPlayerGenerator:
    def __init__(self):
        self.first_names = [
            "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Blake", "Cameron",
            "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason", "Isabella", "William",
            "James", "Benjamin", "Lucas", "Henry", "Alexander", "Michael", "Daniel", "Jacob", "Logan", "Jackson",
            "Sebastian", "Jack", "Aiden", "Owen", "Samuel", "Matthew", "Joseph", "Levi", "Mateo", "David",
            "John", "Wyatt", "Carter", "Luke", "Grayson", "Isaac", "Gabriel", "Julian", "Maverick", "Anthony",
            "Charlotte", "Amelia", "Harper", "Evelyn", "Abigail", "Emily", "Elizabeth", "Mila", "Ella", "Sofia",
            "Camila", "Aria", "Scarlett", "Victoria", "Madison", "Luna", "Grace", "Chloe", "Penelope", "Layla",
            "Riley", "Zoey", "Nora", "Lily", "Eleanor", "Hannah", "Lillian", "Addison", "Aubrey", "Ellie",
            "Stella", "Natalie", "Zoe", "Leah", "Hazel", "Violet", "Aurora", "Savannah", "Audrey", "Brooklyn",
            "Bella", "Claire", "Skylar", "Lucy", "Paisley", "Everly", "Anna", "Caroline", "Nova", "Genesis"
        ]
        
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
            "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
            "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
            "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
            "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts",
            "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes",
            "Stewart", "Morris", "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper",
            "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
            "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
            "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez"
        ]
        
        self.used_names = set()
    
    def generate_name(self) -> str:
        """Generate a unique realistic name for an AI player"""
        max_attempts = 100
        for _ in range(max_attempts):
            first = random.choice(self.first_names)
            last = random.choice(self.last_names)
            full_name = f"{first} {last}"
            
            if full_name not in self.used_names:
                self.used_names.add(full_name)
                return full_name
        
        # Fallback with numbers if we run out of unique combinations
        first = random.choice(self.first_names)
        last = random.choice(self.last_names)
        suffix = random.randint(10, 99)
        full_name = f"{first} {last}{suffix}"
        self.used_names.add(full_name)
        return full_name


class AIPlayer:
    def __init__(self, user: User):
        self.user = user
        self.betting_style = random.choice(['conservative', 'aggressive', 'balanced', 'longshot'])
        self.preferred_bet_types = self._generate_bet_preferences()
        self.bet_frequency = random.uniform(0.3, 0.8)  # 30-80% chance to bet each race
        self.average_bet_amount = random.uniform(0.8, 1.2)  # Multiplier for base bet amounts
        
    def _generate_bet_preferences(self) -> Dict[BetType, float]:
        """Generate betting preferences based on player style"""
        if self.betting_style == 'conservative':
            return {
                BetType.WINNER: 0.4,
                BetType.PLACE: 0.55,
                BetType.TRIFECTA: 0.05
            }
        elif self.betting_style == 'aggressive':
            return {
                BetType.WINNER: 0.6,
                BetType.PLACE: 0.25,
                BetType.TRIFECTA: 0.15
            }
        elif self.betting_style == 'longshot':
            return {
                BetType.WINNER: 0.3,
                BetType.PLACE: 0.2,
                BetType.TRIFECTA: 0.5
            }
        else:  # balanced
            return {
                BetType.WINNER: 0.45,
                BetType.PLACE: 0.4,
                BetType.TRIFECTA: 0.15
            }
    
    def should_bet_this_race(self) -> bool:
        """Determine if this AI player should bet on the current race"""
        return random.random() < self.bet_frequency
    
    def choose_bet_type(self) -> BetType:
        """Choose a bet type based on player preferences"""
        rand = random.random()
        cumulative = 0
        for bet_type, probability in self.preferred_bet_types.items():
            cumulative += probability
            if rand <= cumulative:
                return bet_type
        return BetType.WINNER  # fallback
    
    def choose_horse_selection(self, race, bet_type: BetType) -> List[int]:
        """Choose horse(s) based on betting strategy and odds"""
        horses = race.horses
        
        if bet_type == BetType.TRIFECTA:
            # Choose 3 different horses for trifecta
            selected = random.sample([h.id for h in horses], 3)
            return selected
        else:
            # For winner/place, choose based on betting style and odds
            horse_weights = []
            
            for horse in horses:
                # Get horse strength and initial odds
                strength = race.get_horse_strength(horse.id)
                initial_odds = race.get_initial_odds(horse.id, bet_type)
                
                # Adjust weight based on betting style
                if self.betting_style == 'conservative':
                    # Prefer favorites (low odds, high strength)
                    weight = strength / max(initial_odds, 1.0)
                elif self.betting_style == 'longshot':
                    # Prefer longshots (high odds, lower strength)
                    weight = initial_odds / max(strength, 0.1)
                elif self.betting_style == 'aggressive':
                    # Prefer moderate favorites with good value
                    weight = strength * (2.0 if 2.0 <= initial_odds <= 5.0 else 0.5)
                else:  # balanced
                    # Mix of strength and odds consideration
                    weight = (strength + (1.0 / max(initial_odds, 1.0))) / 2
                
                horse_weights.append((horse.id, weight))
            
            # Weighted random selection
            total_weight = sum(weight for _, weight in horse_weights)
            if total_weight == 0:
                return [random.choice([h.id for h in horses])]
            
            rand = random.uniform(0, total_weight)
            cumulative = 0
            for horse_id, weight in horse_weights:
                cumulative += weight
                if rand <= cumulative:
                    return [horse_id]
            
            return [horse_weights[0][0]]  # fallback
    
    def calculate_bet_amount(self, base_amount: float) -> float:
        """Calculate bet amount based on player's betting style"""
        amount = base_amount * self.average_bet_amount
        
        # Add some randomness
        variation = random.uniform(0.8, 1.2)
        final_amount = amount * variation
        
        # Ensure player has enough balance
        return min(final_amount, self.user.balance)


class AIPlayerManager:
    def __init__(self, max_ai_players: int = 1000):
        self.max_ai_players = max_ai_players
        self.name_generator = AIPlayerGenerator()
        self.ai_players: Dict[str, AIPlayer] = {}
        self.betting_schedule: List[tuple] = []  # (time, ai_player_id, bet_info)
        
    def get_needed_ai_count(self, human_player_count: int) -> int:
        """Calculate how many AI players are needed"""
        return max(0, self.max_ai_players - human_player_count)
    
    def create_ai_players(self, needed_count: int) -> List[AIPlayer]:
        """Create the specified number of AI players"""
        new_ai_players = []
        
        for _ in range(needed_count):
            user_id = f"ai_{uuid.uuid4().hex[:8]}"
            username = self.name_generator.generate_name()
            
            # AI players start with same balance as humans - exactly $10.00
            starting_balance = 10.0
            
            user = User(
                id=user_id,
                username=username,
                balance=starting_balance,
                connected=False  # AI players don't have websocket connections
            )
            
            ai_player = AIPlayer(user)
            self.ai_players[user_id] = ai_player
            new_ai_players.append(ai_player)
            
        return new_ai_players
    
    def schedule_bets_for_race(self, race, betting_duration: float):
        """Schedule AI bets throughout the betting period"""
        self.betting_schedule.clear()
        
        current_time = time.time()
        betting_end_time = current_time + betting_duration
        
        for ai_player in self.ai_players.values():
            if not ai_player.should_bet_this_race():
                continue
            
            # Determine number of bets (1-3 bets per active AI player)
            num_bets = random.choices([1, 2, 3], weights=[0.7, 0.25, 0.05])[0]
            
            for _ in range(num_bets):
                # Random time during betting period
                bet_time = random.uniform(current_time + 1, betting_end_time - 1)
                
                bet_type = ai_player.choose_bet_type()
                selection = ai_player.choose_horse_selection(race, bet_type)
                
                base_amount = 1.0  # Base bet amount
                amount = ai_player.calculate_bet_amount(base_amount)
                
                if amount >= 0.1 and ai_player.user.balance >= amount:  # Minimum bet check
                    bet_info = {
                        'bet_type': bet_type,
                        'amount': amount,
                        'selection': selection
                    }
                    
                    self.betting_schedule.append((bet_time, ai_player.user.id, bet_info))
        
        # Sort by time
        self.betting_schedule.sort(key=lambda x: x[0])
    
    def get_due_bets(self) -> List[tuple]:
        """Get bets that should be placed now"""
        current_time = time.time()
        due_bets = []
        
        while self.betting_schedule and self.betting_schedule[0][0] <= current_time:
            due_bet = self.betting_schedule.pop(0)
            due_bets.append(due_bet)
        
        return due_bets
    
    def place_ai_bet(self, race, ai_player_id: str, bet_info: dict) -> bool:
        """Place a bet for an AI player"""
        ai_player = self.ai_players.get(ai_player_id)
        if not ai_player:
            return False
        
        # Check if player can afford the bet
        if ai_player.user.balance < bet_info['amount']:
            return False
        
        # Create and place the bet
        bet = Bet(
            user_id=ai_player_id,
            bet_type=bet_info['bet_type'],
            amount=bet_info['amount'],
            selection=bet_info['selection']
        )
        
        if race.add_bet(bet):
            ai_player.user.balance -= bet_info['amount']
            return True
        
        return False
    
    def get_all_ai_users(self) -> List[User]:
        """Get all AI player users for leaderboard"""
        return [ai_player.user for ai_player in self.ai_players.values()]
    
    def cleanup_broke_players(self):
        """Remove AI players who have run out of money"""
        # Create a new dict without broke players to avoid modification during iteration
        active_players = {}
        broke_count = 0
        
        for ai_id, ai_player in self.ai_players.items():
            if ai_player.user.balance >= 0.1:
                active_players[ai_id] = ai_player
            else:
                broke_count += 1
        
        self.ai_players = active_players
        
        if broke_count > 0:
            logger.info(f"Removed {broke_count} broke AI players")
    
    def add_new_ai_players_if_needed(self, current_human_count: int):
        """Add new AI players to maintain the target count"""
        needed_count = self.get_needed_ai_count(current_human_count)
        current_ai_count = len(self.ai_players)
        
        if needed_count > current_ai_count:
            additional_needed = needed_count - current_ai_count
            self.create_ai_players(additional_needed)