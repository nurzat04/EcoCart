# Generated by Django 5.1.6 on 2025-04-10 15:23

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shopping', '0003_product_category'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='supplier',
            name='contact_info',
        ),
        migrations.RemoveField(
            model_name='supplier',
            name='name',
        ),
        migrations.AddField(
            model_name='productsupplier',
            name='stock_status',
            field=models.CharField(choices=[('in_stock', 'In Stock'), ('out_of_stock', 'Out of Stock')], default=1, max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='shoppingitem',
            name='expiration_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='shoppingitem',
            name='reminder_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='supplier',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
