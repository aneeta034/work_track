# Generated by Django 3.1.12 on 2025-02-05 08:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('velvetekapp', '0013_apply_created_at'),
    ]

    operations = [
        migrations.RenameField(
            model_name='apply',
            old_name='created_at',
            new_name='created',
        ),
    ]
