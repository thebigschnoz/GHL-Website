from django import forms
from .models import AwardTitle, Player
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from captcha.fields import CaptchaField

class UploadFileForm(forms.Form):
    file = forms.FileField()

class AwardForm(forms.Form):
    award = forms.ModelChoiceField(queryset=AwardTitle.objects.all(), empty_label="Select an award...", label="Award")

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    # Add player_link to the user creation form
    player_link = forms.ModelChoiceField(
        queryset=Player.objects.all(),
        required=False,
        help_text="Optional: link this user to a player profile.",
    )

    # Include captcha field for spam protection
    captcha = CaptchaField()

    # Override the __init__ method to customize the form
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "password1", "password2", "player_link", "captcha")