# Generated by Django 5.1.6 on 2025-04-15 10:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopping', '0007_supplier_address_supplier_contact_email_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='supplier',
            old_name='address',
            new_name='company_name',
        ),
        migrations.RemoveField(
            model_name='supplier',
            name='contact_email',
        ),
        migrations.RemoveField(
            model_name='supplier',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='supplier',
            name='description',
        ),
        migrations.RemoveField(
            model_name='supplier',
            name='name',
        ),
    ]
