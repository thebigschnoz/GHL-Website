from django.apps import AppConfig
import threading
import asyncio
from GHLWebsiteApp.discord_bot import bot, TOKEN


class GhlwebsiteappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'GHLWebsiteApp'

    def ready(self):
        # Start the Discord bot in a background thread
        def start_bot():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot.start(TOKEN))

        threading.Thread(target=start_bot, daemon=True).start()