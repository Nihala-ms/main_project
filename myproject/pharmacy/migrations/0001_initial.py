# Generated by Django 5.1.4 on 2025-02-11 08:46

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Medicine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('dosage', models.CharField(max_length=50)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('stock', models.PositiveIntegerField()),
                ('image', models.ImageField(upload_to='medicine_images/')),
                ('description', models.TextField(blank=True, null=True)),
                ('manufacturer', models.CharField(max_length=100)),
                ('expiry_date', models.DateField()),
                ('category', models.CharField(max_length=100)),
                ('prescription_required', models.BooleanField(default=False)),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='medicines', to='pharmacy.brand')),
            ],
        ),
    ]
