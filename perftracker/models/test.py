import itertools
import json
import uuid
from datetime import timedelta
from functools import reduce

import numpy
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.db import models
from django.db.models import Q
from rest_framework import serializers

from perftracker.helpers import PTDurationField, PTRoundedFloatField, PTRoundedFloatMKField, PTJson, pt_is_valid_uuid
from perftracker.models.job import JobModel
from perftracker.models.test_group import TestGroupModel, TEST_GROUP_TAG_LENGTH

TEST_STATUSES = ['NOTTESTED', 'SKIPPED', 'INPROGRESS', 'SUCCESS', 'FAILED']


class TestModel(models.Model):

    seq_num     = models.IntegerField(help_text="Test sequence number in the job", db_index=True)
    uuid        = models.UUIDField(default=uuid.uuid1, editable=False, help_text="test run uuid", db_index=True)
    tag         = models.CharField(max_length=512, help_text="Test tag used for resuts comparisons: Disk sequential read", db_index=True)
    binary      = models.CharField(max_length=128, help_text="Test binary: hdd_seq_read.exe")
    cmdline     = models.CharField(max_length=1024, help_text="Test cmdline: -f /root/file/ -O 100M -s 1")
    group       = models.CharField(max_length=TEST_GROUP_TAG_LENGTH, help_text="Test group tag")
    description = models.CharField(max_length=1024, help_text="Test description: disk sequential read test by 1M blocks")

    scores      = models.CharField(max_length=16384, help_text="Raw test scores: [12.21, 14.23, 12.94]")
    scores_rejected = models.IntegerField(default=0, help_text="Number of scores rejected")

    deviations  = models.CharField(max_length=1024, help_text="Test deviations: [0.02, 0.03, 0.01]")
    deviations_rejected = models.IntegerField(default=0, help_text="Number of deviations rejected")

    samples     = models.IntegerField(help_text="Number of test samples (iterations)", default=1)

    category    = models.CharField(max_length=128, help_text="Test category: 1-thread")
    metrics     = models.CharField(max_length=64, help_text="Test result metrics: MB/s")
    links       = models.CharField(max_length=1024, help_text="Test links json: {'test logs': 'http://logs.localdomain/231241.log'}")
    attribs     = models.CharField(max_length=1024, help_text="Custom test attributes json: {'version': '12.3'}")
    less_better = models.BooleanField(help_text="Set to True if 'less' score is better")
    errors      = models.IntegerField(help_text="Number of test errors")
    warnings    = models.IntegerField(help_text="Number of test warnings")
    begin       = models.DateTimeField(help_text="Test begin time", null=True)
    end         = models.DateTimeField(help_text="Test end time", null=True)
    loops       = models.IntegerField(help_text="Test loops", null=True)
    duration    = models.DurationField(help_text="total execution time (sec)")
    status      = models.CharField(max_length=16, help_text="Test status: %s" % str(TEST_STATUSES))

    job         = models.ForeignKey(JobModel, help_text="Job instance", related_name="tests", on_delete=models.CASCADE)

    avg_score   = models.FloatField("Test average score: 13.02", null=True)
    min_score   = models.FloatField("Test min score: 12.21", null=True)
    max_score   = models.FloatField("Test max score: 14.23", null=True)

    avg_dev     = models.FloatField("Test average deviation: 0.02", null=True)
    min_dev     = models.FloatField("Test min deviation: 0.01", null=True)
    max_dev     = models.FloatField("Test max deviation: 0.03", null=True)

    avg_plusmin = models.FloatField("Deviation in % of average score: 0.02", null=True)
    min_plusmin = models.FloatField("Deviation in % of min score: 0.01", null=True)
    max_plusmin = models.FloatField("Deviation in % of max score: 0.03", null=True)

    @staticmethod
    def pt_get_uuid(json_data):
        if 'uuid' in json_data:
            u = json_data['uuid']
            if not pt_is_valid_uuid(u):
               raise ValidationError("Invalid test uuid: '%s'" % u)
            return u.lower()
        return uuid.uuid1()

    def pt_update(self, json_data):
        j = PTJson(json_data, obj_name="test json", exception_type=SuspiciousOperation)

        if 'seq_num' in json_data:
            self.seq_num = json_data['seq_num']
        if not self.seq_num:
            self.seq_num = 0

        self.tag = j.get_str('tag', require=True)
        j.obj_name = self.tag

        self.binary = j.get_str('binary')
        self.cmdline = j.get_str('cmdline')
        self.description = j.get_str('description')

        self.status = j.get_str('status', "SUCCESS")

        if self.pt_status_is_failed():
            scores = j.get_list('scores', defval=[])
        else:
            score = j.get_float('score', defval=None)
            if score is None:
                scores = j.get_list('scores', require=True)
            else:
                scores = [score]
        deviations = j.get_list('deviations')

        self.scores = str(scores)
        self.deviations = str(deviations) if deviations else str([0] * len(scores))

        self.category = j.get_str('category')
        self.metrics = j.get_str('metrics', 'loops/sec')
        self.links = json.dumps(j.get_dict('links'))
        self.attribs = json.dumps(j.get_dict('attribs'))
        self.less_better = j.get_bool('less_better')
        self.begin = j.get_datetime('begin')
        self.end = j.get_datetime('end')
        self.loops = j.get_int('loops')
        if self.status not in TEST_STATUSES:
            raise SuspiciousOperation("invalid 'status' value '%s', must be one of: %s" % (self.status, str(TEST_STATUSES)))

        e = j.get('errors', 0)
        if type(e) is int:
            self.errors = e
        else:
            self.errors = len(j.get_list('errors'))

        w = j.get('warnings', 0)
        if type(w) is int:
            self.warnings = w
        else:
            self.warnings = len(j.get_list('warnings'))

        dur_sec = j.get_float('duration_sec', 0)
        if dur_sec:
            self.duration = timedelta(seconds=int(dur_sec))
        elif self.end and self.begin:
            self.duration = self.end - self.begin
        else:
            self.duration = timedelta(seconds=0)

        self.group = j.get_str('group')
        TestGroupModel.pt_get_by_tag(self.group)  # ensure appropriate TestGroupModel object exists

        self.samples = j.get_int('samples', len(scores))

        self.avg_score = numpy.mean(scores) if scores else 0
        self.min_score = min(scores) if scores else 0
        self.max_score = max(scores) if scores else 0

        self.avg_dev = 0
        if deviations or scores:
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

    def pt_save(self):
        try:
            obj = TestModel.objects.get(uuid=self.uuid)
        except TestModel.MultipleObjectsReturned:
            TestModel.objects.filter(uuid=self.uuid).delete()
            obj = None
        except TestModel.DoesNotExist:
            obj = None

        if obj is None or not self.pt_is_equal_to(obj):
            self.save()

    def __str__(self):
        return self.tag

    def pt_status_is_completed(self):
        return self.status in ("SUCCESS", "FAILED")

    def pt_status_is_failed(self):
        return self.status == "FAILED"

    @staticmethod
    def pt_delete_tests(tests_uuids):
        """ Delete Test objects from the tests_uuids by 100 elements at once"""
        if not tests_uuids:
            return

        def grouper(n, iterable):
            args = [iter(iterable)] * n
            return ([e for e in t if e is not None] for t in itertools.zip_longest(*args))

        for uuids in grouper(100, tests_uuids):
            TestModel.objects.filter(reduce(lambda x, y: x | y, [Q(uuid=uuid) for uuid in uuids])).delete()

    def pt_is_equal_to(self, test):
        # FIXME, XXX - not sure this is right way to manage the problem of data object update in the database
        for f in self._meta.get_fields():
            if getattr(test, f.name) != getattr(self, f.name):
                return False
        return True

    def pt_gen_unique_key(self):
        return "%s %s {%s}" % (self.group, self.tag, self.category)

    def pt_validate_uniqueness(self, key2test):
        key = self.pt_gen_unique_key()
        if key not in key2test:
            key2test[key] = self
            return

        test = key2test[key]
        if self.uuid == test.uuid:
            return
        if test.group != self.group or test.tag != self.tag or test.category != self.category:
            return
        raise ValidationError("test with given group ('%s'), tag ('%s') and category ('%s') already exists" %
                              (self.group, self.tag, self.category))

    class Meta:
        verbose_name = "Test result"
        verbose_name_plural = "Tests results"


class TestSimpleSerializer(serializers.ModelSerializer):
    duration = PTDurationField()
    avg_score = PTRoundedFloatMKField()
    avg_plusmin = PTRoundedFloatField()

    class Meta:
        model = TestModel
        fields = ('id', 'seq_num', 'group', 'tag', 'category', 'duration', 'avg_score', 'avg_plusmin', 'errors', 'status')


class TestDetailedSerializer(TestSimpleSerializer):

    class Meta:
        model = TestModel
        fields = [f.name for f in TestModel._meta.get_fields()]
