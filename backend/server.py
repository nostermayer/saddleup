#!/usr/bin/env python3
import asyncio
import logging
import sys
import os

# Add parent directory to path to import config
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

try:
    from config.settings import *
except ImportError:
    # Fallback to local config if import fails
    WEBSOCKET_HOST = 'localhost'
    WEBSOCKET_PORT = 8765
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    MAX_CONCURRENT_USERS = 1000

from websocket_server import WebSocketServer

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)

logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting SaddleUp.io Horse Racing Game Server")
    logger.info(f"Host: {WEBSOCKET_HOST}, Port: {WEBSOCKET_PORT}")
    logger.info(f"Max concurrent users: {MAX_CONCURRENT_USERS}")
    
    server = WebSocketServer(host=WEBSOCKET_HOST, port=WEBSOCKET_PORT)
    
    try:
        await server.start_server()
        logger.info("Server started successfully!")
        
        # Keep the server running
        await asyncio.Future()  # Run forever
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())