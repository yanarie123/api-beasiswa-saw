# Generated by Django 5.1.4 on 2025-01-04 19:36

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('selection', '0007_alter_applicant_decent_house_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='applicant', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='average_score',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='decent_house',
            field=models.IntegerField(blank=True, choices=[(1, 'Sangat Layak'), (2, 'Layak'), (3, 'Cukup Layak'), (4, 'Kurang Layak'), (5, 'Tidak Layak')], null=True),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='dependents',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='parent_income',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
