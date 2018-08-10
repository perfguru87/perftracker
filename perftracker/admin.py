from django.contrib import admin

from perftracker.models.project import ProjectModel
from perftracker.models.job import JobModel
from perftracker.models.regression import RegressionModel
from perftracker.models.comparison import ComparisonModel
from perftracker.models.test_group import TestGroupModel
from perftracker.models.env_node import EnvNodeModel, EnvNodeTypeModel
from perftracker.models.hw_farm_node import HwFarmNodeModel
from perftracker.models.hw_farm_node_lock import HwFarmNodeLockModel

from django.contrib import admin
from django import forms
from django.db.models import Q

# This is required to limit the list of displayed hosts which can be locked
class HwFarmNodeLockForm(forms.ModelForm):

    class Meta:
        model = HwFarmNodeLockModel
        fields = ('title', 'owner', 'hw_nodes', 'begin', 'end', 'planned_dur_hrs', 'manual', 'deleted')

    def __init__(self, *args, **kwargs):
        super(HwFarmNodeLockForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['hw_nodes'].queryset = HwFarmNodeModel.objects.filter(Q(locked_by=self.instance.id) | Q(locked_by=None))
        else:
            self.fields['hw_nodes'].queryset = HwFarmNodeModel.objects.filter(locked_by=None)

    def save(self, commit=True):
        l = super(HwFarmNodeLockForm, self).save(commit=commit)

        hw_nodes_ids = self.cleaned_data['hw_nodes']

        hw_nodes = HwFarmNodeModel.objects.filter(id__in=hw_nodes_ids)
        for n in hw_nodes:
            if n.locked_by and n.locked_by != l:
                 raise forms.ValidationError("Node '%s' is already locked" % str(n))

        l.save()

        l.hw_nodes.clear()
        for n in hw_nodes:
            l.hw_nodes.add(n)

        return l


class HwFarmNodeLockAdmin(admin.ModelAdmin):
    form = HwFarmNodeLockForm

admin.site.register(ProjectModel)
admin.site.register(JobModel)
admin.site.register(RegressionModel)
admin.site.register(ComparisonModel)
admin.site.register(TestGroupModel)
admin.site.register(EnvNodeModel)
admin.site.register(EnvNodeTypeModel)
admin.site.register(HwFarmNodeModel)
admin.site.register(HwFarmNodeLockModel, HwFarmNodeLockAdmin)
