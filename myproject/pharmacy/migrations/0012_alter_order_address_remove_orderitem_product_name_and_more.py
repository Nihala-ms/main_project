# Generated by Django 5.1.4 on 2025-03-25 05:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0011_address_order_orderitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='address',
            field=models.TextField(),
        ),
        migrations.RemoveField(
            model_name='orderitem',
            name='product_name',
        ),
        migrations.AddField(
            model_name='order',
            name='city',
            field=models.CharField(default='DefaultCity', max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='email',
            field=models.EmailField(default='Default@gmail.com', max_length=254),
        ),
        migrations.AddField(
            model_name='order',
            name='full_name',
            field=models.CharField(default='Defaultname', max_length=255),
        ),
        migrations.AddField(
            model_name='order',
            name='phone',
            field=models.CharField(default='987654323', max_length=15),
        ),
        migrations.AddField(
            model_name='order',
            name='state',
            field=models.CharField(default='Defaultstatte', max_length=100),
        ),
        migrations.AddField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Processing', 'Processing'), ('Shipped', 'Shipped'), ('Delivered', 'Delivered'), ('Cancelled', 'Cancelled')], default='Pending', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='zip_code',
            field=models.CharField(default='000000', max_length=10),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='product',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='pharmacy.medicine'),
        ),
        migrations.DeleteModel(
            name='Address',
        ),
    ]
