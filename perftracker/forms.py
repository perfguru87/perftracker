from django.forms import ModelForm
from django import forms
from perftracker.models.comparison import ComparisonModel, CMP_CHARTS, CMP_TABLES, CMP_TESTS, CMP_VALUES
from perftracker.models.hw_farm_node_lock import HwFarmNodeLockModel

class PTCmpDialogForm(ModelForm):
    class Meta:
        model = ComparisonModel
        fields = ['title', 'charts_type', 'tables_type', 'tests_type', 'values_type']


class PTHwFarmNodeLockForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(PTHwFarmNodeLockForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            self.fields['begin'].widget.attrs['readonly'] = True

    def clean_begin(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            return instance.begin
        else:
            return self.cleaned_data['begin']

    def clean_end(self):
        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            return instance.end
        else:
            return self.cleaned_data['end']

    class Meta:
        model = HwFarmNodeLockModel
        fields = ['title', 'begin', 'end', 'hw_nodes', 'planned_dur_hrs']
        exclude = ['end']


class PTJobUploadForm(forms.Form):
    def validate_json_ext(value):
        if not value.name.endswith('.json'):
            raise ValidationError(u'Only *.json file can be uploaded')

    content_type = "text/plain"
    job_title = forms.CharField(max_length=256, label='Tests run title', required=False)
    job_file = forms.FileField(label='perftracker job results (*.json)', validators=[validate_json_ext], required=False)
