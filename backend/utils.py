"""
Utility functions and decorators for SaddleUp horse racing game.
"""

import asyncio
import functools
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
import websockets

logger = logging.getLogger(__name__)


def error_handler(func: Callable) -> Callable:
    """Decorator to handle errors gracefully in async functions"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            # Return None or appropriate default value
            return None
    return wrapper


def sync_error_handler(func: Callable) -> Callable:
    """Decorator to handle errors gracefully in sync functions"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return None
    return wrapper


def rate_limit(max_calls: int, window_seconds: float):
    """Rate limiting decorator"""
    def decorator(func: Callable) -> Callable:
        calls = []
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            # Remove old calls outside the window
            calls[:] = [call_time for call_time in calls if now - call_time < window_seconds]
            
            if len(calls) >= max_calls:
                raise Exception(f"Rate limit exceeded: {max_calls} calls per {window_seconds} seconds")
            
            calls.append(now)
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'errors': 0
        }
    
    def add_connection(self, connection_id: str, websocket: websockets.WebSocketServerProtocol) -> None:
        """Add a new connection"""
        self.connections[connection_id] = websocket
        self.connection_stats['total_connections'] += 1
        self.connection_stats['active_connections'] = len(self.connections)
        logger.info(f"Added connection {connection_id}. Active connections: {len(self.connections)}")
    
    def remove_connection(self, connection_id: str) -> None:
        """Remove a connection"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.connection_stats['active_connections'] = len(self.connections)
            logger.info(f"Removed connection {connection_id}. Active connections: {len(self.connections)}")
        
        # Remove user mapping if exists
        user_id = None
        for uid, cid in self.user_connections.items():
            if cid == connection_id:
                user_id = uid
                break
        
        if user_id:
            del self.user_connections[user_id]
    
    def associate_user(self, user_id: str, connection_id: str) -> None:
        """Associate a user with a connection"""
        self.user_connections[user_id] = connection_id
        logger.debug(f"Associated user {user_id} with connection {connection_id}")
    
    async def send_to_connection(self, connection_id: str, message: str) -> bool:
        """Send message to specific connection"""
        if connection_id not in self.connections:
            return False
        
        websocket = self.connections[connection_id]
        try:
            await websocket.send(message)
            self.connection_stats['messages_sent'] += 1
            return True
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Connection {connection_id} closed, removing")
            self.remove_connection(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to connection {connection_id}: {e}")
            self.connection_stats['errors'] += 1
            return False
    
    async def send_to_user(self, user_id: str, message: str) -> bool:
        """Send message to specific user"""
        connection_id = self.user_connections.get(user_id)
        if not connection_id:
            return False
        
        return await self.send_to_connection(connection_id, message)
    
    async def broadcast(self, message: str, exclude_connections: Optional[List[str]] = None) -> int:
        """Broadcast message to all connections"""
        if exclude_connections is None:
            exclude_connections = []
        
        sent_count = 0
        failed_connections = []
        
        # Create list of connections to avoid modification during iteration
        connections_to_send = [
            (conn_id, ws) for conn_id, ws in self.connections.items()
            if conn_id not in exclude_connections
        ]
        
        # Send to all connections concurrently
        tasks = []
        for conn_id, websocket in connections_to_send:
            task = asyncio.create_task(self._send_with_cleanup(conn_id, websocket, message))
            tasks.append(task)
        
        # Wait for all sends to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if result is True:
                sent_count += 1
            elif isinstance(result, Exception):
                conn_id = connections_to_send[i][0]
                failed_connections.append(conn_id)
                logger.warning(f"Failed to send to {conn_id}: {result}")
        
        # Clean up failed connections
        for conn_id in failed_connections:
            self.remove_connection(conn_id)
        
        logger.debug(f"Broadcast sent to {sent_count}/{len(connections_to_send)} connections")
        return sent_count
    
    async def _send_with_cleanup(self, connection_id: str, websocket: websockets.WebSocketServerProtocol, message: str) -> bool:
        """Send message with automatic cleanup on failure"""
        try:
            await websocket.send(message)
            self.connection_stats['messages_sent'] += 1
            return True
        except websockets.exceptions.ConnectionClosed:
            return False
        except Exception as e:
            self.connection_stats['errors'] += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            **self.connection_stats,
            'active_connections': len(self.connections),
            'user_connections': len(self.user_connections)
        }


class MessageQueue:
    """Simple message queue for batching operations"""
    
    def __init__(self, max_size: int = 100, flush_interval: float = 1.0):
        self.max_size = max_size
        self.flush_interval = flush_interval
        self.queue: List[Dict[str, Any]] = []
        self.last_flush = time.time()
    
    def add(self, message: Dict[str, Any]) -> None:
        """Add message to queue"""
        self.queue.append(message)
        
        # Auto-flush if queue is full or flush interval exceeded
        if len(self.queue) >= self.max_size or time.time() - self.last_flush > self.flush_interval:
            self.flush()
    
    def flush(self) -> List[Dict[str, Any]]:
        """Flush all messages from queue"""
        messages = self.queue.copy()
        self.queue.clear()
        self.last_flush = time.time()
        return messages
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return len(self.queue) == 0


class CircuitBreaker:
    """Circuit breaker pattern for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise e
    
    def record_failure(self) -> None:
        """Record a failure"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def reset(self) -> None:
        """Reset circuit breaker"""
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None


def sanitize_user_input(input_str: str, max_length: int = 100) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not isinstance(input_str, str):
        return ""
    
    # Remove potentially dangerous characters
    sanitized = "".join(char for char in input_str if char.isalnum() or char in " _-.")
    
    # Limit length
    return sanitized[:max_length].strip()


def format_currency(amount: float) -> str:
    """Format currency amount consistently"""
    return f"${amount:.2f}"


def calculate_percentage(part: float, whole: float) -> float:
    """Calculate percentage safely"""
    if whole == 0:
        return 0.0
    return round((part / whole) * 100, 2)


def validate_json_message(message: str) -> Optional[Dict[str, Any]]:
    """Validate and parse JSON message"""
    try:
        data = json.loads(message)
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, TypeError):
        return None


def create_safe_task(coro, name: str = None) -> asyncio.Task:
    """Create asyncio task with error handling"""
    async def safe_wrapper():
        try:
            return await coro
        except Exception as e:
            logger.error(f"Error in task {name or 'unknown'}: {e}", exc_info=True)
    
    return asyncio.create_task(safe_wrapper())


# Performance monitoring utilities
class PerformanceMonitor:
    """Monitor performance metrics"""
    
    def __init__(self):
        self.metrics = {}
    
    def start_timer(self, name: str) -> None:
        """Start timing an operation"""
        self.metrics[name] = {"start": time.time()}
    
    def end_timer(self, name: str) -> float:
        """End timing an operation and return duration"""
        if name not in self.metrics:
            return 0.0
        
        duration = time.time() - self.metrics[name]["start"]
        self.metrics[name]["duration"] = duration
        return duration
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics"""
        return self.metrics.copy()


# Global performance monitor instance
performance_monitor = PerformanceMonitor()