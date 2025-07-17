import random
import asyncio
import time
from typing import List
from models import Horse, Race, RacePhase, BetType


class RaceEngine:
    def __init__(self):
        self.horse_names = [
            "Thunder Bolt", "Lightning Strike", "Storm Chaser", "Wind Runner", "Fire Starter",
            "Ice Breaker", "Star Gazer", "Moon Walker", "Sun Dancer", "Rain Maker",
            "Snow Flake", "Thunder Cloud", "Lightning Bug", "Storm Front", "Wind Rider",
            "Fire Ball", "Ice Storm", "Star Light", "Moon Beam", "Sun Shine"
        ]
    
    def create_race(self, race_id: int) -> Race:
        horses = []
        for i in range(20):
            horse = Horse(
                id=i + 1,
                name=self.horse_names[i],
                speed=random.uniform(0.8, 1.2),
                stamina=random.uniform(0.8, 1.2),
                consistency=random.uniform(0.8, 1.2)
            )
            horses.append(horse)
        
        return Race(id=race_id, horses=horses)
    
    async def simulate_race(self, race: Race, update_callback=None):
        race.phase = RacePhase.RACING
        max_race_duration = 60.0  # Maximum race duration (safety limit)
        update_interval = 0.1  # Update every 100ms for smooth animation
        race_start_time = time.time()
        third_place_finish_time = None
        
        while True:
            current_time = time.time()
            elapsed_time = current_time - race_start_time
            
            # Safety check - end race if it takes too long
            if elapsed_time > max_race_duration:
                break
            
            for horse in race.horses:
                if not horse.finished:
                    # Calculate horse movement with randomization
                    base_speed = horse.speed * horse.stamina * horse.consistency
                    random_factor = random.uniform(0.8, 1.2)
                    # Base movement speed adjusted for more realistic race times
                    position_increment = base_speed * random_factor * update_interval * 2.5
                    
                    horse.position += position_increment
                    
                    # Check if horse finished
                    if horse.position >= race.race_distance and not horse.finished:
                        horse.finished = True
                        horse.finish_position = len(race.finished_horses) + 1
                        race.finished_horses.append(horse)
                        
                        # Record when third place finishes
                        if len(race.finished_horses) == 3:
                            third_place_finish_time = current_time
            
            # Check if race should end (1 second after third place)
            if third_place_finish_time and (current_time - third_place_finish_time) >= 1.0:
                break
            
            # Send update to connected clients
            if update_callback:
                await update_callback(race)
            
            await asyncio.sleep(update_interval)
        
        # Ensure all horses finish (assign positions to remaining horses)
        for horse in race.horses:
            if not horse.finished:
                horse.finished = True
                horse.finish_position = len(race.finished_horses) + 1
                race.finished_horses.append(horse)
        
        race.phase = RacePhase.RESULTS
        return race.finished_horses
    
    def calculate_payouts(self, race: Race) -> dict:
        if len(race.finished_horses) < 3:
            return {}
        
        winner = race.finished_horses[0]
        place_horses = race.finished_horses[:3]
        
        payouts = {
            'winner': {},
            'place': {},
            'trifecta': {}
        }
        
        # Winner payouts
        winner_pool = race.betting_pool.get_total_pool(BetType.WINNER)
        winner_horse_pool = race.betting_pool.get_horse_pool(winner.id, BetType.WINNER)
        
        if winner_horse_pool > 0:
            # Apply 15% house edge
            house_edge = 0.15
            payout_pool = winner_pool * (1 - house_edge)
            winner_odds = max(1.01, payout_pool / winner_horse_pool)
            
            for bet in race.betting_pool.winner_bets.get(winner.id, []):
                if bet.user_id not in payouts['winner']:
                    payouts['winner'][bet.user_id] = 0
                payouts['winner'][bet.user_id] += round(bet.amount * winner_odds, 2)
        
        # Place payouts (top 3)
        place_pool = race.betting_pool.get_total_pool(BetType.PLACE)
        if place_pool > 0:
            # Apply 15% house edge
            house_edge = 0.15
            payout_pool = place_pool * (1 - house_edge)
            
            for horse in place_horses:
                place_horse_pool = race.betting_pool.get_horse_pool(horse.id, BetType.PLACE)
                if place_horse_pool > 0:
                    # Divide payout pool among the 3 place positions
                    place_odds = max(1.01, (payout_pool / 3) / place_horse_pool)
                    for bet in race.betting_pool.place_bets.get(horse.id, []):
                        if bet.user_id not in payouts['place']:
                            payouts['place'][bet.user_id] = 0
                        payouts['place'][bet.user_id] += round(bet.amount * place_odds, 2)
        
        # Trifecta payouts (box trifecta - any order of top 3)
        if len(race.finished_horses) >= 3:
            winning_trifecta = {race.finished_horses[0].id, race.finished_horses[1].id, race.finished_horses[2].id}
            trifecta_pool = race.betting_pool.get_total_pool(BetType.TRIFECTA)
            winning_bets = [bet for bet in race.betting_pool.trifecta_bets if set(bet.selection) == winning_trifecta]
            
            if winning_bets and trifecta_pool > 0:
                # Apply 15% house edge
                house_edge = 0.15
                payout_pool = trifecta_pool * (1 - house_edge)
                
                total_winning_amount = sum(bet.amount for bet in winning_bets)
                for bet in winning_bets:
                    payout_ratio = bet.amount / total_winning_amount
                    if bet.user_id not in payouts['trifecta']:
                        payouts['trifecta'][bet.user_id] = 0
                    payouts['trifecta'][bet.user_id] += round(payout_pool * payout_ratio, 2)
        
        return payouts