import re

from django.contrib import admin

from perftracker.models.project import ProjectModel
from perftracker.models.job import JobModel
from perftracker.models.regression import RegressionModel
from perftracker.models.comparison import ComparisonModel
from perftracker.models.test_group import TestGroupModel
from perftracker.models.env_node import EnvNodeModel, EnvNodeTypeModel
from perftracker.models.hw_farm_node import HwFarmNodeModel
from perftracker.models.hw_farm_node_lock import HwFarmNodeLockModel, HwFarmNodeLockTypeModel

from django.contrib import admin
from django import forms
from django.db.models import Q

# This is required to filter out the locked hosts from the list of hosts available for the lock
class HwFarmNodeLockModelForm(forms.ModelForm):

    class Meta:
        model = HwFarmNodeLockModel
        fields = ('title', 'owner', 'hw_nodes', 'begin', 'end', 'planned_dur_hrs', 'manual', 'deleted')

    def __init__(self, *args, **kwargs):
        super(HwFarmNodeLockModelForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['hw_nodes'].queryset = HwFarmNodeModel.objects.filter(Q(locked_by=self.instance.id) | Q(locked_by=None))
        else:
            self.fields['hw_nodes'].queryset = HwFarmNodeModel.objects.filter(locked_by=None)

    def save(self, commit=True):
        l = super(HwFarmNodeLockModelForm, self).save(commit=commit)

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


class HwFarmNodeLockModelAdmin(admin.ModelAdmin):
    form = HwFarmNodeLockModelForm


# This form is required to validate the color
class HwFarmNodeLockTypeForm(forms.ModelForm):

    class Meta:
        model = HwFarmNodeLockTypeModel
        fields = ('name', 'bg_color', 'fg_color')

        r = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')

        def is_hex_color(input_string):
            if r.search(input_string):
                return True
            return False

        def clean(self):
            if not is_hex_color(self.cleaned_data.get('bg_color')):
                raise forms.ValidationError("Background color is invalid, must be #000000")
            if not is_hex_color(self.cleaned_data.get('gg_color')):
                raise forms.ValidationError("Foreground color is invalid, must be #000000")

            return self.cleaned_data


class HwFarmNodeLockTypeAdmin(admin.ModelAdmin):
    form = HwFarmNodeLockTypeForm


admin.site.register(ProjectModel)
admin.site.register(JobModel)
admin.site.register(RegressionModel)
admin.site.register(ComparisonModel)
admin.site.register(TestGroupModel)
admin.site.register(EnvNodeModel)
admin.site.register(EnvNodeTypeModel)
admin.site.register(HwFarmNodeModel)
admin.site.register(HwFarmNodeLockModel, HwFarmNodeLockModelAdmin)
admin.site.register(HwFarmNodeLockTypeModel, HwFarmNodeLockTypeAdmin)
