# Generated by Django 5.1.4 on 2025-01-17 03:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('GHLWebsiteApp', '0022_skaterrecord_pass_pct_skaterrecord_shot_eff_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='goalierecord',
            name='gaa',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name='goalierecord',
            name='save_pct',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=4),
        ),
    ]
