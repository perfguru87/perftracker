"""perftracker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import url
from django.views.generic import RedirectView

from perftracker import views

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^favicon\.ico$', RedirectView.as_view(url='/static/img/favicon.ico'), name='favicon'),

    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/project/$', views.pt_project_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/home/$', views.pt_home_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/regression/(?P<regression_id>\d+)$', views.pt_regression_id_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/regression/$', views.pt_regression_all_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/comparison/(?P<cmp_id>\d+)/group/(?P<group_id>\d+)/test/(?P<test_id>\d+)$',
        views.pt_comparison_test_id_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/comparison/(?P<cmp_id>\d+)/group/(?P<group_id>\d+)/test/$',
        views.pt_comparison_test_all_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/comparison/(?P<cmp_id>\d+)/group/$', views.pt_comparison_group_all_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/comparison/(?P<cmp_id>\d+)$', views.pt_comparison_id_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/comparison/$', views.pt_comparison_all_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/job/(?P<job_id>\d+)/group/(?P<group_id>\d+)/test/(?P<test_id>\d+)$',
        views.pt_job_test_id_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/job/(?P<job_id>\d+)/group/(?P<group_id>\d+)/test/$', views.pt_job_test_all_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/job/(?P<job_id>\d+)/group/$', views.pt_job_group_all_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/job/(?P<job_id>\d+)$', views.pt_job_id_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/job/$', views.pt_job_all_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/hw_farm/(?P<hw_id>\d+)$', views.pt_hwfarm_node_id_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/hw_farm/$', views.pt_hwfarm_node_all_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/hw_lock/(?P<id>\d+)$', views.pt_hwfarm_node_lock_id_json),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/hw_lock/$', views.pt_hwfarm_node_lock_all_json),

    path('<int:project_id>/home/', views.pt_home_html, name='Home'),
    path('<int:project_id>/regression/<int:regression_id>', views.pt_regression_id_html, name='Regressions'),
    path('<int:project_id>/regression/', views.pt_regression_all_html, name='Regressions'),
    path('<int:project_id>/comparison/<int:cmp_id>', views.pt_comparison_id_html, name='Comparisons'),
    path('<int:project_id>/comparison/', views.pt_comparison_all_html, name='Comparisons'),
    path('<int:project_id>/job/<int:job_id>', views.pt_job_id_html, name='Jobs'),
    path('<int:project_id>/job/', views.pt_job_all_html, name='Jobs'),
    path('<int:project_id>/hw_farm/<int:hw_id>', views.pt_hwfarm_id_html, name='Hosts'),
    path('<int:project_id>/hw_farm/', views.pt_hwfarm_all_html, name='Hosts'),

    path('', RedirectView.as_view(url='/1/comparison/')),
    path('redirect/', views.pt_redirect),
]
