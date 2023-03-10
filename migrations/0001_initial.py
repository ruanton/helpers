# Generated by Django 4.1.3 on 2022-12-05 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SemaphoreRecord',
            fields=[
                ('key', models.CharField(max_length=512, primary_key=True, serialize=False, verbose_name='Semaphore unique name')),
                ('timeout', models.FloatField(verbose_name='Interval in seconds after which the semaphore is considered open')),
                ('pinged', models.DateTimeField(blank=True, null=True, verbose_name='Last pinged at')),
                ('locked', models.DateTimeField(blank=True, null=True, verbose_name='Semaphore locked at')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Record modified at')),
            ],
        ),
    ]
