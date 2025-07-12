import asyncio
import json
import logging
import time
import uuid
import websockets
from typing import Dict, Set
from models import GameState, User, Bet, BetType, RacePhase
from race_engine import RaceEngine
from ai_players import AIPlayerManager

logger = logging.getLogger(__name__)


class WebSocketServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.game_state = GameState()
        self.race_engine = RaceEngine()
        self.connected_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id
        
        # Rate limiting - track connections per IP
        self.connection_attempts: Dict[str, List[float]] = {}  # IP -> [timestamps]
        self.max_connections_per_ip = 5  # Maximum connections per IP
        self.rate_limit_window = 60.0  # 1 minute window
        
        # Game timing
        self.betting_duration = 30.0  # 30 seconds
        self.results_duration = 10.0  # 10 seconds
        self.odds_update_interval = 0.25  # 250ms
        
        # AI player management
        self.ai_manager = AIPlayerManager(max_ai_players=1000)
        
        # Start first race
        self.start_new_race()
    
    def start_new_race(self):
        self.game_state.race_counter += 1
        self.game_state.current_race = self.race_engine.create_race(self.game_state.race_counter)
        
        # Manage AI players
        human_player_count = len([user for user in self.game_state.users.values() if user.connected])
        self.ai_manager.add_new_ai_players_if_needed(human_player_count)
        self.ai_manager.cleanup_broke_players()
        
        logger.info(f"Started race #{self.game_state.race_counter} with {human_player_count} humans and {len(self.ai_manager.ai_players)} AI players")
    
    def is_rate_limited(self, client_ip: str) -> bool:
        """Check if client IP is rate limited"""
        current_time = time.time()
        
        # Clean old entries
        if client_ip in self.connection_attempts:
            self.connection_attempts[client_ip] = [
                timestamp for timestamp in self.connection_attempts[client_ip]
                if current_time - timestamp < self.rate_limit_window
            ]
        
        # Count current connections from this IP
        current_connections = len([
            cid for cid, ws in self.connected_clients.items()
            if ws.remote_address and ws.remote_address[0] == client_ip
        ])
        
        # Check rate limit
        if client_ip not in self.connection_attempts:
            self.connection_attempts[client_ip] = []
        
        recent_attempts = len(self.connection_attempts[client_ip])
        
        return (current_connections >= self.max_connections_per_ip or 
                recent_attempts >= self.max_connections_per_ip * 2)  # Allow some burst
    
    async def register_client(self, websocket, path):
        connection_id = str(uuid.uuid4())
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
        
        # Rate limiting check
        if self.is_rate_limited(client_ip):
            logger.warning(f"Rate limited connection from {client_ip}")
            await websocket.close(code=1008, reason="Rate limited")
            return
        
        # Record connection attempt
        current_time = time.time()
        if client_ip not in self.connection_attempts:
            self.connection_attempts[client_ip] = []
        self.connection_attempts[client_ip].append(current_time)
        
        try:
            self.connected_clients[connection_id] = websocket
            logger.info(f"New client connected: {connection_id} from {client_ip}")
            
            await websocket.send(json.dumps({
                "type": "connection_established",
                "connection_id": connection_id
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(connection_id, data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON from {connection_id}: {e}")
                    await self.send_error(connection_id, "Invalid message format")
                except Exception as e:
                    logger.error(f"Error handling message from {connection_id}: {e}")
                    await self.send_error(connection_id, "Internal server error")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {connection_id} disconnected normally")
        except Exception as e:
            logger.error(f"Unexpected error with client {connection_id}: {e}")
        finally:
            await self.disconnect_client(connection_id)
            logger.info(f"Client {connection_id} cleanup completed")
    
    async def disconnect_client(self, connection_id: str):
        if connection_id in self.connected_clients:
            del self.connected_clients[connection_id]
        
        # Find and disconnect user
        user_id = None
        for uid, cid in self.user_connections.items():
            if cid == connection_id:
                user_id = uid
                break
        
        if user_id:
            user = self.game_state.get_user(user_id)
            if user:
                user.connected = False
            del self.user_connections[user_id]
            self.game_state.update_leaderboard(self.ai_manager.get_all_ai_users())
    
    async def handle_message(self, connection_id: str, message: dict):
        message_type = message.get("type")
        
        if message_type == "login":
            await self.handle_login(connection_id, message)
        elif message_type == "place_bet":
            await self.handle_place_bet(connection_id, message)
        elif message_type == "get_race_state":
            await self.send_race_state(connection_id)
        elif message_type == "get_leaderboard":
            await self.send_leaderboard(connection_id)
    
    async def handle_login(self, connection_id: str, message: dict):
        username = message.get("username", "").strip()
        if not username:
            await self.send_error(connection_id, "Username required")
            return
        
        # Check if user exists
        user_id = None
        for uid, user in self.game_state.users.items():
            if user.username == username:
                user_id = uid
                break
        
        # Create new user if doesn't exist
        if not user_id:
            user_id = str(uuid.uuid4())
            user = User(id=user_id, username=username)
            self.game_state.add_user(user)
        else:
            user = self.game_state.get_user(user_id)
            user.connected = True
        
        self.user_connections[user_id] = connection_id
        
        await self.send_to_client(connection_id, {
            "type": "login_success",
            "user": {
                "id": user.id,
                "username": user.username,
                "balance": user.balance,
                "total_winnings": user.total_winnings,
                "races_played": user.races_played
            }
        })
        
        await self.send_race_state(connection_id)
        self.game_state.update_leaderboard(self.ai_manager.get_all_ai_users())
    
    async def handle_place_bet(self, connection_id: str, message: dict):
        user_id = self.get_user_by_connection(connection_id)
        if not user_id:
            await self.send_error(connection_id, "Not logged in")
            return
        
        user = self.game_state.get_user(user_id)
        if not user:
            await self.send_error(connection_id, "User not found")
            return
        
        if not self.game_state.current_race or self.game_state.current_race.phase != RacePhase.BETTING:
            await self.send_error(connection_id, "Betting is closed")
            return
        
        # Comprehensive input validation
        try:
            # Validate bet_type
            bet_type_str = message.get("bet_type")
            if not bet_type_str or not isinstance(bet_type_str, str):
                await self.send_error(connection_id, "Invalid bet type")
                return
            
            try:
                bet_type = BetType(bet_type_str)
            except ValueError:
                await self.send_error(connection_id, "Invalid bet type")
                return
            
            # Validate amount
            amount_raw = message.get("amount", 1.0)
            if not isinstance(amount_raw, (int, float)):
                await self.send_error(connection_id, "Invalid bet amount")
                return
            
            amount = float(amount_raw)
            
            # Prevent negative, zero, or excessive amounts
            if amount <= 0:
                await self.send_error(connection_id, "Bet amount must be positive")
                return
            
            if amount > 1000.0:  # Prevent overflow attacks
                await self.send_error(connection_id, "Bet amount too large")
                return
            
            if amount != 1.0:  # Game only allows $1 bets
                await self.send_error(connection_id, "Bet amount must be $1.00")
                return
            
            # Validate selection
            selection_raw = message.get("selection", [])
            if not isinstance(selection_raw, list):
                await self.send_error(connection_id, "Invalid selection format")
                return
            
            # Convert and validate selection
            try:
                selection = [int(x) for x in selection_raw]
            except (ValueError, TypeError):
                await self.send_error(connection_id, "Invalid horse selection")
                return
            
            # Validate selection based on bet type
            if bet_type in [BetType.WINNER, BetType.PLACE]:
                if len(selection) != 1:
                    await self.send_error(connection_id, "Must select exactly one horse")
                    return
                
                horse_id = selection[0]
                if horse_id < 1 or horse_id > len(self.game_state.current_race.horses):
                    await self.send_error(connection_id, "Invalid horse selection")
                    return
                
                # Verify horse exists in current race
                if not any(h.id == horse_id for h in self.game_state.current_race.horses):
                    await self.send_error(connection_id, "Horse not found in current race")
                    return
                    
            elif bet_type == BetType.TRIFECTA:
                if len(selection) != 3:
                    await self.send_error(connection_id, "Must select exactly three horses")
                    return
                
                if len(set(selection)) != 3:
                    await self.send_error(connection_id, "Must select three different horses")
                    return
                
                for horse_id in selection:
                    if horse_id < 1 or horse_id > len(self.game_state.current_race.horses):
                        await self.send_error(connection_id, "Invalid horse selection")
                        return
                    
                    # Verify horse exists in current race
                    if not any(h.id == horse_id for h in self.game_state.current_race.horses):
                        await self.send_error(connection_id, "Horse not found in current race")
                        return
            
        except Exception as e:
            await self.send_error(connection_id, "Invalid bet data")
            return
        
        # Check user has sufficient balance (with small precision buffer)
        if user.balance < (amount - 0.01):
            await self.send_error(connection_id, "Insufficient balance")
            return
        
        # Create and place bet
        bet = Bet(user_id=user_id, bet_type=bet_type, amount=amount, selection=selection)
        if self.game_state.current_race.add_bet(bet):
            user.balance -= amount
            self.game_state.update_leaderboard(self.ai_manager.get_all_ai_users())
            
            await self.send_to_client(connection_id, {
                "type": "bet_placed",
                "bet": {
                    "type": bet_type.value,
                    "amount": amount,
                    "selection": selection
                },
                "new_balance": user.balance
            })
            
            # Broadcast updated leaderboard
            await self.broadcast({
                "type": "leaderboard",
                "leaders": [
                    {
                        "username": user.username,
                        "balance": user.balance,
                        "total_winnings": user.total_winnings,
                        "races_played": user.races_played
                    } for user in self.game_state.leaderboard
                ]
            })
    
    def get_user_by_connection(self, connection_id: str) -> str:
        for user_id, cid in self.user_connections.items():
            if cid == connection_id:
                return user_id
        return None
    
    async def send_to_client(self, connection_id: str, message: dict):
        if connection_id in self.connected_clients:
            try:
                await self.connected_clients[connection_id].send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                await self.disconnect_client(connection_id)
    
    async def send_to_client_raw(self, connection_id: str, serialized_message: str):
        """Send pre-serialized message to avoid repeated JSON encoding"""
        if connection_id in self.connected_clients:
            try:
                await self.connected_clients[connection_id].send(serialized_message)
            except (websockets.exceptions.ConnectionClosed, 
                    websockets.exceptions.ConnectionClosedError,
                    ConnectionResetError,
                    BrokenPipeError) as e:
                # Connection is dead, will be cleaned up by caller
                raise e
    
    async def remove_client(self, connection_id: str):
        """Remove a client connection without full disconnect cleanup"""
        if connection_id in self.connected_clients:
            try:
                await self.connected_clients[connection_id].close()
            except:
                pass  # Connection already closed
            
            del self.connected_clients[connection_id]
            
            if connection_id in self.user_connections:
                del self.user_connections[connection_id]
    
    async def broadcast(self, message: dict):
        if not self.connected_clients:
            return
        
        # Pre-serialize the message to avoid repeated JSON encoding
        try:
            serialized_message = json.dumps(message)
        except (TypeError, ValueError):
            print(f"Failed to serialize broadcast message: {message}")
            return
        
        # Create connection list snapshot to avoid issues with concurrent modifications
        client_ids = list(self.connected_clients.keys())
        
        # Batch send operations with limited concurrency to prevent overwhelming the system
        batch_size = min(100, len(client_ids))  # Process at most 100 connections at once
        
        for i in range(0, len(client_ids), batch_size):
            batch = client_ids[i:i + batch_size]
            
            # Send to batch with error handling
            send_tasks = []
            for cid in batch:
                if cid in self.connected_clients:  # Double-check connection still exists
                    send_tasks.append(self.send_to_client_raw(cid, serialized_message))
            
            if send_tasks:
                results = await asyncio.gather(*send_tasks, return_exceptions=True)
                
                # Clean up failed connections
                failed_connections = []
                for j, result in enumerate(results):
                    if isinstance(result, Exception):
                        if j < len(batch):
                            failed_connections.append(batch[j])
                
                # Remove failed connections
                for failed_cid in failed_connections:
                    await self.remove_client(failed_cid)
    
    async def send_error(self, connection_id: str, error: str):
        await self.send_to_client(connection_id, {"type": "error", "message": error})
    
    async def send_race_state(self, connection_id: str):
        race = self.game_state.current_race
        if not race:
            return
        
        # Calculate odds for all horses
        odds = {}
        for horse in race.horses:
            odds[horse.id] = {
                "winner": race.calculate_odds(horse.id, BetType.WINNER),
                "place": race.calculate_odds(horse.id, BetType.PLACE)
            }
        
        await self.send_to_client(connection_id, {
            "type": "race_state",
            "race": {
                "id": race.id,
                "phase": race.phase.value,
                "horses": [
                    {
                        "id": horse.id,
                        "name": horse.name,
                        "position": horse.position,
                        "finished": horse.finished,
                        "finish_position": horse.finish_position
                    } for horse in race.horses
                ],
                "odds": odds,
                "time_remaining": self.get_phase_time_remaining()
            }
        })
    
    async def send_leaderboard(self, connection_id: str):
        await self.send_to_client(connection_id, {
            "type": "leaderboard",
            "leaders": [
                {
                    "username": user.username,
                    "balance": user.balance,
                    "total_winnings": user.total_winnings,
                    "races_played": user.races_played
                } for user in self.game_state.leaderboard
            ]
        })
    
    def get_phase_time_remaining(self) -> float:
        if not self.game_state.current_race:
            return 0.0
        
        race = self.game_state.current_race
        current_time = time.time()
        
        if race.phase == RacePhase.BETTING:
            return max(0, self.betting_duration - (current_time - race.start_time))
        elif race.phase == RacePhase.RACING:
            # Racing phase has dynamic duration, so we can't calculate time remaining
            return 0.0
        elif race.phase == RacePhase.RESULTS:
            if race.racing_end_time > 0:
                return max(0, self.results_duration - (current_time - race.racing_end_time))
            return 0.0
        
        return 0.0
    
    async def race_update_callback(self, race):
        await self.broadcast({
            "type": "race_update",
            "horses": [
                {
                    "id": horse.id,
                    "position": horse.position,
                    "finished": horse.finished,
                    "finish_position": horse.finish_position
                } for horse in race.horses
            ]
        })
    
    async def run_game_loop(self):
        logger.info("Starting game loop")
        
        while True:
            try:
                race = self.game_state.current_race
                if not race:
                    self.start_new_race()
                    continue
                
                # Betting phase
                race.phase = RacePhase.BETTING
                race.start_time = time.time()
                
                # Schedule AI bets for this race
                self.ai_manager.schedule_bets_for_race(race, self.betting_duration)
                
                # Broadcast initial race state
                await self.broadcast({
                    "type": "race_state",
                    "race": {
                        "id": race.id,
                        "phase": race.phase.value,
                        "horses": [
                            {
                                "id": horse.id,
                                "name": horse.name,
                                "position": horse.position,
                                "finished": horse.finished,
                                "finish_position": horse.finish_position
                            } for horse in race.horses
                        ],
                        "odds": {horse.id: {
                            "winner": race.calculate_odds(horse.id, BetType.WINNER),
                            "place": race.calculate_odds(horse.id, BetType.PLACE)
                        } for horse in race.horses},
                        "time_remaining": self.get_phase_time_remaining()
                    }
                })
                
                # Broadcast odds updates during betting and process AI bets
                betting_end_time = time.time() + self.betting_duration
                while time.time() < betting_end_time:
                    # Process any due AI bets
                    await self.process_ai_bets(race)
                    
                    await self.broadcast_odds_update()
                    await asyncio.sleep(self.odds_update_interval)
                
                # Racing phase - race will end dynamically when third place finishes + 1 second
                race.phase = RacePhase.RACING
                race.betting_end_time = time.time()
                
                # Broadcast racing phase start
                await self.broadcast({
                    "type": "race_state",
                    "race": {
                        "id": race.id,
                        "phase": race.phase.value,
                        "horses": [
                            {
                                "id": horse.id,
                                "name": horse.name,
                                "position": horse.position,
                                "finished": horse.finished,
                                "finish_position": horse.finish_position
                            } for horse in race.horses
                        ],
                        "odds": {},
                        "time_remaining": self.get_phase_time_remaining()
                    }
                })
                
                await self.race_engine.simulate_race(race, self.race_update_callback)
                
                # Results phase
                race.phase = RacePhase.RESULTS
                race.racing_end_time = time.time()
                payouts = self.race_engine.calculate_payouts(race)
                await self.process_payouts(payouts)
                
                # Calculate odds for top 3 horses
                top_3_with_odds = []
                for i, horse in enumerate(race.finished_horses[:3]):
                    winner_odds = race.calculate_odds(horse.id, BetType.WINNER)
                    place_odds = race.calculate_odds(horse.id, BetType.PLACE)
                    top_3_with_odds.append({
                        "position": i + 1,
                        "horse_id": horse.id,
                        "horse_name": horse.name,
                        "winner_odds": winner_odds,
                        "place_odds": place_odds
                    })
                
                # Calculate trifecta payout info
                trifecta_info = {}
                if len(race.finished_horses) >= 3:
                    winning_trifecta = [race.finished_horses[0].id, race.finished_horses[1].id, race.finished_horses[2].id]
                    trifecta_pool = sum(bet.amount for bet in race.betting_pool.trifecta_bets)
                    winning_bets = [bet for bet in race.betting_pool.trifecta_bets if bet.selection == winning_trifecta]
                    trifecta_winners = len(winning_bets)
                    
                    trifecta_info = {
                        "winning_combination": winning_trifecta,
                        "total_pool": trifecta_pool,
                        "winners_count": trifecta_winners,
                        "payout_per_dollar": trifecta_pool / sum(bet.amount for bet in winning_bets) if winning_bets else 0
                    }
                
                # Get top 10 winners for this race
                race_winners = {}
                
                # Collect all users who won and their total winnings
                for bet_type, user_payouts in payouts.items():
                    for user_id, payout in user_payouts.items():
                        if payout > 0:
                            if user_id not in race_winners:
                                race_winners[user_id] = {
                                    "user_id": user_id,
                                    "total_winnings": 0,
                                    "bets": []
                                }
                            race_winners[user_id]["total_winnings"] += payout
            
                # Now get the bets for each winning user
                for user_id, winner_data in race_winners.items():
                    user = self.game_state.get_user(user_id)
                    if user:
                        winner_data["username"] = user.username
                    else:
                        # Check if it's an AI player
                        ai_player = self.ai_manager.ai_players.get(user_id)
                        if ai_player:
                            winner_data["username"] = ai_player.user.username
                    
                    # Check winner bets for all users (human and AI)
                    for horse_id, bets in race.betting_pool.winner_bets.items():
                        for bet in bets:
                            if bet.user_id == user_id:
                                winner_data["bets"].append({
                                    "type": "winner",
                                    "horse_id": horse_id,
                                    "horse_name": next(h.name for h in race.horses if h.id == horse_id),
                                    "amount": bet.amount
                                })
                    
                    # Check place bets
                    for horse_id, bets in race.betting_pool.place_bets.items():
                        for bet in bets:
                            if bet.user_id == user_id:
                                winner_data["bets"].append({
                                    "type": "place",
                                    "horse_id": horse_id,
                                    "horse_name": next(h.name for h in race.horses if h.id == horse_id),
                                    "amount": bet.amount
                                })
                    
                    # Check trifecta bets
                    for bet in race.betting_pool.trifecta_bets:
                        if bet.user_id == user_id:
                            horse_names = [next(h.name for h in race.horses if h.id == hid) for hid in bet.selection]
                            winner_data["bets"].append({
                                "type": "trifecta",
                                "selection": bet.selection,
                                "horse_names": horse_names,
                                "amount": bet.amount
                            })
                
                # Convert to list and sort by winnings, get top 10
                race_winners_list = list(race_winners.values())
                race_winners_list.sort(key=lambda x: x["total_winnings"], reverse=True)
                top_race_winners = race_winners_list[:10]
                
                # Broadcast results and updated race state
                await self.broadcast({
                    "type": "race_results",
                    "results": top_3_with_odds,
                    "trifecta_info": trifecta_info,
                    "top_winners": top_race_winners,
                    "payouts": payouts
                })
                
                # Broadcast results phase state
                await self.broadcast({
                    "type": "race_state",
                    "race": {
                        "id": race.id,
                        "phase": race.phase.value,
                        "horses": [
                            {
                                "id": horse.id,
                                "name": horse.name,
                                "position": horse.position,
                                "finished": horse.finished,
                                "finish_position": horse.finish_position
                            } for horse in race.horses
                        ],
                        "odds": {},
                        "time_remaining": self.get_phase_time_remaining()
                    }
                })
                
                # Wait for results phase duration
                results_end_time = time.time() + self.results_duration
                while time.time() < results_end_time:
                    # Update time remaining during results phase
                    await self.broadcast({
                        "type": "phase_update",
                        "phase": race.phase.value,
                        "time_remaining": max(0, results_end_time - time.time())
                    })
                    await asyncio.sleep(1.0)  # Update every second
                
                # Start new race
                self.start_new_race()
            
            except Exception as e:
                logger.error(f"Error in game loop: {e}")
                # Try to recover by starting a new race
                try:
                    self.start_new_race()
                except Exception as recovery_error:
                    logger.critical(f"Failed to recover from game loop error: {recovery_error}")
                    # Wait before trying again to prevent tight error loops
                    await asyncio.sleep(5.0)
    
    async def broadcast_odds_update(self):
        race = self.game_state.current_race
        if not race:
            return
        
        # Cache odds calculation to avoid repeated computation
        odds = {}
        try:
            for horse in race.horses:
                odds[horse.id] = {
                    "winner": race.calculate_odds(horse.id, BetType.WINNER),
                    "place": race.calculate_odds(horse.id, BetType.PLACE)
                }
        except Exception as e:
            print(f"Error calculating odds: {e}")
            return
        
        message = {
            "type": "odds_update",
            "odds": odds,
            "time_remaining": self.get_phase_time_remaining()
        }
        
        await self.broadcast(message)
    
    async def process_ai_bets(self, race):
        """Process AI bets that are due to be placed"""
        due_bets = self.ai_manager.get_due_bets()
        
        for bet_time, ai_player_id, bet_info in due_bets:
            success = self.ai_manager.place_ai_bet(race, ai_player_id, bet_info)
            if success:
                # Update leaderboard after AI bet (balance decreased)
                self.game_state.update_leaderboard(self.ai_manager.get_all_ai_users())
    
    async def process_payouts(self, payouts: dict):
        # Process payouts for human players
        for bet_type, user_payouts in payouts.items():
            for user_id, payout in user_payouts.items():
                user = self.game_state.get_user(user_id)
                if user:
                    user.balance += payout
                    user.total_winnings += payout
                    user.races_played += 1
                else:
                    # Check if it's an AI player
                    ai_player = self.ai_manager.ai_players.get(user_id)
                    if ai_player:
                        ai_player.user.balance += payout
                        ai_player.user.total_winnings += payout
                        ai_player.user.races_played += 1
        
        self.game_state.update_leaderboard(self.ai_manager.get_all_ai_users())
        
        # Broadcast updated leaderboard
        await self.broadcast({
            "type": "leaderboard",
            "leaders": [
                {
                    "username": user.username,
                    "balance": user.balance,
                    "total_winnings": user.total_winnings,
                    "races_played": user.races_played
                } for user in self.game_state.leaderboard
            ]
        })
    
    async def start_server(self):
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        try:
            # Start game loop
            asyncio.create_task(self.run_game_loop())
            
            # Start WebSocket server
            await websockets.serve(self.register_client, self.host, self.port)
            logger.info("Server started successfully!")
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise


if __name__ == "__main__":
    server = WebSocketServer()
    asyncio.run(server.start_server())
    asyncio.get_event_loop().run_forever()