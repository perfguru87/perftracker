from scipy import stats

from collections import OrderedDict

from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.utils import timezone
from rest_framework import serializers
from scipy import stats

from perftracker.helpers import pt_float2human, pt_cut_common_sfx
from perftracker.models.env_node import EnvNodeSimpleSerializer
from perftracker.models.job import JobModel, JobSimpleSerializer
from perftracker.models.project import ProjectModel, ProjectSerializer
from perftracker.models.test import TestModel
from perftracker.models.test_group import TestGroupModel


class PTCmpChartType:
    AUTO = 0
    NOCHART = 1
    XYLINE = 2
    XYLINE_WITH_TREND = 3
    BAR = 4
    BAR_WITH_TREND = 5


CMP_CHARTS = (
    (PTCmpChartType.AUTO, 'Auto'),
    (PTCmpChartType.NOCHART, 'No charts'),
    (PTCmpChartType.XYLINE, 'XY-line'),
    (PTCmpChartType.XYLINE_WITH_TREND, 'XY-line + trend'),
    (PTCmpChartType.BAR, 'Bar charts'),
    (PTCmpChartType.BAR_WITH_TREND, 'Bar + trend'))


class PTCmpTableType:
    AUTO = 0
    HIDE = 1
    SHOW = 2


CMP_TABLES = (
    (PTCmpTableType.AUTO, 'Auto'),
    (PTCmpTableType.HIDE, 'Hide all tables'),
    (PTCmpTableType.SHOW, 'Show all tables'))


class PTCmpTestsType:
    AUTO = 0
    TESTS_WO_WARNINGS = 1
    TESTS_WO_ERRORS = 2
    ALL_TESTS = 3


CMP_TESTS = (
    (PTCmpTestsType.AUTO, 'Auto'),
    (PTCmpTestsType.TESTS_WO_WARNINGS, 'Tests w/o warnings'),
    (PTCmpTestsType.TESTS_WO_ERRORS, 'Tests w/o errors'),
    (PTCmpTestsType.ALL_TESTS, 'All tests'))


class PTCmpValueType:
    AUTO = 0
    AVERAGE = 1
    MIN = 2
    MAX = 3


CMP_VALUES = (
    (PTCmpValueType.AUTO, 'Auto'),
    (PTCmpValueType.AVERAGE, 'Average values'),
    (PTCmpValueType.MIN, 'Min values'),
    (PTCmpValueType.MAX, 'Max values'))


class ComparisonModel(models.Model):
    title       = models.CharField(max_length=512, help_text="Comparison title")

    author      = models.CharField(max_length=128, help_text="Comparison author: user@mycompany.localdomain", null=True, blank=True)
    project     = models.ForeignKey(ProjectModel, help_text="Comparison project", on_delete=models.CASCADE)
    updated     = models.DateTimeField(help_text="Comparison updated datetime", default=timezone.now)
    deleted     = models.BooleanField(help_text="True means the Comparison was deleted", db_index=True, default=False)

    is_public   = models.BooleanField(help_text="Seen to everybody", default=False, blank=True)

    charts_type = models.IntegerField(help_text="Charts type", default=0, choices=CMP_CHARTS)
    tables_type = models.IntegerField(help_text="Tables type", default=0, choices=CMP_TABLES)
    tests_type  = models.IntegerField(help_text="Tests type", default=0, choices=CMP_TESTS)
    values_type = models.IntegerField(help_text="Values type", default=0, choices=CMP_VALUES)

    _jobs       = models.ManyToManyField(JobModel, help_text="Jobs")
    _job_ids    = models.TextField(help_text="Id's of the jobs (needed for proper jobs ordering)")

    @staticmethod
    def pt_validate_json(json_data):
        if 'title' not in json_data:
            raise SuspiciousOperation("Comparison title is not specified: it must be 'title': '...'")
        if 'jobs' not in json_data:
            raise SuspiciousOperation("Comparison jobs are not specified: it must be 'jobs': [1, 3, ...] ")
        if type(json_data['jobs']) is not list:
            raise SuspiciousOperation("Comparison jobs must be a list: 'jobs': [1, 3, ...] ")

    @staticmethod
    def _pt_get_type(types, json_data, key, not_found_rv=0):
        if key not in json_data:
            return not_found_rv

        type2id = {}
        for id, type in types:
            type2id[type] = id
        id = type2id.get(json_data[key], None)
        if id is None:
            raise SuspiciousOperation("Unknown type: %s, acceptable types are: %s" % (json_data[key], ",".join(type2id.keys())))
        return id

    def pt_update(self, json_data):
        self.title = json_data['title']
        self.deleted = False
        self.charts_type = self._pt_get_type(CMP_CHARTS, json_data, 'charts_type')
        self.tables_type = self._pt_get_type(CMP_TABLES, json_data, 'tables_type')
        self.tests_type = self._pt_get_type(CMP_TESTS, json_data, 'tests_type')
        self.values_type = self._pt_get_type(CMP_VALUES, json_data, 'values_type')

        jobs = []

        for jid in json_data['jobs']:
            try:
                job = JobModel.objects.get(id=int(jid))
            except JobModel.DoesNotExist:
                raise SuspiciousOperation("Job with id = '%d' doesn't exist" % jid)
            jobs.append(job)

        self._job_ids = ",".join([str(j.id) for j in jobs])

        self.save()
        self._jobs.clear()
        for job in jobs:
            self._jobs.add(job)
        self.save()

    def pt_get_jobs(self):
        # the method is required to order the jobs according to the order specified by user
        _jobs = self._jobs.all()
        if not self._job_ids:
            return _jobs

        try:
            jids = list(map(int, self._job_ids.split(",")))
            return sorted(_jobs, key=lambda job: jids.index(job.id))
        except ValueError:
            return _jobs

    def __str__(self):
        return "#%d, %s" % (self.id, self.title)

    class Meta:
        verbose_name = "Comparison"
        verbose_name_plural = "Comparisons"


class ComparisonBaseSerializer(serializers.ModelSerializer):
    env_node = serializers.SerializerMethodField()
    suite_ver = serializers.SerializerMethodField()
    suite_name = serializers.SerializerMethodField()
    tests_total = serializers.SerializerMethodField()
    tests_errors = serializers.SerializerMethodField()
    testcases_total = serializers.SerializerMethodField()
    testcases_errors = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    def get_env_node(self, cmp):
        objs = []
        visited = set()
        for job in cmp.pt_get_jobs():
            #for obj in EnvNodeModel.objects.filter(job=job.id, parent=None).all():
            for obj in job.env_nodes.all().only("job_id", "parent", "name"):
                if obj.parent is not None or obj.name in visited:
                    continue
                visited.add(obj.name)
                objs.append(obj)

        return EnvNodeSimpleSerializer(objs, many=True).data

    def _pt_get_jobs_attr(self, cmp, attr):
        ret = []
        for job in cmp.pt_get_jobs():
            ret.append(str(job.__dict__[attr]))
        return ", ".join(ret)

    def _pt_get_jobs_sum(self, cmp, attr):
        ret = 0
        for job in cmp.pt_get_jobs():
            ret += job.__dict__[attr]
        return ret

    def get_suite_ver(self, cmp):
        return self._pt_get_jobs_attr(cmp, 'suite_ver')

    def get_suite_name(self, cmp):
        return self._pt_get_jobs_attr(cmp, 'suite_name')

    def get_tests_total(self, cmp):
        return [j.tests_total for j in cmp.pt_get_jobs()]

    def get_tests_errors(self, cmp):
        return [j.tests_errors for j in cmp.pt_get_jobs()]

    def get_testcases_total(self, cmp):
        return [j.testcases_total for j in cmp.pt_get_jobs()]

    def get_testcases_errors(self, cmp):
        return [j.testcases_errors for j in cmp.pt_get_jobs()]

    def get_project(self, cmp):
        return ProjectSerializer(cmp.project).data


class ComparisonSimpleSerializer(ComparisonBaseSerializer):
    jobs = serializers.SerializerMethodField()

    def get_jobs(self, cmp):
        # jobs = JobModel.objects.filter(jobejob.id, parent=None).all()
        return [j.id for j in cmp.pt_get_jobs()]

    class Meta:
        model = ComparisonModel
        fields = ('id', 'title', 'suite_name', 'suite_ver', 'env_node', 'updated',
                  'tests_total', 'tests_errors', 'testcases_total', 'testcases_errors', 'project', 'jobs')


class ComparisonNestedSerializer(ComparisonBaseSerializer):
    jobs = serializers.SerializerMethodField()

    def get_jobs(self, cmp):
        # jobs = JobModel.objects.filter(jobejob.id, parent=None).all()
        return JobSimpleSerializer(cmp.pt_get_jobs(), many=True).data

    class Meta:
        model = ComparisonModel
        fields = ('id', 'title', 'suite_name', 'suite_ver', 'env_node', 'updated', 'tests_total',
                  'tests_errors', 'testcases_total', 'testcases_errors', 'project', 'jobs', 'charts_type',
                  'tables_type', 'tests_type', 'values_type', 'deleted')


######################################################################
# Comparison viewer
######################################################################
#  Comparison View Anatomy:
#  Comparison
#  +- Group[]       : unique group names among all tests
#     +- Section[]  : see below, also named Test Case
#        +- Serie[] : XY data for chart line
#        +- Test[]  : tabular data for section table
#
#  Section (aka Test Case) is defined by 2 possible scenarios:
#    - tests with the same tag and different categories
#    - tests with no categories, and same group

def test_errors2str(t):
    s = "%d errors" % t.errors if t.errors else ""
    if t.pt_status_is_failed():
        if s:
            s += ", "
        s += t.status
    return s

class PTComparisonServSideTestView:
    def __init__(self, jobs):
        self.tests = [None] * len(jobs)
        self.title = ''
        self.id = 0
        self.seq_num = 0

    def pt_add_test(self, job, job_n, test_obj):
        self.tests[job_n] = test_obj
        if not self.id:
            self.title = test_obj.category or test_obj.tag   # if category is present, it is unique within section
            self.id = test_obj.id
            self.seq_num = test_obj.seq_num

    def table_row(self):
        if not len(self.tests):
            return []
        t = self.tests
        ret = ['', self.id, self.seq_num, self.title]
        for n in range(0, len(t)):
            if t[n]:
                ret.append(pt_float2human(t[n].avg_score))
                ret.append(int(round(100 * t[n].avg_dev / t[n].avg_score, 0)) if t[n].avg_score else 0)
                ret.append(test_errors2str(t[n]))
            else:
                ret.append("-")
                ret.append("-")
                ret.append("")

            for prev in range(0, n):
                if t[prev] is None or t[n] is None:
                    ret.append("- 0")
                    continue
                if not t[n].avg_score or not t[prev].avg_score:
                    d = 0
                elif t[prev].avg_score < t[n].avg_score:
                    d = 100 * (t[n].avg_score / t[prev].avg_score - 1)
                elif t[prev].avg_score > t[n].avg_score:
                    d = -100 * (t[prev].avg_score / t[n].avg_score - 1)
                else:
                    d = 0

                diff = 0
                try:
                    s = stats.ttest_ind_from_stats(t[prev].avg_score, t[prev].avg_dev, t[prev].samples,
                                                   t[n].avg_score, t[n].avg_dev, t[n].samples)
                    if s[1] < 0.1:
                        diff = 1
                except ZeroDivisionError:
                    diff = 1

                if diff:
                    if t[prev].avg_score < t[n].avg_score:
                        diff = (-1 if t[prev].less_better else 1)
                    elif t[prev].avg_score > t[n].avg_score:
                        diff = (1 if t[prev].less_better else -1)
                    elif t[prev].avg_score == t[n].avg_score:
                        diff = 0
                ret.append(str(int(round(d, 0))) + " " + str(diff))

        return ret


class PTComparisonServSideSerieView:
    def __init__(self, sect, legend):
        self.sect = sect
        self.tests = []
        self.legend = legend
        self._scores = None
        self._errors = None

    def pt_add_test(self, job, job_n, test_obj):
        self.tests.append(test_obj)
        if test_obj.pt_status_is_failed() or test_obj.errors:
            self.sect.has_failures = True

    def _init_scores(self):
        if self._scores:
            return

        self._scores = [None] * len(self.sect.x_axis_categories)
        self._errors = [None] * len(self.sect.x_axis_categories)
        maxi = 0
        for t in self.tests:
            i = self.sect.test_cat_to_axis_cat_seqnum.get(t.category)
            if i is None:
                print("WARNING: test category '%s' is not found in %s" % (t.category, str(self.sect.test_cat_to_axis_cat_seqnum)))
                continue
            maxi = max(maxi, i)
            self._scores[i] = pt_float2human(t.avg_score)
            self._errors[i] = test_errors2str(t)   # t.errors or ((t.loops or "all") if t.status == 'FAILED' else 0)
        self._scores = self._scores[:maxi + 1]
        self._errors = self._errors[:maxi + 1]

    @property
    def less_better(self):
        less_better_arr = [int(test.less_better) for test in self.tests]
        return less_better_arr[0] if len(set(less_better_arr)) == 1 else less_better_arr

    @property
    def data(self):
        self._init_scores()
        ret = []
        if self.sect.chart_type == PTCmpChartType.BAR:
            for n in range(0, len(self._scores)):
                if self._errors[n]:
                    pt = {"value": self._scores[n],
                          "label": {"show": 1, "formatter": "fail"},
                          "errors": self._errors[n]}
                    ret.append(pt)
                else:
                    ret.append(self._scores[n])
        else:
            for n in range(0, len(self._scores)):
                if self._scores[n] is None:
                    continue
                if self._errors[n]:
                    pt = { "value": [self.sect.x_axis_categories[n], self._scores[n]],
                           "symbol": "diamond",
                           "symbolSize": 10,
                           "itemStyle": {"color": '#000'},
                           "errors": self._errors[n]}
                    ret.append(pt)
                else:
                    ret.append([self.sect.x_axis_categories[n], self._scores[n]])
        return ret


class PTComparisonServSideSectView:
    def __init__(self, cmp_obj, jobs, title):
        self.cmp_obj = cmp_obj
        self.title = title or "Tests results"
        self.jobs = jobs
        self.tests = OrderedDict()
        self.tests_tags = set()
        self.chart_type = PTCmpChartType.NOCHART
        self.chart_trend_line = False
        self.table_type = cmp_obj.tables_type
        self.tests_categories = []
        self.x_axis_categories = []
        self.test_cat_to_axis_cat_seqnum = []
        self.x_axis_name = ''
        self.x_axis_type = 'category'
        self.x_axis_rotate = 0
        self.y_axis_name = ''
        self.has_failures = False

        titles = set(j.title for j in jobs)
        titles_vers = set(",".join((j.title, j.product_name, j.product_ver)) for j in jobs)
        add_title = len(titles) > 1
        add_ver = not add_title and len(titles_vers) != 1

        def job_legend(job):
            if len(jobs) == 1:
                s = job.title  # nothing to compare with, so no need for uniqueness
            else:
                s = "#%s: " % (list(jobs).index(job) + 1)
                if add_title or (not add_title and not add_ver):
                    s += job.title
                if add_ver and (job.product_name or job.product_ver):
                    tmpl = " [%s %s]" if add_title else " %s %s"
                    s += tmpl % (job.product_name, job.product_ver)
            job.calculated_legend = s  # requested from template
            return s

        self.legends = [job_legend(j) for j in jobs]
        self.series = [PTComparisonServSideSerieView(self, l) for l in self.legends]

    def pt_add_test(self, job, job_n, test_obj):
        key = "%s %s" % (test_obj.tag, test_obj.category)
        if key not in self.tests:
            self.tests[key] = PTComparisonServSideTestView(self.jobs)
            self.tests_categories.append(test_obj.category)
            self.y_axis_name = test_obj.metrics
        self.series[job_n].pt_add_test(job, job_n, test_obj)
        self.tests[key].pt_add_test(job, job_n, test_obj)
        self.tests_tags.add(test_obj.tag)

    @property
    def id(self):
        if not self.tests:
            return 0
        return min((t.seq_num, t.id) for t in self.tests.values())[1]  # id of test with min seq_num

    @property
    def table_data(self):
        return [t.table_row() for t in self.tests.values()]

    @property
    def same_tag(self):
        return len(self.tests_tags) == 1

    def _pt_init_chart_type(self):
        if self.cmp_obj.charts_type == PTCmpChartType.XYLINE_WITH_TREND:
            self.chart_type = PTCmpChartType.XYLINE
            self.chart_trend_line = True
            self.legends += [("%s (trend)" % l) for l in self.legends]
            return

        if self.cmp_obj.charts_type == PTCmpChartType.BAR_WITH_TREND:
            self.chart_type = PTCmpChartType.BAR
            self.chart_trend_line = True
            return

        if self.cmp_obj.charts_type != PTCmpChartType.AUTO:
            return

        if not self.same_tag:
            self.chart_type = PTCmpChartType.NOCHART
            return

        self.chart_type = PTCmpChartType.BAR
        if len(self.tests) <= 3:
            return

        int_ar = []
        for c in self.x_axis_categories:
            try:
               int_ar.append(float(c))
            except ValueError:
               if len(self.tests) > 10:
                  self.x_axis_rotate = 45
               return
        self.x_axis_type = 'value'
        self.chart_type = PTCmpChartType.XYLINE

    def pt_init_chart_and_table(self):
        self.x_axis_name, self.x_axis_categories, self.test_cat_to_axis_cat_seqnum = pt_cut_common_sfx(self.tests_categories)

        self._pt_init_chart_type()

        if self.chart_type == PTCmpChartType.XYLINE and self.has_failures:
            self.legends += [{"name": "Failed test", "icon": "diamond"}]

        if self.same_tag:
            if self.table_type == PTCmpTableType.AUTO:
                self.table_type = PTCmpTableType.HIDE if len(self.tests) > 5 else PTCmpTableType.SHOW
        else:
            if self.table_type == PTCmpTableType.AUTO:
                self.table_type = PTCmpTableType.SHOW

    @property
    def pageable(self):
        return len(self.tests) > 20


class PTComparisonServSideGroupView:
    def __init__(self, id, cmp_obj, jobs, group):
        self.cmp_obj = cmp_obj
        self.jobs = jobs
        self.group_obj = TestGroupModel.pt_get_by_tag(group)
        self.sections = OrderedDict()
        self.id = id

    def pt_add_test(self, job, job_n, test_obj):
        key = test_obj.tag if test_obj.category else ""
        if key not in self.sections:
            self.sections[key] = PTComparisonServSideSectView(self.cmp_obj, self.jobs, key)
        self.sections[key].pt_add_test(job, job_n, test_obj)

    def pt_init_chart_and_table(self):
        for s in self.sections.values():
            s.pt_init_chart_and_table()
        if len(self.sections) > 1:
            for s in self.sections.values():
                if s.title == "":
                    s.title = "Tests results"

    @property
    def num_sections(self):
        return len(self.sections)

class PTComparisonServSideView:
    def __init__(self, cmp_obj, section_ids=None):
        self.cmp_obj = cmp_obj
        self.job_objs = self.cmp_obj.pt_get_jobs()
        self.groups = OrderedDict()

        self.init(section_ids)

    def pt_add_test(self, job, job_n, test_obj):
        if test_obj.group not in self.groups:
            self.groups[test_obj.group] = PTComparisonServSideGroupView(len(self.groups), self.cmp_obj, self.job_objs, test_obj.group)
        self.groups[test_obj.group].pt_add_test(job, job_n, test_obj)

    def init(self, section_ids):
        # section_ids is a list of ids of 'sample' tests that give a reference to the sections in interest
        # see PTComparisonServSideSectView.id - min test ID is section id.
        # to get all other tests we need to filter by sample test tag (if it has category) or group (if no category)
        tags = []
        groups = []
        if section_ids:
            sample_tests = TestModel.objects.filter(id__in=section_ids).only("tag", "group", "category")
            for t in sample_tests:
                if t.category:
                    tags.append(t.tag)
                else:
                    groups.append(t.group)

        for i, job in enumerate(self.job_objs):
            tests = TestModel.objects.filter(job=job)
            if tags:
                tests = tests.filter(tag__in=tags)
            if groups:
                tests = tests.filter(group__in=groups)
            for t in tests.order_by('seq_num'):
                self.pt_add_test(job, i, t)

        for g in self.groups.values():
            g.pt_init_chart_and_table()
