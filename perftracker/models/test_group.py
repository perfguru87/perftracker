import numpy
import uuid
import itertools
import json
from functools import reduce

from datetime import timedelta
from datetime import datetime

from django.db import models
from django.utils.dateparse import parse_datetime
from django.apps import apps
from django.db.models import Q
from django.core.exceptions import SuspiciousOperation

from rest_framework import serializers

from perftracker.models.job import JobModel
from perftracker.helpers import ptDurationField, ptRoundedFloatField, ptRoundedFloatMKField, pt_is_valid_uuid

TEST_GROUP_TAG_LENGTH = 128


class TestGroupModel(models.Model):

    tag         = models.CharField(max_length=TEST_GROUP_TAG_LENGTH, help_text="Test group tag: pagetests", db_index=True, default='')
    title       = models.CharField(max_length=128, help_text="Test group name: Web page tests", db_index=True)
    glyphicon   = models.CharField(max_length=128, help_text="Bootstrap 3 glyphicon to use: glyphicon glyphicon-hdd")
    icon        = models.URLField(max_length=256, help_text="URL of the icon to be used")

    @staticmethod
    def ptGetByTag(tag):
        try:
            return TestGroupModel.objects.get(tag=tag)
        except TestGroupModel.DoesNotExist:
            g = TestGroupModel(title=tag, tag=tag)
            g.save()
            return g

    def __str__(self):
        return self.tag

    class Meta:
        verbose_name = "Test group"
        verbose_name_plural = "Test groups"


class TestGroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = TestGroupModel
        fields = [f.name for f in TestGroupModel._meta.get_fields(include_hidden=True)]
