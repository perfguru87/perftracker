import json
import re
import uuid

from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.utils import timezone
from rest_framework import serializers

from perftracker.helpers import PTDurationField, PTJson
from perftracker.models.artifact import ArtifactLinkModel, ArtifactMetaSerializer, ArtifactMetaModel
from perftracker.models.env_node import EnvNodeModel, EnvNodeUploadSerializer, EnvNodeSimpleSerializer, \
    EnvNodeNestedSerializer
from perftracker.models.project import ProjectModel, ProjectSerializer


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

    tests_total     = models.IntegerField(help_text="Total number of tests in the job", null=False)
    tests_completed = models.IntegerField(help_text="Number of tests completed", null=False)
    tests_failed    = models.IntegerField(default=0, help_text="Number of failed tests", null=False)
    tests_errors    = models.IntegerField(default=0, help_text="Number of tests with errors (includes failed)", null=False)
    tests_warnings  = models.IntegerField(default=0, help_text="Number of tests with warnings", null=False)

    testcases_total = models.IntegerField(help_text="Total number of test cases in the job", null=False)
    testcases_errors= models.IntegerField(help_text="Number of test cases with test errors/failures", null=False)

    project         = models.ForeignKey(ProjectModel, help_text="Job project", on_delete=models.CASCADE)

    regression_original = models.ForeignKey('perftracker.RegressionModel', help_text="Original regression of this job",
                                            related_name="regr_original", null=True, blank=True, on_delete=models.SET_NULL)
    regression_linked   = models.ForeignKey('perftracker.RegressionModel', help_text="Regression this job linked to",
                                            related_name="regr_linked", null=True, blank=True, on_delete=models.SET_NULL)

    deleted         = models.BooleanField(help_text="True means the Job was deleted", db_index=True, default=False)

    def __str__(self):
        s = "#%d, %s" % (self.id, self.title)
        if self.product_name or self.product_ver:
            s += " [" + self.product_name + " " + self.product_ver + "]"
        return s

    def pt_update(self, json_data):
        from perftracker.models.test import TestModel

        j = PTJson(json_data, obj_name="job json", exception_type=SuspiciousOperation)

        project_name = j.get_str('project_name', require=True)
        self.uuid = j.get_uuid('uuid', defval=uuid.uuid1())

        self.title = j.get_str('job_title')
        if not self.title:
            self.title = j.get_str('title', require=True)
        self.cmdline = j.get_str('cmdline')
        self.project = ProjectModel.pt_get_by_name(j.get_str('project_name'))

        # append = False if self.deleted else j.get_bool('append')
        append = j.get_bool('append')

        now = timezone.now()

        env_nodes_json = j.get_list('env_nodes')
        tests_json = j.get_list('tests')

        key2test = {}
        tests_to_delete = {}
        tests_to_commit = {}
        test_seq_num = 0

        # process existing tests
        if self.id:
            for t in TestModel.objects.filter(job=self):
                test_seq_num = max(t.seq_num, test_seq_num)
                u = str(t.uuid)
                if append:
                    t.pt_validate_uniqueness(key2test)
                    tests_to_commit[u] = t
                else:
                    tests_to_delete[u] = t

        for t in tests_json:
            if not len(t.keys()):
                continue
            u = TestModel.pt_get_uuid(t)
            if u in tests_to_delete:
                tests_to_commit[u] = tests_to_delete[u]
                del tests_to_delete[u]
            else:
                test_seq_num += 1
                try:
                    tests_to_commit[u] = TestModel.objects.get(uuid=u)
                except TestModel.MultipleObjectsReturned:
                    TestModel.objects.filter(uuid=self.uuid).delete()
                    tests_to_commit[u] = TestModel(uuid=u, seq_num=test_seq_num)
                except TestModel.DoesNotExist:
                    tests_to_commit[u] = TestModel(uuid=u, seq_num=test_seq_num)
            tests_to_commit[u].pt_update(t)
            tests_to_commit[u].pt_validate_uniqueness(key2test)

        self.suite_name = j.get_str('suite_name')
        self.suite_ver  = j.get_str('suite_ver')
        self.author     = j.get_str('author')
        self.product_name = j.get_str('product_name')
        self.product_ver  = j.get_str('product_ver')
        regression_tag = json_data.get('regression_tag', '')

        links = json_data.get('links', None)
        if links == None or links == "":
            self.links = json.dumps({})
        elif isinstance(links, dict):
            self.links = json.dumps(links)
        elif not links.startswith("{"):
            self.links = json.dumps({links: links})
        else:
            self.links = json.dumps(j.get_dict('links'))

        self.upload = now

        begin = j.get_datetime('begin', now)
        end = j.get_datetime('end', now)

        self.tests_total = 0
        self.tests_completed = 0
        self.tests_failed = 0
        self.tests_errors = 0
        self.tests_warnings = 0

        self.testcases_total = 0
        self.testcases_errors = 0

        self.deleted = False

        if not append or j.get_bool('is_edited') or not self.duration or not self.begin:
            self.duration = end - begin
            self.begin = begin
            self.end = end
        else:
            # job is being appended, do correct duration math
            if self.end < begin:  # 1st upload
                self.duration += end - begin
            else:  # subsequent upload
                self.duration += end - self.end
            self.end = end


        if self.begin and (self.begin.tzinfo is None or self.begin.tzinfo.utcoffset(self.begin) is None):
            raise SuspiciousOperation("'begin' datetime object must include timezone: %s" % str(self.begin))
        if self.end and (self.end.tzinfo is None or self.end.tzinfo.utcoffset(self.end) is None):
            raise SuspiciousOperation("'end' datetime object must include timezone: %s" % str(self.end))

        self.save()

        # process env_nodes, try not to delete and re-create all the nodes each time because normally this is static information
        env_nodes_to_update = EnvNodeModel.pt_find_env_nodes_for_update(self, env_nodes_json)
        if env_nodes_to_update:
            EnvNodeModel.objects.filter(job=self).delete()
            for env_node_json in env_nodes_to_update:
                serializer = EnvNodeUploadSerializer(job=self, data=env_node_json)
                if serializer.is_valid():
                    serializer.save()
                else:
                    raise SuspiciousOperation(str(serializer.errors) + ", original json: " + str(env_node_json))

        testcases = {}
        #  Test Case (aka Section in comparison) is defined by 2 possible scenarios:
        #    - tests with the same tag and different categories
        #    - tests with no categories, and same group

        for t in tests_to_commit.values():
            t.job = self
            t.pt_save()

            self.tests_total += 1
            if t.pt_status_is_completed():
                self.tests_completed += 1
            test_ok = True
            if t.pt_status_is_failed():
                self.tests_failed += 1
                test_ok = False
            if t.errors:
                test_ok = False
            if t.warnings:
                self.tests_warnings += 1

            self.tests_errors += int(not test_ok)
            testcase = t.tag if t.category else t.group
            if testcase in testcases:
                testcases[testcase] = testcases[testcase] and test_ok
            else:
                testcases[testcase] = test_ok

        self.testcases_total = len(testcases)
        self.testcases_errors = len([1 for ok in testcases.values() if not ok])

        if tests_to_delete:
            TestModel.pt_delete_tests(tests_to_delete.keys())

        if regression_tag is not None:
            from perftracker.models.regression import RegressionModel
            r = RegressionModel.pt_on_job_save(self, regression_tag)
            self.regression_original = r
            self.regression_linked   = r

        self.save()

    def pt_gen_filename(self):
        name = self.title
        if self.id:
            name = "job-%d-%s" % (self.id, name)
        return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

    @staticmethod
    def pt_change_regression_link(job_id, new_link_status):
        job = JobModel.objects.get(pk=job_id)

        curr_link_status = job.regression_linked is not None
        if curr_link_status == new_link_status:
            raise KeyError

        job.regression_linked = None if job.regression_linked is not None else job.regression_original
        job.save()

    def save(self):
        super(JobModel, self).save()

        if self.regression_original is not None:
            self.regression_original.pt_set_first_last_job()

    class Meta:
        verbose_name = "Job"
        verbose_name_plural = "Jobs"


def handle_job_duration(job):
    if not job.duration:
        return 0
    dur = int(round(job.duration.total_seconds()))
    if not job.begin or not job.end:
        return dur
    maxdur = int(round((job.end - job.begin).total_seconds()))
    return min(dur, maxdur)


class JobBaseSerializer(serializers.ModelSerializer):
    env_node = serializers.SerializerMethodField()
    is_linked = serializers.SerializerMethodField()
    artifacts = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()

    def get_is_linked(self, job):
        return job.regression_linked is not None

    def get_project(self, job):
        return ProjectSerializer(job.project).data

    def get_env_node(self, job):
        # this function is required to apply 'parent=None' filter because env_node children will be
        # populated by the EnvNodeNestedSerializer
        objs = EnvNodeModel.objects.filter(job=job.id, parent=None).all()
        if isinstance(self, JobSimpleSerializer):
            return EnvNodeSimpleSerializer(objs, many=True).data
        else:
            return EnvNodeNestedSerializer(objs, many=True).data

    def get_artifacts(self, job):
        objs = ArtifactLinkModel.objects.filter(linked_uuid=job.uuid, deleted=False).all()
        artifacts = []
        for obj in objs:
            try:
                artifacts.append(obj.artifact)
            except ArtifactMetaModel.DoesNotExist:
                continue
        return ArtifactMetaSerializer(artifacts, many=True).data

    def get_duration(self, job):
        return handle_job_duration(job)


class JobSimpleSerializer(JobBaseSerializer):
    class Meta:
        model = JobModel
        fields = ('id', 'title', 'suite_name', 'suite_ver', 'env_node', 'end', 'duration', 'upload',
                  'tests_total', 'tests_completed', 'tests_failed', 'tests_errors', 'tests_warnings',
                  'project', 'product_name', 'product_ver', 'is_linked', 'testcases_total', 'testcases_errors')


class JobNestedSerializer(JobBaseSerializer):
    class Meta:
        model = JobModel
        fields = ('id', 'title', 'cmdline', 'uuid', 'suite_name', 'suite_ver', 'product_name', 'product_ver',
                  'links', 'env_node', 'begin', 'end', 'duration', 'upload',
                  'tests_total', 'tests_completed', 'tests_failed', 'tests_errors', 'tests_warnings',
                  'project', 'product_name', 'product_ver', 'artifacts', 'testcases_total', 'testcases_errors')


class JobDetailedSerializer(serializers.ModelSerializer):
    duration = serializers.SerializerMethodField()

    def get_duration(self, job):
        return handle_job_duration(job)

    class Meta:
        model = JobModel
        depth = 1
        fields = [f.name for f in JobModel._meta.get_fields()] + ['tests']
