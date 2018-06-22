import uuid
import itertools
import json

from datetime import timedelta
from datetime import datetime

from django.db import models
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.core.exceptions import SuspiciousOperation

from rest_framework import serializers

from perftracker.models.project import ProjectModel
from perftracker.models.env_node import EnvNodeModel, EnvNodeUploadSerializer, EnvNodeSimpleSerializer, EnvNodeNestedSerializer
from perftracker.helpers import ptDurationField, pt_is_valid_uuid


class JobModel(models.Model):
    title           = models.CharField(max_length=512, help_text="Job title")
    cmdline         = models.CharField(max_length=1024, help_text="Job cmdline", null=True, blank=True)

    uuid            = models.UUIDField(default=uuid.uuid1, editable=False, help_text="job uuid", db_index=True)

    suite_name      = models.CharField(max_length=128, help_text="Test suite name")
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

    deleted         = models.BooleanField(help_text="True means the Job was deleted", db_index=True, default=False)

    def __str__(self):
        return "#%d, %s" % (self.id, self.title)

    def ptUpdate(self, json_data):
        from perftracker.models.test import TestModel

        self.ptValidateJson(json_data)

        self.title = json_data['job_title']
        self.cmdline = json_data.get('cmdline', None)
        self.uuid = json_data['uuid']
        self.project = ProjectModel.ptGetByName(json_data['project_name'])

        now = timezone.now()

        tests_json = json_data.get('tests', [])
        env_nodes_json = json_data.get('env_nodes', [])

        self.suite_name = json_data.get('suite_name', '')
        self.suite_ver  = json_data.get('suite_ver', '')
        self.author     = json_data.get('author', None)
        self.product_name = json_data.get('product_name', None)
        self.product_ver  = json_data.get('product_ver', None)
        self.links = json.dumps(json_data.get('links', None))
        self.begin = parse_datetime(json_data['begin']) if json_data.get('begin', None) else now
        self.end = parse_datetime(json_data['end']) if json_data.get('end', None) else now
        self.upload = now
        self.duration = self.end - self.begin
        self.tests_total = json_data.get('tests_total', len(tests_json))

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
        uuid2test = {}
        for t in tests:
            uuid2test[str(t.uuid)] = t

        self.tests_completed = 0
        self.tests_failed = 0
        self.tests_errors = 0
        self.tests_warnings = 0

        for t in tests_json:
            TestModel.ptValidateJson(t)
            test_uuid = t['uuid']

            if test_uuid not in uuid2test:
                uuid2test[test_uuid] = TestModel(job=self, uuid=test_uuid)

            test = uuid2test[test_uuid]

            test.ptUpdate(self, t)

            if test.ptStatusIsCompleted():
                self.tests_completed += 1
            if test.ptStatusIsFailed():
                self.tests_failed += 1
            if test.errors:
                self.tests_errors += 1
            if test.warnings:
                self.tests_warnings += 1
            ret = uuid2test.pop(test_uuid, None)

        TestModel.ptDeleteTests(uuid2test.keys())

        self.save()

    @staticmethod
    def ptValidateJson(json_data):
        for key in ('project_name', 'job_title', 'uuid', 'tests'):
            if key not in json_data:
                raise SuspiciousOperation("'%s' key is not found in the POST request payload" % key)
        if 'links' in json_data:
            if type(json_data['links']) is not dict:
                raise SuspiciousOperation("Invalid job 'links' format '%s', it must be a dictionary" % json_data['links'])
        if not pt_is_valid_uuid(json_data['uuid']):
            raise SuspiciousOperation("Invalid job 'uuid' format '%s', it must be uuid1" % json_data['uuid'])

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
                  'tests_total', 'tests_completed', 'tests_failed', 'tests_errors', 'tests_warnings', 'project')


class JobNestedSerializer(JobBaseSerializer):
    class Meta:
        model = JobModel
        fields = ('id', 'title', 'cmdline', 'uuid', 'suite_name', 'suite_ver', 'product_name', 'product_ver',
                  'links', 'env_node', 'begin', 'end', 'duration', 'upload',
                  'tests_total', 'tests_completed', 'tests_failed', 'tests_errors', 'tests_warnings', 'project')
