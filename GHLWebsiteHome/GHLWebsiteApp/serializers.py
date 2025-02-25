from rest_framework import serializers
from .models import Standing

class StandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Standing
        fields = ['team', 'gp', 'wins', 'losses', 'otlosses', 'points']