from collections import OrderedDict

import numpy
from django.db import models
from rest_framework import serializers

from perftracker.helpers import pt_float2human
from perftracker.models.job import JobModel, JobSimpleSerializer
from perftracker.models.project import ProjectModel, ProjectSerializer
from perftracker.models.test import TestModel


class RegressionModel(models.Model):
    title     = models.CharField(max_length=512, help_text="Job title")
    tag       = models.CharField(max_length=512, help_text="MyProduct-2.0 regression", db_index=True)
    project   = models.ForeignKey(ProjectModel, help_text="Job project", on_delete=models.CASCADE)
    jobs      = models.IntegerField(help_text="Number of jobs in regression", blank=True)

    first_job = models.ForeignKey(JobModel, help_text="First job", related_name="regr_first_job", null=True, blank=True, on_delete=models.CASCADE)
    last_job  = models.ForeignKey(JobModel, help_text="Last job", related_name="regr_last_job", null=True, blank=True, on_delete=models.CASCADE)

    deleted   = models.BooleanField(help_text="True means the Job was deleted", db_index=True, default=False)

    def __str__(self):
        return "#%d, %s" % (self.id, self.title)

    def save(self):
        super(RegressionModel, self).save()

    def pt_get_all_jobs(self, order='end'):
        return JobModel.objects.filter(regression_original=self, deleted=False).order_by(order).all()

    def pt_get_linked_jobs(self, order='end'):
        return JobModel.objects.filter(regression_linked=self, deleted=False).order_by(order).all()

    def pt_set_first_last_job(self):
        jobs = self.pt_get_linked_jobs()
        if len(jobs):
            first = jobs[0]
            last = jobs[len(jobs) - 1]
        else:
            first = None
            last = None

        if self.first_job != first or self.last_job != last or self.jobs != len(jobs):
            self.first_job = first
            self.last_job = last
            self.jobs = len(jobs)
            self.save()

    @staticmethod
    def pt_on_job_save(job, regression_tag):
        try:
            r = RegressionModel.objects.get(tag=regression_tag, project=job.project)
        except RegressionModel.DoesNotExist:
            r = RegressionModel(title="%s regression" % job.project.name, tag=regression_tag, project=job.project, jobs=0)
            r.save()

        return r


class RegressionBaseSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()

    def get_project(self, regression):
        return ProjectSerializer(regression.project).data


class RegressionSimpleSerializer(RegressionBaseSerializer):

    first_job = serializers.SerializerMethodField()
    last_job = serializers.SerializerMethodField()

    def get_first_job(self, regression):
        return JobSimpleSerializer(regression.first_job, many=False).data

    def get_last_job(self, regression):
        return JobSimpleSerializer(regression.last_job, many=False).data

    class Meta:
        model = RegressionModel
        fields = ('id', 'title', 'tag', 'jobs', 'project', 'first_job', 'last_job')


class RegressionNestedSerializer(RegressionBaseSerializer):

    jobs_list = serializers.SerializerMethodField()

    def get_jobs_list(self, regression):
        jobs = regression.pt_get_all_jobs(order='-end')
        return JobSimpleSerializer(jobs, many=True).data

    class Meta:
        model = RegressionModel
        fields = ('id', 'title', 'tag', 'jobs', 'project', 'project', 'jobs_list')


######################################################################
# Regression viewer
######################################################################

# FIXME: move to view or templates
TREND_RATIO_THR = [[0.5, 'pt_regr_neg2'],
                   [0.9, 'pt_regr_neg'],
                   [1.1, 'pt_regr_norm'],
                   [1.5, 'pt_regr_pos'],
                   [0, 'pt_regr_pos2']]


class PTRegressionServSideSeriesView:
    def __init__(self, id, key):
        self.id = id
        self.key = key
        self.data = []
        self.x_axis_type = "category"
        self.x_axis_rotate = 0
        self.y_axis_name = ""
        self.title = ""
        self.css_class = 'pt_regr_norm'  # FIXME: move to view or templates
        self.less_better = False
        self.trend_begin = 0
        self.trend_end = 0
        self.trend_ratio = 1
        self.show_regression = False

    def pt_add_test(self, job, job_n, test_obj):
        if not test_obj.avg_score:
            return

        self.data.append((job.product_ver if job.product_ver is not None else '?', pt_float2human(test_obj.avg_score)))
        if not self.title or test_obj.less_better != self.less_better:
            self.title = test_obj.metrics + " " + ("[lower is better]" if test_obj.less_better else "[bigger is better]")
            self.less_better = test_obj.less_better

    def calc_trend(self):
        l = len(self.data)

        if l <= 1:
            return
        elif l <= 6:
            p_coeff = numpy.polyfit( range(0, l), self.values, 1)
            p = numpy.poly1d(p_coeff)
            self.trend_begin = p(0)
            self.trend_end = p(l - 1)
        else:
            self.trend_begin = numpy.mean([d[1] for d in self.data[0:3]])
            self.trend_end =   numpy.mean([d[1] for d in self.data[-3:]])

        # base = self.data[0][1]
        # end = self.data[-1][1]

        base = self.trend_begin
        end  = self.trend_end

        if base and not self.less_better:
            self.trend_ratio = end / base
        elif end and self.less_better:
            self.trend_ratio = base / end

        self.css_class = 'pt_regr_pos2'
        for tr, css_class in TREND_RATIO_THR:
            if self.trend_ratio < tr:
                self.css_class = css_class
                break

        if self.trend_ratio <= 0.9 or self.trend_ratio >= 1.1:
            self.show_regression = True

    @property
    def categories(self):
        return [d[0] for d in self.data]

    @property
    def values(self):
        return [d[1] for d in self.data]

    @property
    def xy_values(self):
        ret = []
        for d in self.data:
            ret.append([len(ret), d[1]])
        return ret


class PTRegressionServSideGroupView:
    def __init__(self, id):
        self.id = id
        self.series = OrderedDict()

    def pt_add_test(self, job, job_n, test_obj):
        key = test_obj.tag
        if test_obj:
            key += " {%s}" % test_obj.category
        if key not in self.series:
            self.series[key] = PTRegressionServSideSeriesView(len(self.series), key)
        self.series[key].pt_add_test(job, job_n, test_obj)

    def calc_trends(self):
        for s in self.series.values():
            s.calc_trend()


class PTRegressionServSideView:
    def __init__(self, regr_obj):
        self.regr_obj = regr_obj
        self.job_objs = regr_obj.pt_get_linked_jobs()
        self.groups = OrderedDict()

        self.init()

    def pt_add_test(self, job, job_n, test_obj):
        if test_obj.group not in self.groups:
            self.groups[test_obj.group] = PTRegressionServSideGroupView(len(self.groups))
        self.groups[test_obj.group].pt_add_test(job, job_n, test_obj)

    def init(self):
        for job_n in range(0, len(self.job_objs)):
            job = self.job_objs[job_n]

            tests = TestModel.objects.filter(job=job).order_by('seq_num')
            for test_obj in tests:
                self.pt_add_test(job, job_n, test_obj)

        for g in self.groups.values():
            g.calc_trends()

        # FIXME, crap
        self.info = OrderedDict()
        self.info["pt_regr_neg2"] = [0, "Degradation > 50%", True]
        self.info["pt_regr_neg"]  = [0, "Degradation > 10%", True]
        self.info["pt_regr_norm"] = [0, "No degradation", False]
        self.info["pt_regr_pos"]  = [0, "Improvement > 10%", False]
        self.info["pt_regr_pos2"] = [0, "Improvement > 50%", False]

        for g in self.groups.values():
           for s in g.series.values():
               self.info[s.css_class][0] += 1

        for style in self.info.keys():
           if not self.info[style][0]:
               self.info[style][2] = False
               continue
           if not self.info[style][2]:
               self.info[style][2] = True
           break
