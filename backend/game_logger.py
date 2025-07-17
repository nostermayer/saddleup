import logging
import requests
import datetime
import aiohttp
import os

logger = logging.getLogger(__name__)


class GameLogger:
    def __init__(self):
        # Retrieve webhook URL from environment variable
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.is_production = os.getenv("ENVIRONMENT") == "production"

        if not self.webhook_url:
            logger.info(
                "🚨 Warning: DISCORD_WEBHOOK_URL environment variable not set. Discord notifications will be disabled."
            )
        else:
            logger.info(f"Webhook URL loaded successfully - {self.webhook_url}")

        if not self.webhook_url:
            logger.info("🔧 Development mode: Discord notifications disabled")
        elif not self.is_production:
            logger.info(
                "🔧 Development mode: Discord notifications will be sent to dev webhook."
            )
        else:
            logger.info("🚀 Production mode: Discord notifications enabled")

    def log_generic_event(self, message):
        """Log a generic event to the logger."""
        logger.info("Generic Event: %s", message)

    def log_user_join(self, username, user_count, ip_address=None):
        """Log when a user connects to the game"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        data = {
            "embeds": [
                {
                    "title": "🟢 User Connected",
                    "color": 0x00FF00,
                    "fields": [
                        {"name": "Username", "value": username, "inline": True},
                        {
                            "name": "Total Online",
                            "value": str(user_count),
                            "inline": True,
                        },
                        {"name": "Time", "value": timestamp, "inline": True},
                    ],
                    "timestamp": datetime.datetime.now().isoformat(),
                }
            ]
        }

        if ip_address:
            data["embeds"][0]["fields"].append(
                {"name": "IP", "value": ip_address, "inline": True}
            )

        self._send(data)

    def log_user_leave(self, username, user_count, duration=None):
        """Log when a user disconnects from the game"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        fields = [
            {"name": "Username", "value": username, "inline": True},
            {"name": "Total Online", "value": str(user_count), "inline": True},
            {"name": "Time", "value": timestamp, "inline": True},
        ]

        if duration:
            fields.append(
                {"name": "Session Duration", "value": duration, "inline": True}
            )

        data = {
            "embeds": [
                {
                    "title": "🔴 User Disconnected",
                    "color": 0xFF0000,
                    "fields": fields,
                    "timestamp": datetime.datetime.now().isoformat(),
                }
            ]
        }

        self._send(data)

    def log_game_event(self, event_type, message, color=0x0099FF):
        """Log general game events"""
        data = {
            "embeds": [
                {
                    "title": f"🎮 {event_type}",
                    "description": message,
                    "color": color,
                    "timestamp": datetime.datetime.now().isoformat(),
                }
            ]
        }

        self._send(data)

    def log_error(self, error_message, username=None):
        """Log errors and exceptions"""
        fields = [{"name": "Error", "value": error_message, "inline": False}]

        if username:
            fields.append({"name": "User", "value": username, "inline": True})

        data = {
            "embeds": [
                {
                    "title": "⚠️ Error Occurred",
                    "color": 0xFF6600,
                    "fields": fields,
                    "timestamp": datetime.datetime.now().isoformat(),
                }
            ]
        }

        self._send(data)

    async def log_server_status(self, status, player_count, uptime=None):
        """Log server status updates"""
        color = 0x00FF00 if status == "online" else 0xFF0000

        fields = [
            {"name": "Status", "value": status.title(), "inline": True},
            {"name": "Players Online", "value": str(player_count), "inline": True},
        ]

        if uptime:
            fields.append({"name": "Uptime", "value": uptime, "inline": True})

        data = {
            "embeds": [
                {
                    "title": f"🖥️ Server {status.title()}",
                    "color": color,
                    "fields": fields,
                    "timestamp": datetime.datetime.now().isoformat(),
                }
            ]
        }

        await self.async_send(data)

    def _send(self, data):
        """Send data to Discord webhook"""
        # Skip sending if not in production
        if not self.webhook_url:
            logger.info(
                f"[DEV] Would send Discord notification: {data['embeds'][0]['title']}"
            )
            return

        try:
            response = requests.post(self.webhook_url, json=data)
            response.raise_for_status()
            logger.info(
                f"Discord notification sent: {data['embeds'][0]['title']}"
            )
        except requests.exceptions.RequestException as e:
            logger.info(f"Discord logging failed: {e}")

    # Async version for better performance with websockets
    async def async_send(self, data):
        """Async version of send for use with asyncio"""
        # Skip sending if not in production
        if not self.webhook_url:
            logger.info(
                f"[DEV] Would send Discord notification: {data['embeds'][0]['title']}"
            )
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=data) as response:
                    response.raise_for_status()
        except Exception as e:
            logger.info(f"Discord logging failed: {e}")

    async def async_log_user_join(self, username, user_count, ip_address=None):
        """Async version of log_user_join"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        data = {
            "embeds": [
                {
                    "title": "🟢 User Connected",
                    "color": 0x00FF00,
                    "fields": [
                        {"name": "Username", "value": username, "inline": True},
                        {
                            "name": "Total Online",
                            "value": str(user_count),
                            "inline": True,
                        },
                        {"name": "Time", "value": timestamp, "inline": True},
                    ],
                    "timestamp": datetime.datetime.now().isoformat(),
                }
            ]
        }

        if ip_address:
            data["embeds"][0]["fields"].append(
                {"name": "IP", "value": ip_address, "inline": True}
            )

        await self.async_send(data)


# Usage Examples:

# # Initialize logger
# game_logger = GameLogger()

# # Example usage in your websocket server:

# # When a user connects:
# game_logger.log_user_join("player123", 5, "192.168.1.100")

# # When a user disconnects:
# game_logger.log_user_leave("player123", 4, "5 minutes")

# # For game events:
# game_logger.log_game_event(
#     "High Score", "Player 'speedrun_king' achieved new high score: 15,420!"
# )

# # For errors:
# game_logger.log_error("WebSocket connection failed", "player123")

# # For server status:
# game_logger.log_server_status("online", 0, "2 hours 30 minutes")
