# Generated by Django 2.2.5 on 2019-10-14 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('perftracker', '0049_auto_20191014_1046'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainDataModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.TextField()),
                ('fails', models.TextField(blank=True, null=True)),
                ('less_better', models.TextField(default='_')),
                ('function_type', models.IntegerField(choices=[(0, 'Not specified'), (1, 'Constant'), (2, 'Linear'), (3, 'Logarithm'), (4, 'Square or exp')], default=0)),
                ('outliers', models.IntegerField(choices=[(0, '0'), (1, '1'), (2, 'Many')], default=0)),
                ('oscillation', models.IntegerField(choices=[(0, 'False'), (1, 'True')], default=0)),
                ('anomaly', models.IntegerField(choices=[(0, 'False'), (1, 'True')], default=0)),
            ],
        ),
    ]
