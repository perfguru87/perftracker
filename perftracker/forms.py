from django.forms import ModelForm
from perftracker.models.comparison import ComparisonModel, CMP_CHARTS, CMP_TABLES, CMP_TESTS, CMP_VALUES


class ptCmpDialogForm(ModelForm):
    class Meta:
        model = ComparisonModel
        fields = ['title', 'charts_type', 'tables_type', 'tests_type', 'values_type']
