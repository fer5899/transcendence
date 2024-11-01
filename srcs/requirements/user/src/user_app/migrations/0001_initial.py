# Generated by Django 5.1.2 on 2024-10-15 15:51

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('units', models.IntegerField()),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('DENIED', 'Denied')], default='PENDING', max_length=100)),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'usering': ['date'],
            },
        ),
    ]
