# Generated by Django 2.0.3 on 2018-09-30 22:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('perftracker', '0036_auto_20180930_2344'),
    ]

    operations = [
        migrations.AlterField(
            model_name='artifactmetamodel',
            name='deleted',
            field=models.BooleanField(db_index=True, default=False, help_text='Artifact is deleted'),
        ),
    ]
