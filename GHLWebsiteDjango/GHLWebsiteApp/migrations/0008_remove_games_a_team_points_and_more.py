# Generated by Django 5.1.4 on 2024-12-30 00:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('GHLWebsiteApp', '0007_games_a_team_points_games_h_team_points'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='games',
            name='a_team_points',
        ),
        migrations.RemoveField(
            model_name='games',
            name='h_team_points',
        ),
    ]
