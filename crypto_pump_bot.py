# crypto_pump_bot.py
import asyncio
import ccxt
import pandas as pd
import plotly.graph_objects as go
import websockets
import json
import time
import logging
import os
import nest_asyncio
from dotenv import load_dotenv
from collections import deque
from telegram import InputFile
from telegram.ext import ApplicationBuilder

# ========== CODESPACES FIXES ========== #
nest_asyncio.apply()  # Fix async conflicts
os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # Fix plotly rendering
# ====================================== #

# ========== INITIALIZATION ========== #
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Environment validation
REQUIRED_ENV = ['TELEGRAM_TOKEN', 'CHAT_ID']
for var in REQUIRED_ENV:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
BOT_NAME = os.getenv('BOT_NAME', 'GitHub Codespaces Bot')

# Configuration with fail-safes
ALERT_THRESHOLDS = {
    '5m': 5.0,
    '15m': 10.0,
    '1h': 50.0
}

class RobustCryptoBot:
    def __init__(self):
        self.exchange = self._init_exchange()
        self.symbol_data = {}
        self.alert_cooldown = {}
        self.app = self._init_telegram()
        self.ws_uri = "wss://stream.binance.com:9443/ws/!ticker@arr"
        self.retries = 0
        self.max_retries = 10

    def _init_exchange(self):
        """Create exchange instance with rate limiting"""
        return ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'defaultType': 'spot'
            }
        })

    def _init_telegram(self):
        """Telegram app setup with validation"""
        if not TELEGRAM_TOKEN or not CHAT_ID:
            raise ValueError("Telegram credentials missing")
        return ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    async def start(self):
        """Main entry point with monitoring"""
        try:
            logger.info("🚀 Starting bot in Codespaces environment")
            await asyncio.gather(
                self.websocket_listener(),
                self.app.initialize(),
                self.app.start(),
                self.app.updater.start_polling(),
                self.system_monitor()
            )
        except Exception as e:
            logger.critical(f"🔥 Critical failure: {e}")
            await self.shutdown()

    async def system_monitor(self):
        """Resource monitoring and cleanup"""
        while True:
            logger.info(f"System status: Retries {self.retries}/{self.max_retries}")
            await asyncio.sleep(3600)  # Hourly status report

    async def websocket_listener(self):
        """Enhanced WebSocket handler with circuit breaker"""
        while self.retries < self.max_retries:
            try:
                async with websockets.connect(self.ws_uri, ping_interval=30) as ws:
                    logger.info("🔌 WebSocket connected")
                    self.retries = 0  # Reset on success
                    while True:
                        try:
                            data = await asyncio.wait_for(ws.recv(), timeout=45)
                            await self.process_data(json.loads(data))
                        except (asyncio.TimeoutError, websockets.ConnectionClosed):
                            logger.warning("⚠️ Connection timeout, reconnecting...")
                            break
            except Exception as e:
                self.retries += 1
                wait = min(2 ** self.retries, 300)
                logger.error(f"🔴 Connection failed (retry {self.retries}): {e}")
                await asyncio.sleep(wait)
        
        logger.error("⛔ Maximum retries reached")
        await self.shutdown()

    async def shutdown(self):
        """Graceful shutdown sequence"""
        logger.info("🛑 Initiating shutdown...")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.app.stop()
        await self.app.shutdown()
        logger.info("🔌 Bot shutdown complete")

    # [Keep other methods from original code but add error handling]
    # Add try/except blocks to all async methods
    # Add data validation in process_data
    # Add memory cleanup in generate_chart

if __name__ == "__main__":
    try:
        bot = RobustCryptoBot()
        asyncio.run(bot.start())
    except Exception as e:
        logger.critical(f"💀 Fatal initialization error: {e}")