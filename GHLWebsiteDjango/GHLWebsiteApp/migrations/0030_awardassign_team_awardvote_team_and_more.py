# Generated by Django 5.1.4 on 2025-04-17 21:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('GHLWebsiteApp', '0029_rename_award_num_awardvote_award_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='awardassign',
            name='team',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='GHLWebsiteApp.team', verbose_name='Team'),
        ),
        migrations.AddField(
            model_name='awardvote',
            name='team',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='GHLWebsiteApp.team', verbose_name='Team'),
        ),
        migrations.AlterField(
            model_name='awardassign',
            name='award_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='GHLWebsiteApp.awardtitle', verbose_name='Award'),
        ),
        migrations.AlterField(
            model_name='awardassign',
            name='players',
            field=models.ManyToManyField(blank=True, to='GHLWebsiteApp.player', verbose_name='Players'),
        ),
        migrations.AlterField(
            model_name='awardassign',
            name='season_num',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='GHLWebsiteApp.season', verbose_name='Season'),
        ),
        migrations.AlterField(
            model_name='awardvote',
            name='award_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='GHLWebsiteApp.awardtitle', verbose_name='Award'),
        ),
        migrations.AlterField(
            model_name='awardvote',
            name='ea_player_num',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='GHLWebsiteApp.player', verbose_name='Player'),
        ),
        migrations.AlterField(
            model_name='awardvote',
            name='season_num',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='GHLWebsiteApp.season', verbose_name='Season'),
        ),
        migrations.AlterField(
            model_name='awardvote',
            name='votes_num',
            field=models.SmallIntegerField(default=0, verbose_name='Votes'),
        ),
    ]
