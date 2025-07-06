from django import template
import re # Regular expression library
from django.utils.safestring import mark_safe # Marks output as HTML-safe
from GHLWebsiteApp.models import Player

register = template.Library() # Register the template library for use

@register.filter
def tag_players(content):
    """
    Replaces @username mentions with links to that player's profile.
    This was designed to use in announcements, since it will be a model only with text inputs.
    """
    def repl(match):
        username = match.group(1) # Get the username after "@"
        try:
            player = Player.objects.get(username=username) # Look up the Player with this username
            url = f"/player/{player.ea_player_num}/" # Build the profile URL
            return f'<a href="{url}">{username}</a>' # Replace with link
        except Player.DoesNotExist:
            return f'@{username}' # If not found, leave as plain text

    tagged = re.sub(r'@(\w+)', repl, content) # Find all @word patterns and run through repl()
    return mark_safe(tagged)
