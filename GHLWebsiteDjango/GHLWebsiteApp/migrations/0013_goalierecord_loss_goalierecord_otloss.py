# Generated by Django 5.1.4 on 2025-01-02 23:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('GHLWebsiteApp', '0012_rename_awards_awardassign_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='goalierecord',
            name='loss',
            field=models.BooleanField(default='0'),
        ),
        migrations.AddField(
            model_name='goalierecord',
            name='otloss',
            field=models.BooleanField(default='0'),
        ),
    ]
