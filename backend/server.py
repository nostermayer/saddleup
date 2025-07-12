#!/usr/bin/env python3
import asyncio
import logging
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import *
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