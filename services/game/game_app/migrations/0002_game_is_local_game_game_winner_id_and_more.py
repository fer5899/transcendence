# Generated by Django 5.1.5 on 2025-04-01 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='is_local_game',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='game',
            name='winner_id',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rockpaperscissorsgame',
            name='is_local_game',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='rockpaperscissorsgame',
            name='winner_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
