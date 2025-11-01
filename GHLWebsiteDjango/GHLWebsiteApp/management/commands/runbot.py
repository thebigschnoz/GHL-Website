import asyncio
from django.core.management.base import BaseCommand
from GHLWebsiteApp.discord_bot import bot, TOKEN


class Command(BaseCommand):
    help = "Runs the Discord bot independently from the web server"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Starting Discord bot..."))
        try:
            asyncio.run(bot.start(TOKEN))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("🛑 Bot shutdown requested by user."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Bot crashed: {e}"))