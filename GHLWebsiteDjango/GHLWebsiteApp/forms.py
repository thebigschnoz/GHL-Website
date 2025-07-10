from django import forms
from .models import AwardTitle, Player, User, Position, PlayerAvailability
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from captcha.fields import CaptchaField
from dal import autocomplete

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
        widget=autocomplete.ModelSelect2(
            url='player-autocomplete',
            attrs={
                'data-placeholder': 'Start typing a player username...',
                'data-minimum-input-length': 1,
            }
        ),
        help_text="Optional: link this user to an existing EA player profile.",
        label="Player Link",
    )

    # Include captcha field for spam protection
    captcha = CaptchaField()

    # Override the __init__ method to customize the form
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "password1", "password2", "player_link", "captcha")

class UserProfileForm(forms.ModelForm):
    player_link = forms.ModelChoiceField(
        queryset=Player.objects.all(),
        widget=autocomplete.ModelSelect2(url='player-autocomplete'),
        required=False,
        label="Linked Player",
    )

    jersey_num = forms.IntegerField(required=False, label="Jersey Number")
    primarypos = forms.ModelChoiceField(
        queryset=Position.objects.all().order_by('-ea_pos'),
        required=False,
        label="Primary Position"
    )
    secondarypos = forms.ModelMultipleChoiceField(
        queryset=Position.objects.all().order_by('-ea_pos'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Secondary Positions"
    )

    class Meta:
        model = User
        fields = ['player_link', 'jersey_num', 'primarypos', 'secondarypos']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Pre-fill player fields if user already linked
        if user and user.player_link:
            player = user.player_link
            self.fields['jersey_num'].initial = player.jersey_num
            self.fields['primarypos'].initial = player.primarypos
            self.fields['secondarypos'].initial = player.secondarypos.all()

class PlayerAvailabilityForm(forms.ModelForm):
    class Meta:
        model = PlayerAvailability
        fields = [
            'week_start',
            'sunday',
            'monday',
            'tuesday',
            'wednesday',
            'thursday',
            'comment',
        ]
        widgets = {
            'week_start': forms.SelectDateWidget,
        }