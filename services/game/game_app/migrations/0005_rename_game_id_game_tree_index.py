# Generated by Django 5.1.5 on 2025-02-10 09:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('game_app', '0004_alter_game_tournament_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='game',
            old_name='game_id',
            new_name='tree_index',
        ),
    ]
