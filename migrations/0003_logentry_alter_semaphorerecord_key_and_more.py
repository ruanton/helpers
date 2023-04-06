# Generated by Django 4.1.7 on 2023-04-06 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helpers', '0002_taskhandle_taskhandle_uniq_task_handle_task_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='LogEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Logger name')),
                ('level', models.PositiveSmallIntegerField(choices=[(0, 'NotSet'), (20, 'Info'), (30, 'Warning'), (10, 'Debug'), (40, 'Error'), (50, 'Fatal')], default=40)),
                ('msg', models.TextField()),
                ('trace', models.TextField(blank=True)),
                ('task_id', models.CharField(blank=True, editable=False, max_length=32, verbose_name='Task ID')),
                ('username', models.CharField(blank=True, editable=False, max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='db record created at', verbose_name='Created at')),
            ],
            options={
                'verbose_name': 'Logging',
                'verbose_name_plural': 'Logging',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AlterField(
            model_name='semaphorerecord',
            name='key',
            field=models.CharField(editable=False, help_text='semaphore unique name', max_length=512, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='semaphorerecord',
            name='locked',
            field=models.DateTimeField(blank=True, help_text='semaphore locked at', null=True),
        ),
        migrations.AlterField(
            model_name='semaphorerecord',
            name='modified',
            field=models.DateTimeField(auto_now=True, help_text='database record last modified at'),
        ),
        migrations.AlterField(
            model_name='semaphorerecord',
            name='pinged',
            field=models.DateTimeField(blank=True, help_text='semaphore last pinged at', null=True),
        ),
        migrations.AlterField(
            model_name='semaphorerecord',
            name='timeout',
            field=models.FloatField(help_text='interval in seconds after which the semaphore is considered open'),
        ),
        migrations.AlterField(
            model_name='taskhandle',
            name='cancel_requested',
            field=models.BooleanField(default=False, help_text='task cancellation requested', verbose_name='Cancel'),
        ),
        migrations.AlterField(
            model_name='taskhandle',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, help_text='db record created at', verbose_name='Created at'),
        ),
        migrations.AlterField(
            model_name='taskhandle',
            name='ormq_id',
            field=models.IntegerField(blank=True, editable=False, help_text='Django-Q ORM message broker record ID', null=True, verbose_name='OrmQ ID'),
        ),
        migrations.AlterField(
            model_name='taskhandle',
            name='task_id',
            field=models.CharField(editable=False, max_length=32, verbose_name='Task ID'),
        ),
        migrations.AlterField(
            model_name='taskhandle',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, help_text='db record updated at', verbose_name='Updated at'),
        ),
        migrations.AddIndex(
            model_name='logentry',
            index=models.Index(fields=['level', '-created_at'], name='idx_log_entry_level'),
        ),
        migrations.AddIndex(
            model_name='logentry',
            index=models.Index(fields=['task_id', '-created_at'], name='idx_log_entry_task_id'),
        ),
    ]