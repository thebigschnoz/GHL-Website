# Generated by Django 5.1.4 on 2025-01-03 22:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('GHLWebsiteApp', '0016_player_primarypos_player_secondarypos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='player',
            name='secondarypos',
            field=models.ManyToManyField(blank=True, related_name='secondary', to='GHLWebsiteApp.position'),
        ),
    ]
