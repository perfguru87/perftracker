import numpy
import uuid
import itertools
import json
import copy
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
from perftracker.models.test_group import TestGroupModel, TEST_GROUP_TAG_LENGTH
from perftracker.helpers import ptDurationField, ptRoundedFloatField, ptRoundedFloatMKField, pt_is_valid_uuid

from pyecharts import Bar

TEST_STATUSES = ['NOTTESTED', 'SKIPPED', 'INPROGRESS', 'SUCCESS', 'FAILED']


class TestModel(models.Model):

    seq_num     = models.IntegerField(help_text="Test sequence number in the job", db_index=True)
    uuid        = models.UUIDField(default=uuid.uuid1, editable=False, help_text="test run uuid", db_index=True)
    tag         = models.CharField(max_length=512, help_text="Test tag used for resuts comparisons: Disk sequential read", db_index=True)
    binary      = models.CharField(max_length=128, help_text="Test binary: hdd_seq_read.exe")
    cmdline     = models.CharField(max_length=1024, help_text="Test cmdline: -f /root/file/ -O 100M -s 1")
    group       = models.CharField(max_length=TEST_GROUP_TAG_LENGTH, help_text="Test group tag")
    description = models.CharField(max_length=1024, help_text="Test description: disk sequential read test by 1M blocks")

    scores      = models.CharField(max_length=1024, help_text="Raw test scores: [12.21, 14.23, 12.94]")
    scores_rejected = models.IntegerField(default=0, help_text="Number of scores rejected")

    deviations  = models.CharField(max_length=1024, help_text="Test deviations: [0.02, 0.03, 0.01]")
    deviations_rejected = models.IntegerField(default=0, help_text="Number of deviations rejected")

    samples     = models.IntegerField(help_text="Number of test samples (iterations)", default=1)

    category    = models.CharField(max_length=128, help_text="Test category: 1-thread")
    metrics     = models.CharField(max_length=64, help_text="Test result metrics: MB/s")
    links       = models.CharField(max_length=1024, help_text="Test links json: {'test logs': 'http://logs.localdomain/231241.log'}")
    less_better = models.BooleanField(help_text="Set to True if 'less' score is better")
    errors      = models.IntegerField(help_text="Number of test errors")
    warnings    = models.IntegerField(help_text="Number of test warnings")
    begin       = models.DateTimeField(help_text="Test begin time", null=True)
    end         = models.DateTimeField(help_text="Test end time", null=True)
    loops       = models.IntegerField(help_text="Test loops", null=True)
    duration    = models.DurationField(help_text="total execution time (sec)")
    status      = models.CharField(max_length=16, help_text="Test status: %s" % str(TEST_STATUSES))

    job         = models.ForeignKey(JobModel, help_text="Job instance", on_delete=models.CASCADE)

    avg_score   = models.FloatField("Test average score: 13.02", null=True)
    min_score   = models.FloatField("Test min score: 12.21", null=True)
    max_score   = models.FloatField("Test max score: 14.23", null=True)

    avg_dev     = models.FloatField("Test average deviation: 0.02", null=True)
    min_dev     = models.FloatField("Test min deviation: 0.01", null=True)
    max_dev     = models.FloatField("Test max deviation: 0.03", null=True)

    avg_plusmin = models.FloatField("Deviation in % of average score: 0.02", null=True)
    min_plusmin = models.FloatField("Deviation in % of min score: 0.01", null=True)
    max_plusmin = models.FloatField("Deviation in % of max score: 0.03", null=True)

    def ptUpdate(self, job, json_data):
        self.ptValidateJson(json_data)

        self.seq_num = json_data['seq_num']
        self.tag = json_data['tag']

        self.binary = json_data.get('binary', '')
        self.cmdline = json_data.get('cmdline', '')
        self.description = json_data.get('description', '')

        scores = json_data['scores']
        deviations = json_data.get('deviations', None)

        self.scores = str(scores)
        self.deviations = str(deviations) if deviations else str([0] * len(scores))

        self.category = json_data.get('category', '')
        self.metrics = json_data.get('metrics', 'loops/sec')
        self.links = json.dumps(json_data.get('links', None))
        self.less_better = json_data.get('less_better', False)
        self.errors = len(json_data.get('errors', []))
        self.warnings = len(json_data.get('warnings', []))
        self.begin = parse_datetime(json_data['begin']) if json_data.get('begin', None) else None
        self.end = parse_datetime(json_data['end']) if json_data.get('end', None) else None
        self.status = json_data.get('status', "SUCCESS")

        dur_sec = json_data.get('duration_sec', 0)
        self.duration = timedelta(seconds=int(dur_sec)) if dur_sec else self.end - self.begin

        self.job = job
        self.group = json_data.get('group', '')
        TestGroupModel.ptGetByTag(self.group)  # ensure appropriate TestGroupModel object exists

        self.samples = json_data.get('samples', len(scores))

        self.avg_score = numpy.mean(scores)
        self.min_score = min(scores)
        self.max_score = max(scores)

        self.avg_dev = numpy.mean(deviations) if deviations else numpy.std(scores)
        self.min_dev = min(deviations) if deviations else self.avg_dev
        self.max_dev = max(deviations) if deviations else self.avg_dev

        self.avg_plusmin = int(round(100 * abs(self.avg_dev / self.avg_score))) if self.avg_score else 0
        self.min_plusmin = int(round(100 * abs(self.min_dev / self.min_score))) if self.min_score else 0
        self.max_plusmin = int(round(100 * abs(self.max_dev / self.max_score))) if self.max_score else 0

        if self.begin and (self.begin.tzinfo is None or self.begin.tzinfo.utcoffset(self.begin) is None):
            raise SuspiciousOperation("'begin' datetime object must include timezone: %s" % str(self.begin))
        if self.end and (self.end.tzinfo is None or self.end.tzinfo.utcoffset(self.end) is None):
            raise SuspiciousOperation("'end' datetime object must include timezone: %s" % str(self.end))

        try:
            obj = TestModel.objects.get(uuid=self.uuid)
        except TestModel.DoesNotExist:
            obj = None

        if obj is None or not self.ptIsEqualTo(obj):
            self.save()

    def __str__(self):
        return self.tag

    @staticmethod
    def ptValidateJson(json_data):
        j = str(json_data)
        if 'tag' not in json_data:
            raise SuspiciousOperation("%s: 'tag' field not found" % j)
        if 'uuid' not in json_data:
            raise SuspiciousOperation("%s: 'uuid' field not found" % j)
        if 'seq_num' not in json_data:
            raise SuspiciousOperation("%s: 'seq_num' field not found" % j)
        if not pt_is_valid_uuid(json_data['uuid']):
            raise SuspiciousOperation("%s: 'uuid' '%s' is not invalid, it must be version1 UUID" % (j, json_data['uuid']))
        if 'scores' not in json_data:
            raise SuspiciousOperation("%s: 'scores' field not found" % j)
        if type(json_data['scores']) is not list:
            raise SuspiciousOperation("%s: 'scores' field must be a list" % j)
        if 'links' in json_data:
            if type(json_data['links']) is not dict:
                raise SuspiciousOperation("Invalid test 'links' format '%s', it must be a dictionary" % json_data['links'])
        if 'deviations' in json_data:
            if type(json_data['deviations']) is not list:
                raise SuspiciousOperation("%s: 'deviations' field must be a list" % j)
            if len(json_data['deviations']) != len(json_data['scores']):
                raise SuspiciousOperation("%s: length of 'deviations' and 'scores' lists mismatch: %s, %s" %
                                          (j, json_data['deviations'], json_data['scores']))
        if 'status' in json_data:
            if not json_data['status'] in TEST_STATUSES:
                raise SuspiciousOperation("%s: invalid 'status' value '%s', must be one of: %s" % (j, json_data['status'], TEST_STATUSES))

    def ptStatusIsCompleted(self):
        return self.status in ("SUCCESS", "FAILED")

    def ptStatusIsFailed(self):
        return self.status == "FAILED"

    @staticmethod
    def ptDeleteTests(tests_uuids):
        """ Delete Test objects from the tests_uuids by 100 elements at once"""
        if not tests_uuids:
            return

        def grouper(n, iterable):
            args = [iter(iterable)] * n
            return ([e for e in t if e is not None] for t in itertools.zip_longest(*args))

        for uuids in grouper(100, tests_uuids):
            TestModel.objects.filter(reduce(lambda x, y: x | y, [Q(uuid=uuid) for uuid in uuids])).delete()

    def ptIsEqualTo(self, test):
        # FIXME, XXX - not sure this is right way to manage the problem of data object update in the database
        for f in self._meta.get_fields():
            if getattr(test, f.name) != getattr(self, f.name):
                return False
        return True

    @staticmethod
    def ptCreateSimpleBar(self):
        bar = Bar("My First Chart", "Here's the subtitle")
        bar.add("clothing", ["shirt", "sweater", "chiffon shirt", "pants", "high heels", "socks"], [5, 20, 36, 10, 75, 90])
        return bar

    class Meta:
        verbose_name = "Test result"
        verbose_name_plural = "Tests results"


class TestSimpleSerializer(serializers.ModelSerializer):
    duration = ptDurationField()
    avg_score = ptRoundedFloatMKField()
    avg_dev = ptRoundedFloatField()
    avg_plusmin = ptRoundedFloatField()

    class Meta:
        model = TestModel
        fields = ('id', 'seq_num', 'group', 'tag', 'category', 'duration', 'avg_score', 'avg_dev', 'avg_plusmin')


class TestDetailedSerializer(TestSimpleSerializer):

    class Meta:
        model = TestModel
        fields = [f.name for f in TestModel._meta.get_fields()]
