import uuid
import itertools
import json
import uuid

from datetime import timedelta
from datetime import datetime

from django.db import models
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.core.exceptions import SuspiciousOperation

from rest_framework import serializers

from perftracker.models.job import JobModel
from perftracker.models.project import ProjectModel
from perftracker.models.env_node import EnvNodeModel, EnvNodeUploadSerializer, EnvNodeSimpleSerializer, EnvNodeNestedSerializer


class ptCmpChartType:
    AUTO = 0
    NOCHART = 1
    XYLINE = 2
    XYLINE_AND_TREND = 3
    BAR = 4
    BAR_AND_TREND = 5


CMP_CHARTS = (
    (ptCmpChartType.AUTO, 'Auto'),
    (ptCmpChartType.NOCHART, 'No charts'),
    (ptCmpChartType.XYLINE, 'XY-line'),
    (ptCmpChartType.XYLINE_AND_TREND, 'XY-line + trend'),
    (ptCmpChartType.BAR, 'Bar charts'),
    (ptCmpChartType.BAR_AND_TREND, 'Bar + trend'))


class ptCmpTableType:
    AUTO = 0
    HIDE_ALL = 1
    SHOW_ALL = 2


CMP_TABLES = (
    (ptCmpTableType.AUTO, 'Auto'),
    (ptCmpTableType.HIDE_ALL, 'Hide all tables'),
    (ptCmpTableType.SHOW_ALL, 'Show all tables'))


class ptCmpTestsType:
    AUTO = 0
    TESTS_WO_WARNINGS = 1
    TESTS_WO_ERRORS = 2
    ALL_TESTS = 3


CMP_TESTS = (
    (ptCmpTestsType.AUTO, 'Auto'),
    (ptCmpTestsType.TESTS_WO_WARNINGS, 'Tests w/o warnings'),
    (ptCmpTestsType.TESTS_WO_ERRORS, 'Tests w/o errors'),
    (ptCmpTestsType.ALL_TESTS, 'All tests'))


class ptCmpValueType:
    AUTO = 0
    AVERAGE = 1
    MIN = 2
    MAX = 3


CMP_VALUES = (
    (ptCmpValueType.AUTO, 'Auto'),
    (ptCmpValueType.AVERAGE, 'Average values'),
    (ptCmpValueType.MIN, 'Min values'),
    (ptCmpValueType.MAX, 'Max values'))


class ComparisonModel(models.Model):
    title       = models.CharField(max_length=512, help_text="Comparison title")

    author      = models.CharField(max_length=128, help_text="Comparison author: user@mycompany.localdomain", null=True, blank=True)
    project     = models.ForeignKey(ProjectModel, help_text="Comparison project", on_delete=models.CASCADE)
    updated     = models.DateTimeField(help_text="Comparison updated datetime", default=timezone.now)

    is_public   = models.BooleanField(help_text="Seen to everybody", default=False, blank=True)

    charts_type = models.IntegerField(help_text="Charts type", default=0, choices=CMP_CHARTS)
    tables_type = models.IntegerField(help_text="Tables type", default=0, choices=CMP_TABLES)
    tests_type  = models.IntegerField(help_text="Tests type", default=0, choices=CMP_TESTS)
    values_type = models.IntegerField(help_text="Values type", default=0, choices=CMP_VALUES)

    jobs        = models.ManyToManyField(JobModel, help_text="Jobs")

    @staticmethod
    def ptValidateJson(json_data):
        if 'title' not in json_data:
            raise SuspiciousOperation("Comparison title is not specified: it must be 'title': '...'")
        if 'jobs' not in json_data:
            raise SuspiciousOperation("Comparison jobs are not specified: it must be 'jobs': [1, 3, ...] ")
        if type(json_data['jobs']) is not list:
            raise SuspiciousOperation("Comparison jobs must be a list: 'jobs': [1, 3, ...] ")

    @staticmethod
    def _ptGetType(types, json_data, key):
        if key not in json_data:
            return 0

        type2id = {}
        for id, type in types:
            type2id[type] = id
        id = type2id.get(json_data[key], None)
        if id is None:
            raise SuspiciousOperation("Unknown type: %s, acceptable types are: %s" % (json_data[key], ",".join(type2id.keys())))
        return id

    def ptUpdate(self, json_data):
        self.title = json_data['title']
        self.charts_type = self._ptGetType(CMP_CHARTS, json_data, 'charts_type')
        self.tables_type = self._ptGetType(CMP_TABLES, json_data, 'tables_type')
        self.tests_type = self._ptGetType(CMP_TESTS, json_data, 'tests_type')
        self.values_type = self._ptGetType(CMP_VALUES, json_data, 'values_type')

        jobs = []

        for jid in json_data['jobs']:
            try:
                job = JobModel.objects.get(id=int(jid))
            except JobModel.DoesNotExist:
                raise SuspiciousOperation("Job with id = '%d' doesn't exist" % jid)
            jobs.append(job)

        self.save()
        self.jobs.clear()
        for job in jobs:
            self.jobs.add(job)
        self.save()

    def __str__(self):
        return "#%d, %s" % (self.id, self.title)

    class Meta:
        verbose_name = "Comparison"
        verbose_name_plural = "Comparisons"


class ComparisonBaseSerializer(serializers.ModelSerializer):
    env_node = serializers.SerializerMethodField()

    def get_env_node(self, job):
        # this function is required to apply 'parent=None' filter because env_node children will be
        # populated by the EnvNodeNestedSerializer
        return None


class ComparisonSimpleSerializer(ComparisonBaseSerializer):
    class Meta:
        model = ComparisonModel
        fields = ('id', 'title', 'suite_name', 'suite_ver', 'env_node', 'updated',
                  'tests_total', 'tests_completed', 'tests_failed', 'tests_errors', 'tests_warnings', 'project', 'jobs')


class ComparisoNestedSerializer(ComparisonBaseSerializer):
    class Meta:
        model = ComparisonModel
        fields = ('id', 'title', 'suite_name', 'suite_ver', 'product_name', 'product_ver', 'env_node', 'updated',
                  'tests_total', 'tests_completed', 'tests_failed', 'tests_errors', 'tests_warnings', 'project', 'jobs')
