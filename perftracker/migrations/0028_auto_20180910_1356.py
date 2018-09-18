# Generated by Django 2.1.1 on 2018-09-10 13:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('perftracker', '0027_remove_hwfarmnodelockmodel_color_rgb'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comparisonmodel',
            name='is_public',
            field=models.BooleanField(blank=True, default=False, help_text='Seen to everybody'),
        ),
        migrations.AlterField(
            model_name='hwfarmnodelockmodel',
            name='manual',
            field=models.BooleanField(default=True, help_text='True means it was manually locked'),
        ),
        migrations.AlterField(
            model_name='hwfarmnodelockmodel',
            name='planned_dur_hrs',
            field=models.IntegerField(default=24, help_text='Planned lock duration (hours)'),
        ),
        migrations.AlterField(
            model_name='testmodel',
            name='job',
            field=models.ForeignKey(help_text='Job instance', on_delete=django.db.models.deletion.CASCADE, related_name='tests', to='perftracker.JobModel'),
        ),
    ]
