# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial')
    ]

    operations = [

        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.CharField(max_length=64, serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=64)),
                ('enabled', models.IntegerField()),
                ('extra', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'domain',
                'managed': False,
            },
            bases=(models.Model,),
        ),

        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.CharField(max_length=64, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('extra', models.TextField(blank=True)),
                ('description', models.TextField(blank=True)),
                ('enabled', models.IntegerField(null=True, blank=True)),
            ],
            options={
                'db_table': 'project',
                'managed': False,
            },
            bases=(models.Model,),
        ),

        migrations.CreateModel(
            name='Area',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=30)),
                ('description', models.TextField(max_length=255)),
                ('created_at', models.DateField(auto_now=True)),
            ],
            options={
                'db_table': 'vault_area',
            },
            bases=(models.Model,),
        )
    ]
