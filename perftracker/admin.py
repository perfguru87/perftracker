from perftracker.models.project import ProjectModel
from perftracker.models.job import JobModel
from perftracker.models.comparison import ComparisonModel
from perftracker.models.test_group import TestGroupModel
from perftracker.models.env_node import EnvNodeModel, EnvNodeTypeModel
from perftracker.models.hw_farm_node import HwFarmNodeModel
from django.contrib import admin

admin.site.register(ProjectModel)
admin.site.register(JobModel)
admin.site.register(ComparisonModel)
admin.site.register(TestGroupModel)
admin.site.register(EnvNodeModel)
admin.site.register(EnvNodeTypeModel)
admin.site.register(HwFarmNodeModel)
