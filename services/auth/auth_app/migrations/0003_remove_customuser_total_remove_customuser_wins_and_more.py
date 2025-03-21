# Generated by Django 4.1.13 on 2025-03-21 18:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0002_customuser_profile_picture_alter_customuser_total_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='total',
        ),
        migrations.RemoveField(
            model_name='customuser',
            name='wins',
        ),
        migrations.AlterField(
            model_name='customuser',
            name='profile_picture',
            field=models.CharField(blank=True, default='/media/default.png', max_length=255, null=True),
        ),
    ]
