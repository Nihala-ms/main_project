# Generated by Django 5.1.4 on 2025-04-03 04:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0023_medicine_discounted_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orders',
            name='order_number',
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
    ]
