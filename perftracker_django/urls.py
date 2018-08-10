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

    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/home/$', views.ptHomeJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/regression/(?P<regression_id>\d+)$', views.ptRegressionIdJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/regression/$', views.ptRegressionAllJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/comparison/(?P<cmp_id>\d+)/group/(?P<group_id>\d+)/test/(?P<test_id>\d+)$',
        views.ptComparisonTestIdJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/comparison/(?P<cmp_id>\d+)/group/(?P<group_id>\d+)/test/$',
        views.ptComparisonTestAllJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/comparison/(?P<cmp_id>\d+)/group/$', views.ptComparisonGroupAllJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/comparison/(?P<cmp_id>\d+)$', views.ptComparisonIdJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/comparison/$', views.ptComparisonAllJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/job/(?P<job_id>\d+)/group/(?P<group_id>\d+)/test/(?P<test_id>\d+)$',
        views.ptJobTestIdJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/job/(?P<job_id>\d+)/group/(?P<group_id>\d+)/test/$', views.ptJobTestAllJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/job/(?P<job_id>\d+)/group/$', views.ptJobGroupAllJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/job/(?P<job_id>\d+)$', views.ptJobIdJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/job/$', views.ptJobAllJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/hw_farm/(?P<hw_id>\d+)$', views.ptHwFarmNodeIdJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/hw_farm/$', views.ptHwFarmNodeAllJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/hw_lock/(?P<id>\d+)$', views.ptHwFarmNodeLockIdJson),
    url(r'^api/v(?P<api_ver>\d+.\d+)/(?P<project_id>\d+)/hw_lock/$', views.ptHwFarmNodeLockAllJson),

    path('<int:project_id>/home/', views.ptHomeHtml, name='Home'),
    path('<int:project_id>/regression/<int:regression_id>', views.ptRegressionIdHtml, name='Regressions'),
    path('<int:project_id>/regression/', views.ptRegressionAllHtml, name='Regressions'),
    path('<int:project_id>/comparison/<int:cmp_id>', views.ptComparisonIdHtml, name='Comparisons'),
    path('<int:project_id>/comparison/', views.ptComparisonAllHtml, name='Comparisons'),
    path('<int:project_id>/job/<int:job_id>', views.ptJobIdHtml, name='Jobs'),
    path('<int:project_id>/job/', views.ptJobAllHtml, name='Jobs'),
    path('<int:project_id>/hw_farm/<int:hw_id>', views.ptHwFarmIdHtml, name='Hosts'),
    path('<int:project_id>/hw_farm/', views.ptHwFarmAllHtml, name='Hosts'),

    path('', RedirectView.as_view(url='/1/comparison/')),
    path('redirect/', views.ptRedirect),
]
