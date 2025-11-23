from django import forms
from .models import AwardTitle, Player, User, Position, PlayerAvailability, TradeBlockPlayer, TeamNeed, Game, Signup, Position
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.models.functions import Lower
from captcha.fields import CaptchaField
from dal import autocomplete
from datetime import timedelta
from django.utils.timezone import make_aware
from zoneinfo import ZoneInfo
from collections import defaultdict

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
    def __init__(self, *args, player=None, **kwargs):
        super().__init__(*args, **kwargs)
        if player is None:
            return
        team = player.current_team
        
        # Get all game times (ignore nulls)
        game_times = Game.objects.filter(expected_time__isnull=False).filter(Q(h_team_num=team) | Q(a_team_num=team)).values_list("expected_time", flat=True)

        # Build a dict: {sunday_date: game_count}
        week_counts = defaultdict(int)

        for dt in game_times:
            # Ensure timezone-aware datetime
            if dt.tzinfo is None:
                dt = make_aware(dt)

            # Convert to EST
            local_dt = dt.astimezone(ZoneInfo("America/New_York"))
            game_date = local_dt.date()

            # Normalize to Sunday of that week
            sunday = game_date - timedelta(days=game_date.weekday() + 1) if game_date.weekday() != 6 else game_date
            week_counts[sunday] += 1

        # Add 2 weeks past the last actual game-week Sunday
        if week_counts:
            latest = max(week_counts)
            week_counts[latest + timedelta(weeks=1)] = 0
            week_counts[latest + timedelta(weeks=2)] = 0

        sunday_choices = sorted([
            (sunday, f"{sunday.strftime('%B %d, %Y')} ({count} game{'s' if count != 1 else ''})")
            for sunday, count in week_counts.items()
        ])

        self.fields['week_start'] = forms.ChoiceField(
            choices=sunday_choices,
            label="Week Starting (Sunday)",
            required=True
        )

class TradeBlockForm(forms.ModelForm):
    class Meta:
        model = TradeBlockPlayer
        fields = ['player', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes (e.g., looking for LD or picks)'}),
        }

    def __init__(self, *args, **kwargs):
        user_team = kwargs.pop('user_team', None)
        super().__init__(*args, **kwargs)

        # Limit player choices to players on the manager's team
        if user_team:
            self.fields['player'].queryset = Player.objects.filter(team=user_team)

class TeamNeedForm(forms.ModelForm):
    class Meta:
        model = TeamNeed
        fields = ['position', 'skill', 'note']
        widgets = {
            'note': forms.TextInput(attrs={'placeholder': 'e.g. Top 6 winger, shutdown RD...'}),
        }

class SignupForm(forms.ModelForm):
    primary_position = forms.ModelChoiceField(
        queryset=Position.objects.all().order_by('-ea_pos'),
        label="Primary Position",
    )
    secondary_positions = forms.ModelMultipleChoiceField(
        queryset=Position.objects.all().order_by('-ea_pos'),
        label="Secondary Positions",
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select all positions you are comfortable playing (including your primary).",
    )

    class Meta:
        model = Signup
        fields = [
            "primary_position",
            "secondary_positions",
            "days_per_week",
            "scheduling_issues",
            "invited_by_name",
            "committed_to_league",
            "other_league_obligations",
        ]
        widgets = {
            "days_per_week": forms.NumberInput(attrs={"min": 2, "max": 5}),
            "scheduling_issues": forms.Textarea(attrs={"rows": 3}),
            "other_league_obligations": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "days_per_week": "Nights per Week (2–5)",
            "scheduling_issues": "Known Scheduling Issues",
            "invited_by_name": "Who Invited You?",
            "committed_to_league": "Are You Committed to This League?",
            "other_league_obligations": "Other League Obligations",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use positionShort for display labels
        self.fields["primary_position"].label_from_instance = lambda obj: obj.positionShort
        self.fields["secondary_positions"].label_from_instance = lambda obj: obj.positionShort

    def clean(self):
        cleaned = super().clean()
        primary = cleaned.get("primary_position")
        secondaries = cleaned.get("secondary_positions")

        # enforce 2–5 constraint even if someone bypasses HTML
        days = cleaned.get("days_per_week")
        if days is not None and not (2 <= days <= 5):
            self.add_error("days_per_week", "Nights per week must be between 2 and 5.")

        if primary:
            if not secondaries:
                # auto-include primary as the only secondary
                cleaned["secondary_positions"] = [primary]
            elif primary not in secondaries:
                # enforce invariant: primary ∈ secondaries
                cleaned["secondary_positions"] = list(secondaries) + [primary]

        return cleaned

class ComparePlayersForm(forms.Form):
    player1 = forms.ModelChoiceField(
        queryset=Player.objects.all().exclude(banneduser__isnull=False).order_by(Lower("username")),
        required=False,
        label="Player 1",
    )
    player2 = forms.ModelChoiceField(
        queryset=Player.objects.all().exclude(banneduser__isnull=False).order_by(Lower("username")),
        required=False,
        label="Player 2",
    )
    player3 = forms.ModelChoiceField(
        queryset=Player.objects.all().exclude(banneduser__isnull=False).order_by(Lower("username")),
        required=False,
        label="Player 3",
    )
    player4 = forms.ModelChoiceField(
        queryset=Player.objects.all().exclude(banneduser__isnull=False).order_by(Lower("username")),
        required=False,
        label="Player 4",
    )
    player5 = forms.ModelChoiceField(
        queryset=Player.objects.all().exclude(banneduser__isnull=False).order_by(Lower("username")),
        required=False,
        label="Player 5",
    )
