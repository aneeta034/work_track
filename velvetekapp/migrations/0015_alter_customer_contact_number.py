# Generated by Django 5.1.4 on 2025-02-14 09:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('velvetekapp', '0014_alter_customer_contact_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='contact_number',
            field=models.CharField(max_length=10, unique=True),
        ),
    ]
