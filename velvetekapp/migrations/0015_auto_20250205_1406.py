# Generated by Django 3.1.12 on 2025-02-05 08:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('velvetekapp', '0014_auto_20250205_1359'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='apply',
            name='created',
        ),
        migrations.AddField(
            model_name='apply',
            name='created_at',
            field=models.DateTimeField(null=True),
        ),
    ]
