import uuid
import itertools
import json
import re

from datetime import timedelta
from datetime import datetime

from django.db import models
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.core.exceptions import SuspiciousOperation

from rest_framework import serializers

from perftracker.models.project import ProjectModel
from perftracker.models.env_node import EnvNodeModel, EnvNodeUploadSerializer, EnvNodeSimpleSerializer, EnvNodeNestedSerializer
from perftracker.helpers import ptDurationField, ptJson


class JobModel(models.Model):
    title           = models.CharField(max_length=512, help_text="Job title")
    cmdline         = models.CharField(max_length=1024, help_text="Job cmdline", null=True, blank=True)

    uuid            = models.UUIDField(default=uuid.uuid1, editable=False, help_text="job uuid", db_index=True)

    suite_name      = models.CharField(max_length=128, help_text="Test suite name", blank=True)
    suite_ver       = models.CharField(max_length=128, help_text="Test suite version")
    author          = models.CharField(max_length=128, help_text="Job author: user@mycompany.localdomain", null=True, blank=True)
    product_name    = models.CharField(max_length=128, help_text="Tested product name", null=True, blank=True)
    product_ver     = models.CharField(max_length=128, help_text="Tested product version", null=True, blank=True)

    begin           = models.DateTimeField(help_text="Job begin datetime", null=True, blank=True)
    end             = models.DateTimeField(help_text="Job end datetime", null=True, blank=True)
    duration        = models.DurationField(help_text="total execution time (sec)")
    upload          = models.DateTimeField(help_text="Job upload datetime", default=timezone.now)

    links           = models.CharField(max_length=1024, help_text="{'link name': 'link url', 'link2': 'url2'}", null=True, blank=True)

    tests_total     = models.IntegerField(help_text="Total number of tests in the job", null=True)
    tests_completed = models.IntegerField(help_text="Total number of tests completed", null=True)
    tests_failed    = models.IntegerField(default=0, help_text="Total number of failed tests", null=True)
    tests_errors    = models.IntegerField(default=0, help_text="Total number of tests with errors", null=True)
    tests_warnings  = models.IntegerField(default=0, help_text="Total number of tests with warnings", null=True)

    project         = models.ForeignKey(ProjectModel, help_text="Job project", on_delete=models.CASCADE)

    regression      = models.ForeignKey('perftracker.RegressionModel', help_text="Regression of this job", related_name="regr", null=True, blank=True, on_delete=models.CASCADE)
    regression_tag  = models.CharField(max_length=512, help_text="MyProduct-2.0 regression", null=True, blank=True, db_index=True)

    deleted         = models.BooleanField(help_text="True means the Job was deleted", db_index=True, default=False)

    def __str__(self):
        return "#%d, %s" % (self.id, self.title)

    def ptUpdate(self, json_data):
        from perftracker.models.test import TestModel

        j = ptJson(json_data, obj_name="job json", exception_type=SuspiciousOperation)

        project_name = j.get_str('project_name', require=True)
        self.uuid = j.get_uuid('uuid', require=True)

        self.title = j.get_str('job_title')
        if not self.title:
            self.title = j.get_str('title', require=True)
        self.cmdline = j.get_str('cmdline')
        self.project = ProjectModel.ptGetByName(j.get_str('project_name'))

        now = timezone.now()

        env_nodes_json = j.get_list('env_nodes')
        tests_json = j.get_list('tests', require=True)

        for t in tests_json:
            if 'uuid' not in t:
                raise SuspiciousOperation("test doesn't have 'uuid' key: %s" % str(t))
            test = TestModel(job=self, uuid=t['uuid'])
            test.ptUpdate(self, t, validate_only=True)  # FIXME, double ptUpdate() call (here and below)

        self.suite_name = j.get_str('suite_name')
        self.suite_ver  = j.get_str('suite_ver')
        self.author     = j.get_str('author')
        self.product_name = j.get_str('product_name')
        self.product_ver  = j.get_str('product_ver')
        self.links = json.dumps(j.get_dict('links'))
        self.regression_tag = json_data.get('regression_tag', '')

        self.upload = now

        begin = j.get_datetime('begin', now)
        end = j.get_datetime('end', now)

        self.tests_total = 0
        self.tests_completed = 0
        self.tests_failed = 0
        self.tests_errors = 0
        self.tests_warnings = 0

        append = False if self.deleted else j.get_bool('append')

        self.deleted = False

        if append:
            if self.duration:
                self.duration += end - begin
            else:
                self.duration = end - begin
            if not self.begin:
                self.begin = begin
            self.end = end
        else:
            self.duration = end - begin
            self.begin = begin
            self.end = end

        if self.begin and (self.begin.tzinfo is None or self.begin.tzinfo.utcoffset(self.begin) is None):
            raise SuspiciousOperation("'begin' datetime object must include timezone: %s" % str(self.begin))
        if self.end and (self.end.tzinfo is None or self.end.tzinfo.utcoffset(self.end) is None):
            raise SuspiciousOperation("'end' datetime object must include timezone: %s" % str(self.end))

        self.save()

        # process env_nodes, try not to delete and re-create all the nodes each time because normally this is static information
        env_nodes_to_update = EnvNodeModel.ptFindEnvNodesForUpdate(self, env_nodes_json)
        if env_nodes_to_update:
            EnvNodeModel.objects.filter(job=self).delete()
            for env_node_json in env_nodes_to_update:
                serializer = EnvNodeUploadSerializer(job=self, data=env_node_json)
                if serializer.is_valid():
                    serializer.save()
                else:
                    raise SuspiciousOperation(str(serializer.errors) + ", original json: " + str(env_node_json))

        # process tests
        tests = TestModel.objects.filter(job=self)
        test_seq_num = 0
        uuid2test = {}
        for t in tests:
            uuid2test[str(t.uuid)] = t
            if test_seq_num <= t.seq_num:
                test_seq_num = t.seq_num

        for t in tests_json:
            test_uuid = t['uuid']

            if test_uuid not in uuid2test:
                uuid2test[test_uuid] = TestModel(job=self, uuid=test_uuid)
                test_seq_num += 1
                uuid2test[test_uuid].seq_num = test_seq_num

            test = uuid2test[test_uuid]

            test.ptUpdate(self, t)

            self.tests_total += 1
            if test.ptStatusIsCompleted():
                self.tests_completed += 1
            if test.ptStatusIsFailed():
                self.tests_failed += 1
            if test.errors:
                self.tests_errors += 1
            if test.warnings:
                self.tests_warnings += 1
            ret = uuid2test.pop(test_uuid, None)

        if not append:
            TestModel.ptDeleteTests(uuid2test.keys())

        for t in uuid2test.values():
            self.tests_total += 1
            if t.ptStatusIsCompleted():
                self.tests_completed += 1
            if t.ptStatusIsFailed():
                self.tests_failed += 1
            if t.errors:
                self.tests_errors += 1
            if t.warnings:
                self.tests_warnings += 1

        self.save()

    def ptGenFileName(self):
        name = self.title
        if self.id:
            name = "job-%d-%s" % (self.id, name)
        return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

    def save(self):
        super(JobModel, self).save()

        from perftracker.models.regression import RegressionModel
        r = RegressionModel.ptOnJobSave(self)
        if r is not None:
            self.regression = r
            super(JobModel, self).save()

    class Meta:
        verbose_name = "Job"
        verbose_name_plural = "Jobs"


class JobBaseSerializer(serializers.ModelSerializer):
    env_node = serializers.SerializerMethodField()
    duration = ptDurationField()

    def get_env_node(self, job):
        # this function is required to apply 'parent=None' filter because env_node children will be
        # populated by the EnvNodeNestedSerializer
        objs = EnvNodeModel.objects.filter(job=job.id, parent=None).all()
        if isinstance(self, JobSimpleSerializer):
            return EnvNodeSimpleSerializer(objs, many=True).data
        else:
            return EnvNodeNestedSerializer(objs, many=True).data


class JobSimpleSerializer(JobBaseSerializer):
    class Meta:
        model = JobModel
        fields = ('id', 'title', 'suite_name', 'suite_ver', 'env_node', 'end', 'duration', 'upload',
                  'tests_total', 'tests_completed', 'tests_failed', 'tests_errors', 'tests_warnings', 'project',
                  'product_name', 'product_ver')


class JobNestedSerializer(JobBaseSerializer):
    class Meta:
        model = JobModel
        fields = ('id', 'title', 'cmdline', 'uuid', 'suite_name', 'suite_ver', 'product_name', 'product_ver',
                  'links', 'env_node', 'begin', 'end', 'duration', 'upload',
                  'tests_total', 'tests_completed', 'tests_failed', 'tests_errors', 'tests_warnings', 'project',
                  'product_name', 'product_ver')


class JobDetailedSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobModel
        depth = 1
        fields = [f.name for f in JobModel._meta.get_fields()] + ['tests']
