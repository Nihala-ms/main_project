# Generated by Django 5.1.4 on 2025-03-29 05:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0019_products_alter_cartitems_medicine_cartitems_product_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Product',
        ),
    ]
