# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.auth.models import Group


# Keystone
class Domain(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(unique=True, max_length=64)
    enabled = models.IntegerField()
    extra = models.TextField(blank=True)

    class Meta:
        managed = False
        db_table = 'domain'


# Keystone
class Project(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=64)
    extra = models.TextField(blank=True)
    description = models.TextField(blank=True)
    enabled = models.IntegerField(blank=True, null=True)
    domain = models.ForeignKey(Domain)

    class Meta:
        managed = False
        db_table = 'project'

    def __unicode__(self):
        return " %s" % (self.name)


# Vault
class Area(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    description = models.TextField(max_length=255)
    created_at = models.DateField(auto_now=True)

    class Meta:
        db_table = 'vault_area'

    def __unicode__(self):
        return " %s" % (self.name)


class GroupProjects(models.Model):
    group = models.ForeignKey(Group)
    project = models.ForeignKey(Project)

    class Meta:
        db_table = 'vault_group_projects'
        unique_together = (('project', 'group'),)
        verbose_name_plural = 'Times (Groups) & Projetos'

    def __unicode__(self):
        return " Time (Group) %s - Projeto %s" % (self.group, self.project)


class AreaProjects(models.Model):
    area = models.ForeignKey(Area)
    project = models.ForeignKey(Project, unique=True)

    class Meta:
        db_table = 'vault_area_projects'
        verbose_name_plural = 'Areas & Projetos'

    def __unicode__(self):
        return " Area %s - Projeto %s" % (self.area, self.project)
