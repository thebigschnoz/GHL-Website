# Generated by Django 5.1.4 on 2025-07-07 20:15

import django.db.models.functions.text
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('GHLWebsiteApp', '0045_player_jersey_num_alter_announcement_author'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'ordering': [django.db.models.functions.text.Lower('username')]},
        ),
    ]
