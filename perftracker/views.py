# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import json
import http.client

from django.views.generic.base import TemplateView
from django.template import RequestContext
from django.template.response import TemplateResponse
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseForbidden
from django.http import JsonResponse, Http404
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize
from django.core.exceptions import SuspiciousOperation, ObjectDoesNotExist, ValidationError
from django.contrib.auth.decorators import login_required
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q
from django.db.models import Count
from django.db.models.query import QuerySet

from perftracker import __pt_version__
from perftracker.models.project import ProjectModel
from perftracker.models.comparison import ComparisonModel, ComparisonSimpleSerializer, ComparisonNestedSerializer, PTComparisonServSideView
from perftracker.models.regression import RegressionModel, RegressionSimpleSerializer, RegressionNestedSerializer, PTRegressionServSideView
from perftracker.models.comparison import PTCmpTableType, PTCmpChartType
from perftracker.models.job import JobModel, JobSimpleSerializer, JobNestedSerializer, JobDetailedSerializer
from perftracker.models.hw_farm_node import HwFarmNodeModel, HwFarmNodeSimpleSerializer, HwFarmNodeNestedSerializer
from perftracker.models.hw_farm_node_lock import HwFarmNodeLockModel, HwFarmNodeLockTypeModel
from perftracker.models.hw_farm_node_lock import HwFarmNodeLockSimpleSerializer, HwFarmNodeLockNestedSerializer, HwFarmNodesLocksTimeline
from perftracker.models.test import TestModel, TestSimpleSerializer, TestDetailedSerializer
from perftracker.models.test_group import TestGroupModel, TestGroupSerializer
from perftracker.models.env_node import EnvNodeModel
from perftracker.models.artifact import ArtifactMetaModel, ArtifactLinkModel, ArtifactMetaSerializer

from perftracker.forms import PTCmpDialogForm, PTHwFarmNodeLockForm, PTJobUploadForm
from perftracker.helpers import pt_dur2str, pt_is_valid_uuid
from perftracker.rest import pt_rest_ok, pt_rest_err, pt_rest_not_found, pt_rest_method_not_allowed

API_VER = '1.0'


def pt_handle_500(request):
    context = RequestContext(request)
    return HttpResponseBadRequest(context)


def pt_redirect(request):
    redirect = request.session.get('redirect', None)
    del request.session['redirect']
    if redirect:
        return HttpResponseRedirect(redirect)
    return HttpResponse()

# HTML views ###

def pt_base_html(request, project_id, template, params=None, obj=None):
    if request.method == 'POST':
        raise Http404

    params = params if params else {}

    dentries = request.path.split("/")
    verb = dentries[2] if len(dentries) > 3 else "comparison"

    default_params = {'projects': ProjectModel().pt_get_all(),
                      'request': request,
                      'verb': verb,
                      'obj': obj,
                      'pt_version': __pt_version__,
                      'project': ProjectModel.pt_get_by_id(project_id),
                      'api_ver': API_VER,
                      'screens': [('Home', '/%d/home/' % project_id),
                                  ('Regressions', '/%d/regression/' % project_id),
                                  ('Comparisons', '/%d/comparison/' % project_id),
                                  ('Jobs', '/%d/job/' % project_id),
                                  ('Hosts', '/%d/hw_farm/' % project_id)]}
    params.update(default_params)
    return TemplateResponse(request, template, params)


def pt_home_html(request, project_id):
    return pt_base_html(request, project_id, 'home.html')


def pt_comparison_all_html(request, project_id):
    return pt_base_html(request, project_id, 'comparison_all.html')


def pt_comparison_id_html(request, project_id, cmp_id):
    try:
        obj = ComparisonModel.objects.get(pk=cmp_id)
    except ComparisonModel.DoesNotExist:
        raise Http404

    # register 'range' template tag

    return pt_base_html(request, project_id, 'comparison_id.html',
                      params={'jobs': obj.pt_get_jobs(),
                              'cmp_view': PTComparisonServSideView(obj),
                              'PTCmpChartType': PTCmpChartType,
                              'PTCmpTableType': PTCmpTableType
                              },
                      obj=obj)


def pt_regression_all_html(request, project_id):
    return pt_base_html(request, project_id, 'regression_all.html')


def pt_regression_id_html(request, project_id, regression_id):
    try:
        obj = RegressionModel.objects.get(pk=regression_id)
    except RegressionModel.DoesNotExist:
        raise Http404

    # register 'range' template tag

    return pt_base_html(request, project_id, 'regression_id.html',
                      params={'jobs': obj.pt_get_linked_jobs(),
                              'first_job': obj.first_job,
                              'last_job': obj.last_job,
                              'duration': pt_dur2str(obj.last_job.end - obj.first_job.end),
                              'regr_view': PTRegressionServSideView(obj),
                              'PTCmpChartType': PTCmpChartType,
                              'PTCmpTableType': PTCmpTableType,
                              },
                      obj=obj)


def _pt_upload_job_json(data, job_title=None, project_name=None):
    try:
        j = json.loads(data)
    except ValueError as e:
        return HttpResponse("can't load json: %s" % str(e), status = http.client.UNSUPPORTED_MEDIA_TYPE)

    if job_title:
        j['job_title'] = job_title
    if project_name:
        j['project_name'] = project_name

    uuid = j.get('uuid', None)
    append = j.get('append', False)

    if not uuid:
        return HttpResponse("job 'uuid' is no set", status=http.client.BAD_REQUEST)

    uuid = uuid.lower()
    if not pt_is_valid_uuid(uuid):
        return HttpResponse("job 'uuid' value '%s' is not valid" % uuid, status=http.client.BAD_REQUEST)

    new = False
    try:
        job = JobModel.objects.get(uuid=uuid)
    except JobModel.DoesNotExist:
        new = True
        title = j['job_title'] if 'job_title' in j else j['title']
        job = JobModel(title=title, uuid=uuid)

    try:
        job.pt_update(j)
    except (SuspiciousOperation, ValidationError) as e:
        return HttpResponse(str(e), status = http.client.BAD_REQUEST)

    return HttpResponse("OK, job %d has been %s" % (job.id, "created" if new else ("appended" if append else "updated")))


# @login_required
@csrf_exempt
def pt_job_all_html(request, project_id):
    if request.method == 'POST':
        f = PTJobUploadForm(request.POST, request.FILES)
        if f.is_valid():
            try:
                project = ProjectModel.objects.get(id=project_id)
            except ProjectModel.DoesNotExist:
                raise Http404

            try:
                data = request.FILES['job_file'].read()
                ret = _pt_upload_job_json(data, job_title=f.cleaned_data['job_title'].strip(), project_name=project.name)
                msg = ret.content.decode('utf-8')
                messages.success(request, msg) if ret.status_code == http.client.OK else messages.error(request, msg)
            except UnicodeDecodeError as e:
                messages.error(request, "can't decode json file")
        else:
            messages.error(request, 'Upload failed: ' + f.errors.as_text())
        return HttpResponseRedirect(request.get_full_path())

    params = {
               'cmp_form': PTCmpDialogForm(),
               'hw_lock_form': PTHwFarmNodeLockForm(),
               'hw_lock_types': HwFarmNodeLockTypeModel.pt_get_all(),
               'hw_lock_timeline': HwFarmNodesLocksTimeline(project_id).gen_html()
             }
    return pt_base_html(request, project_id, 'job_all.html', params=params)


# @login_required
def pt_job_id_html(request, project_id, job_id):
    try:
        job = JobModel.objects.get(pk=job_id)
    except JobModel.DoesNotExist:
        raise Http404

    if request.GET.get('as_json', False):
        j = JobDetailedSerializer(job).data
        resp = JsonResponse(JobDetailedSerializer(job, allow_null=False).data, safe=False, json_dumps_params={'indent': 2})
        resp['Content-Disposition'] = 'attachment; filename=%s.json' % job.pt_gen_filename()
        return resp

    return pt_base_html(request, project_id, 'job_id.html', obj=job)


# @login_required
def pt_hwfarm_all_html(request, project_id):
    params = {
               'hw_lock_form': PTHwFarmNodeLockForm(),
               'hw_lock_types': HwFarmNodeLockTypeModel.pt_get_all(),
               'hw_lock_timeline': HwFarmNodesLocksTimeline(project_id).gen_html()
             }

    return pt_base_html(request, project_id, 'hw_farm_node_all.html', params=params)


# @login_required
def pt_hwfarm_id_html(request, project_id, id):
    return pt_base_html(request, project_id, 'hw_farm_node_id.html')


# Json views ###


@csrf_exempt
def pt_project_json(request, api_ver, project_id):
    ret = []
    projects = ProjectModel.objects.all()
    for p in ProjectModel.objects.all():
        ret.append({"id": p.id, "name": p.name})
    return JsonResponse(ret, safe=False)


def pt_home_json(request, api_ver, project_id):
    return JsonResponse([], safe=False)


@csrf_exempt
def pt_job_all_json(request, api_ver, project_id):

    class JobJson(BaseDatatableView):
        # The model we're going to show
        model = JobModel

        # define the columns that will be returned
        columns = ['', 'id', 'end', 'project', 'env_node', 'product_name', 'product_ver', 'title',
                   'suite_ver', 'duration', 'tests_total', 'tests_completed', 'tests_failed']

        # define column names that will be used in sorting
        # order is important and should be same as order of columns
        # displayed by datatables. For non sortable columns use empty
        # value like ''
        order_columns = ['', 'id', 'end', 'project', 'env_node', 'product_name', 'product_ver', 'title',
                         'suite_ver', 'duration', 'tests_total', 'tests_completed', 'tests_failed']

        # set max limit of records returned, this is used to protect our site if someone tries to attack our site
        # and make it return huge amount of data
        max_display_length = 5000

        def render_column(self, row, column):
            # We want to render user as a custom column
            if column == 'tests_total':
                return '{0} {1}'.format(row.tests_total, row.tests_completed)
            else:
                return super(JobJson, self).render_column(row, column)

        def filter_queryset(self, qs):
            # use parameters passed in GET request to filter queryset

            # simple example:
            search = self.request.GET.get(u'search[value]', None)
            if search:
                qs = qs.filter(Q(title__icontains=search) | Q(suite_ver__icontains=search))

            if int(project_id) != 0:
                qs = qs.filter(Q(project_id=project_id))

            qs = qs.filter(Q(deleted=False))

            # more advanced example using extra parameters
            # filter_title = self.request.GET.get(u'title', None)
            #
            # if filter_title:
            #    title_parts = filter_title.split(' ')
            #    qs_params = None
            #    for part in title_parts:
            #        q = Q(title__istartswith=part)|Q(title__istartswith=part)
            #        qs_params = qs_params | q if qs_params else q
            #    qs = qs.filter(qs_params)
            return qs

        def prepare_results(self, qs):
            return JobSimpleSerializer(qs, many=True).data

    if request.method == 'POST':
        return _pt_upload_job_json(request.body.decode('utf-8'))

    return JobJson.as_view()(request)


@csrf_exempt
def pt_job_id_json(request, api_ver, project_id, job_id):

    if request.method == 'PATCH':
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Wrong json")

        try:
            job_id = data['job_id']
            link = data['link']
        except KeyError:
            return HttpResponseBadRequest("Wrong data in json")

        try:
            JobModel.pt_change_regression_link(job_id, link)
        except JobModel.DoesNotExist:
            HttpResponseBadRequest("There is no such job")
        except KeyError:
            return HttpResponseBadRequest("Job has already been in this status")

        return HttpResponse("OK")

    elif request.method in ['PUT', 'GET', 'DELETE']:
        try:
            job = JobModel.objects.get(pk=job_id)
        except JobModel.DoesNotExist:
            return JsonResponse([], safe=False, status=http.client.NOT_FOUND)

        if request.method == 'PUT':
            if request.content_type != "application/json":
                return HttpResponseBadRequest("content_type must be 'application/json'")

            body_unicode = request.body.decode('utf-8')
            try:
                body = json.loads(body_unicode)
            except ValueError as ve:
                return HttpResponseBadRequest("unable to parse JSON data. Error : {0}".format(ve))

            job.pt_update(body)
            messages.success(request, "job #%s was successfully edited" % str(job_id))
            return HttpResponse("OK")

        elif request.method == 'GET':
            return JsonResponse(JobNestedSerializer(job).data, safe=False)

        elif request.method == 'DELETE':
            job.deleted = True
            job.save()
            messages.success(request, "job #%s was deleted" % str(job_id))
            return JsonResponse([], safe=False)

    return JsonResponse([], safe=False, status=http.client.NOT_IMPLEMENTED)


def pt_job_test_all_json(request, api_ver, project_id, job_id, group_id):
    class TestView(BaseDatatableView):
        model = TestModel
        columns = ['', 'id', 'seq_num', 'group', 'tag', 'category', 'duration', 'avg_score', 'avg_plusmin']
        order_columns = ['', 'id', 'seq_num', 'group', 'tag', 'category', 'duration', 'avg_score', 'avg_plusmin']
        max_display_length = 5000

        def filter_queryset(self, qs):
            # use parameters passed in GET request to filter queryset

            qs = qs.filter(job=job_id)

            gid = int(group_id)
            if gid:
                try:
                    group = TestGroupModel.objects.get(pk=gid)
                    qs = qs.filter(job=job_id).filter(group=group.tag)
                except TestGroupModel.DoesNotExist:
                    qs = TestModel.objects.none()

            search = self.request.GET.get(u'search[value]', None)
            if search:
                qs = qs.filter(Q(tag__icontains=search) | Q(category__icontains=search))
            return qs

        def prepare_results(self, qs):
            return TestSimpleSerializer(qs, many=True).data

    return TestView.as_view()(request)


@csrf_exempt
def pt_job_group_all_json(request, api_ver, project_id, job_id):
    try:
        job = JobModel.objects.get(pk=job_id)
    except JobModel.DoesNotExist:
        raise Http404

    groups = TestModel.objects.filter(job=job).values('group').annotate(Count('id'))

    ret = []
    for g in groups:
        ret.append(TestGroupModel.pt_get_by_tag(g['group']))
    return JsonResponse(TestGroupSerializer(ret, many=True).data, safe=False)


def pt_job_test_id_json(request, api_ver, project_id, job_id, group_id, test_id):
    try:
        return JsonResponse(TestDetailedSerializer(TestModel.objects.get(id=test_id)).data, safe=False)
    except TestModel.DoesNotExist:
        return JsonResponse([], safe=False)


@csrf_exempt
def pt_comparison_all_json(request, api_ver, project_id):
    class ComparisonJson(BaseDatatableView):
        # The model we're going to show
        model = ComparisonModel

        # define the columns that will be returned
        columns = ['', 'id', 'updated', 'project', 'env_node', 'suite_ver', 'title', 'jobs',
                   'tests_total', 'tests_completed', 'tests_failed']

        # define column names that will be used in sorting
        # order is important and should be same as order of columns
        # displayed by datatables. For non sortable columns use empty
        # value like ''
        order_columns = ['', 'id', 'updated', 'project', 'env_node', 'suite_ver', 'title', 'jobs',
                         'tests_total', 'tests_completed', 'tests_failed']

        # set max limit of records returned, this is used to protect our site if someone tries to attack our site
        # and make it return huge amount of data
        max_display_length = 5000

        def render_column(self, row, column):
            # We want to render user as a custom column
            if column == 'tests_total':
                return '{0} {1}'.format(row.tests_total, row.tests_completed)
            else:
                return super(JobJson, self).render_column(row, column)

        def filter_queryset(self, qs):
            # use parameters passed in GET request to filter queryset

            # simple example:
            search = self.request.GET.get(u'search[value]', None)
            if search:
                qs = qs.filter(Q(title__icontains=search) | Q(suite_ver__icontains=search))

            if int(project_id) != 0:
                qs = qs.filter(Q(project_id=project_id))

            qs = qs.filter(Q(deleted=False))

            return qs

        def prepare_results(self, qs):
            return ComparisonSimpleSerializer(qs, many=True).data

    if request.method == "POST":
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)

        try:
            ComparisonModel.pt_validate_json(body)
        except SuspiciousOperation as e:
            return HttpResponseBadRequest(e)

        cmp = ComparisonModel(project=ProjectModel.pt_get_by_id(project_id))
        try:
            cmp.pt_update(body)
        except SuspiciousOperation as e:
            return HttpResponseBadRequest(e)

        return JsonResponse({'id': cmp.id}, safe=False)

    return ComparisonJson.as_view()(request)

@csrf_exempt
def pt_comparison_id_json(request, api_ver, project_id, cmp_id):
    try:
        comparison = ComparisonModel.objects.get(pk=cmp_id)
    except ComparisonModel.DoesNotExist:
        return JsonResponse([], safe=False, status=http.client.NOT_FOUND)

    if request.method == 'DELETE':
        comparison.deleted = True
        comparison.save()
        messages.success(request, "comparison #%s was deleted" % str(cmp_id))
        return JsonResponse([], safe=False)

    try:
        return JsonResponse(ComparisonNestedSerializer(ComparisonModel.objects.get(pk=cmp_id)).data, safe=False)
    except ComparisonModel.DoesNotExist:
        return JsonResponse([], safe=False)


def pt_comparison_test_all_json(request, api_ver, project_id, cmp_id, group_id):
    cmp = ComparisonModel.objects.get(pk=cmp_id)
    jobs = cmp.pt_get_jobs()
    ret = []
    for job in jobs:
        ret.append(pt_job_test_all_json(request, api_ver, project_id, job.id, group_id).content.decode("utf-8"))
    return HttpResponse("[" + ",".join(ret) + "]", content_type="application/json")


@csrf_exempt
def pt_comparison_group_all_json(request, api_ver, project_id, cmp_id):
    try:
        cmp = ComparisonModel.objects.get(pk=cmp_id)
    except ComparisonModel.DoesNotExist:
        raise Http404

    jobs = cmp.pt_get_jobs()

    found = set()
    ret = []
    for job in jobs:
        groups = TestModel.objects.filter(job=job).values('group').annotate(Count('id'))
        for g in groups:
            group = g['group']
            if group in found:
                continue
            found.add(group)
            ret.append(TestGroupModel.pt_get_by_tag(group))
    return JsonResponse(TestGroupSerializer(ret, many=True).data, safe=False)


def pt_comparison_test_id_json(request, api_ver, project_id, cmp_id, group_id, test_id):
    cmp = ComparisonModel.objects.get(pk=cmp_id)

    try:
        orig_test = TestModel.objects.get(id=test_id)
    except TestModel.DoesNotExist:
        return JsonResponse([], safe=False)

    jobs = cmp.pt_get_jobs()
    ret = []
    for job in jobs:
        try:
            test = TestModel.objects.get(job=job.id, tag=orig_test.tag, group=orig_test.group, category=orig_test.category)
            ret.append(TestDetailedSerializer(test).data)
        except TestModel.DoesNotExist:
            ret.append({})
        except TestModel.MultipleObjectsReturned:
            # w/a for bug in versions < 0.3 where it was possible to upload tests with identical tag and category
            tests = TestModel.objects.filter(job=job.id, tag=orig_test.tag, group=orig_test.group, category=orig_test.category)
            for t in tests:
                ret.append(TestDetailedSerializer(t).data)
    return JsonResponse(ret, safe=False)


@csrf_exempt
def pt_regression_all_json(request, api_ver, project_id):
    class RegressionJson(BaseDatatableView):
        # The model we're going to show
        model = RegressionModel

        # define the columns that will be returned
        columns = ['', 'id', 'project', 'title', 'tag', 'jobs', 'first_job', 'last_job']

        # define column names that will be used in sorting
        # order is important and should be same as order of columns
        # displayed by datatables. For non sortable columns use empty
        # value like ''
        order_columns = ['', 'id', 'project', 'title', 'tag', 'jobs', 'first_job', 'last_job']

        # set max limit of records returned, this is used to protect our site if someone tries to attack our site
        # and make it return huge amount of data
        max_display_length = 5000

        def filter_queryset(self, qs):
            # use parameters passed in GET request to filter queryset

            # simple example:
            search = self.request.GET.get(u'search[value]', None)
            if search:
                qs = qs.filter(Q(title__icontains=search) | Q(suite_ver__icontains=search))

            if int(project_id) != 0:
                qs = qs.filter(Q(project_id=project_id))

            qs = qs.filter(Q(deleted=False))

            return qs

        def prepare_results(self, qs):
            return RegressionSimpleSerializer(qs, many=True).data

    return RegressionJson.as_view()(request)


def pt_regression_id_json(request, api_ver, project_id, regression_id):
    try:
        return JsonResponse(RegressionNestedSerializer(RegressionModel.objects.get(pk=regression_id)).data, safe=False)
    except RegressionModel.DoesNotExist:
        return JsonResponse([], safe=False)


def pt_regression_test_all_json(request, api_ver, project_id, regression_id, group_id):
    regr = RegressionModel.objects.get(pk=regression_id)
    jobs = regr.jobs.all()
    ret = []
    for job in jobs:
        ret.append(pt_job_test_all_json(request, api_ver, project_id, job.id, group_id).content.decode("utf-8"))
    return HttpResponse("[" + ",".join(ret) + "]", content_type="application/json")


@csrf_exempt
def pt_regression_group_all_json(request, api_ver, project_id, regression_id):
    try:
        regr = RegressionModel.objects.get(pk=regression_id)
    except RegressionModel.DoesNotExist:
        raise Http404

    jobs = regr.jobs.all()

    found = set()
    ret = []
    for job in jobs:
        groups = TestModel.objects.filter(job=job).values('group').annotate(Count('id'))
        for g in groups:
            group = g['group']
            if group in found:
                continue
            found.add(group)
            ret.append(TestGroupModel.ptGetByTag(group))
    return JsonResponse(TestGroupSerializer(ret, many=True).data, safe=False)


def pt_regression_test_id_json(request, api_ver, project_id, regression_id, group_id, test_id):
    regr = RegressionModel.objects.get(pk=regression_id)
    try:
        orig_test = TestModel.objects.get(id=test_id)
    except TestModel.DoesNotExist:
        return JsonResponse([], safe=False)

    jobs = regr.jobs.all()
    ret = []
    for job in jobs:
        try:
            test = TestModel.objects.get(job=job.id, tag=orig_test.tag, category=orig_test.category)
            ret.append(TestDetailedSerializer(test).data)
        except TestModel.DoesNotExist:
            ret.append({})
    return JsonResponse(ret, safe=False)


@csrf_exempt
def pt_hwfarm_node_all_json(request, api_ver, project_id):
    project_id = int(project_id)

    class HwFarmNodeJson(BaseDatatableView):
        # The model we're going to show
        model = HwFarmNodeModel

        # define the columns that will be returned
        columns = ['', 'order', 'id', 'name', 'os', 'hostname', 'purpose', 'vendor', 'model',
                   'cpus_count', 'ram_gb', 'storage_tb', 'network_gbs', 'locked_by']
        order_columns = ['', 'order', 'id', 'name', 'os', 'hostname', 'purpose',
                   'vendor', 'model', 'cpus_count', 'ram_gb', 'storage_tb', 'network_gbs', 'locked_by']

        # set max limit of records returned, this is used to protect our site if someone tries to attack our site
        # and make it return huge amount of data
        max_display_length = 5000

        def render_column(self, row, column):
            # We want to render user as a custom column
            if column == 'model':
                return '{0} {1}'.format(row.vendor, row.model)
            else:
                return super(HwFarmNodeJson, self).render_column(row, column)

        def filter_queryset(self, qs):
            # use parameters passed in GET request to filter queryset

            # simple example:
            search = self.request.GET.get(u'search[value]', None)
            if search:
                qs = qs.filter(Q(name__icontains=search) | Q(os__icontains=search) |
                               Q(hostname__icontains=search) | Q(purpose__icontains=search) |
                               Q(model__icontains=search))

            if int(project_id) != 0:
                qs = qs.filter(Q(projects=project_id))

            f = 0
            while True:
                _filter = self.request.GET.get(u'filter[%d][column]' % f, None)
                if not _filter:
                    break
                value = self.request.GET.get(u'filter[%d][value]' % f, None)
                if not value:
                    value = None
                qs = qs.filter(Q(**{_filter: value}))
                f += 1

            qs = qs.filter(Q(hidden=False))
            return qs

        def prepare_results(self, qs):
            return HwFarmNodeSimpleSerializer(qs, many=True).data

    try:
        return HwFarmNodeJson.as_view()(request)
    except ValueError:
        return HttpResponseBadRequest('bad request')

def pt_hwfarm_node_id_json(request, api_ver, project_id, hw_id):
    try:
        return JsonResponse(HwFarmNodeNestedSerializer(HwFarmNodeModel.objects.get(pk=hw_id)).data, safe=False)
    except HwFarmNodeModel.DoesNotExist:
        return JsonResponse([], safe=False)


@csrf_exempt
def pt_hwfarm_node_lock_all_json(request, api_ver, project_id):

    if request.method == 'POST':
        body_unicode = request.body.decode('utf-8')
        try:
            body = json.loads(body_unicode)
        except ValueError as ve:
            return HttpResponseBadRequest("unable to parse JSON data. Error : {0}".format(ve))

        obj = HwFarmNodeLockModel()

        try:
            obj.pt_validate_json(body)
        except SuspiciousOperation as e:
            return HttpResponseBadRequest(e)

        obj.pt_update(body)
        return HttpResponse("OK")

    if request.method == 'GET':

        class LockView(BaseDatatableView):
            model = HwFarmNodeLockModel
            columns = ['', 'id', 'title', 'owner', 'begin', 'end', 'manual', 'planned_dur_hrs']
            order_columns = ['', 'id', 'title', 'owner', 'begin', 'end', 'manual', 'planned_dur_hrs']
            max_display_length = 5000

            def filter_queryset(self, qs):
                search = self.request.GET.get(u'search[value]', None)
                if search:
                    qs = qs.filter(Q(tag__icontains=search) | Q(category__icontains=search))
                return qs

            def prepare_results(self, qs):
                return HwFarmNodeLockSimpleSerializer(qs, many=True).data

        return LockView.as_view()(request)

    return HttpResponseBadRequest("")


@csrf_exempt
def pt_hwfarm_node_lock_id_json(request, api_ver, project_id, id):

    try:
        obj = HwFarmNodeLockModel.objects.get(pk=id)
    except HwFarmNodeLockModel.DoesNotExist:
        return HttpResponseNotFound()

    if request.method == 'DELETE':
        # FIXME. Check owner
        obj.pt_unlock()
        return HttpResponse("OK")

    if request.method == 'PUT':

        if request.content_type != "application/json":
            return HttpResponseBadRequest("content_type must be 'application/json'")

        body_unicode = request.body.decode('utf-8')
        try:
            body = json.loads(body_unicode)
        except ValueError as ve:
            return HttpResponseBadRequest("unable to parse JSON data. Error : {0}".format(ve))

        try:
            HwFarmNodeLockModel.pt_validate_json(body)
        except SuspiciousOperation as e:
            return HttpResponseBadRequest(e)

        obj.pt_update(body)
        return HttpResponse("OK")

    try:
        return JsonResponse(HwFarmNodeLockNestedSerializer(HwFarmNodeLockModel.objects.get(pk=id)).data, safe=False)
    except HwFarmNodeLockModel.DoesNotExist:
        return JsonResponse([], safe=False)


@csrf_exempt
def pt_artifact_meta_all_json(request, api_ver, project_id):
    project_id = int(project_id)

    if not ArtifactMetaModel.pt_artifacts_enabled():
        return pt_rest_err(http.client.NOT_IMPLEMENTED, "Artifacts management is not configured, set the ARTIFACTS_STORAGE_DIR setting")

    if request.method == "GET":
        if project_id:
            qs = ArtifactMetaModel.objects.filter(project_id=project_id, deleted=False)
        else:
            qs = ArtifactMetaModel.objects.filter(deleted=False)
        try:
            start = int(request.GET.get('start', 0))
            length = int(request.GET.get('length', 10))
        except ValueError:
            raise SuspiciousOperation("start and length must be integer")

        qs = qs.order_by('-uploaded_dt')[start:(start+length)]
        return pt_rest_ok(ArtifactMetaSerializer(qs, many=True).data)

    raise pt_rest_method_not_allowed(request)


@csrf_exempt
def pt_artifact_meta_id_json(request, api_ver, project_id, uuid):
    project_id = int(project_id)

    uuid = uuid.lower()
    if not pt_is_valid_uuid(uuid):
        return pt_rest_bad_req("Invalid artifact UUID %s" % uuid)

    if not ArtifactMetaModel.pt_artifacts_enabled():
        return pt_rest_err(http.client.NOT_IMPLEMENTED, "Artifacts management is not configured, set the ARTIFACTS_STORAGE_DIR setting")

    try:
        artifact = ArtifactMetaModel.objects.get(uuid=uuid)
    except ArtifactMetaModel.DoesNotExist:
        artifact = None

    if request.method == "POST":
        if artifact is None:
            artifact = ArtifactMetaModel(uuid=uuid)
        return artifact.pt_update(request.POST, request.FILES)

    if artifact is None:
        return pt_rest_not_found("Artifact with UUID %s is not found" % uuid)

    if request.method == "PATCH":
        data = json.loads(request.body.decode("utf-8"))
        return artifact.pt_update(data)
    elif request.method == "DELETE":
        return artifact.pt_delete()
    elif request.method == "GET":
        return pt_rest_ok(ArtifactMetaSerializer(artifact).data)

    return pt_rest_method_not_allowed(request)


@csrf_exempt
def pt_artifact_content_id(request, project_id, uuid):
    if not ArtifactMetaModel.pt_artifacts_enabled():
        return pt_rest_err(http.client.NOT_IMPLEMENTED, "Artifacts management is not configured, set the ARTIFACTS_STORAGE_DIR setting")

    uuid = uuid.lower()
    if not pt_is_valid_uuid(uuid):
        return pt_rest_bad_req("Invalid artifact content UUID %s" % uuid)

    try:
        artifact = ArtifactMetaModel.objects.get(uuid=uuid)
    except ArtifactMetaModel.DoesNotExist:
        return Http404

    return artifact.pt_get_http_content()
