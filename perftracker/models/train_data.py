from django.core.exceptions import SuspiciousOperation
from django.db import models


class PTChartFunctionType:
    NOT_SPECIFIED = 0
    CONST = 1
    LINEAR = 2
    LOGARITHM = 3
    SQUARE_OR_EXP = 4


CHART_FUNCTION_TYPES = (
    (PTChartFunctionType.NOT_SPECIFIED, 'Not specified'),
    (PTChartFunctionType.CONST, 'Constant'),
    (PTChartFunctionType.LINEAR, 'Linear'),
    (PTChartFunctionType.LOGARITHM, 'Logarithm'),
    (PTChartFunctionType.SQUARE_OR_EXP, 'Square or exp'),
)


class PTChartOutliers:
    ZERO = 0
    ONE = 1
    MANY = 2


CHART_OUTLIERS = (
    (PTChartOutliers.ZERO, '0'),
    (PTChartOutliers.ONE, '1'),
    (PTChartOutliers.MANY, 'Many'),
)


class PTChartOscillation:
    FALSE = 0
    TRUE = 1


CHART_OSCILLATION = (
    (PTChartOscillation.FALSE, 'False'),
    (PTChartOscillation.TRUE, 'True'),
)


class PTChartAnomaly:
    FALSE = 0
    TRUE = 1


CHART_ANOMALY = (
    (PTChartAnomaly.FALSE, 'False'),
    (PTChartAnomaly.TRUE, 'True'),
)


class PTTrainDataModel(models.Model):
    data = models.TextField()
    function_type = models.IntegerField(default=0, choices=CHART_FUNCTION_TYPES)
    outliers = models.IntegerField(default=0, choices=CHART_OUTLIERS)
    oscillation = models.IntegerField(default=0, choices=CHART_OSCILLATION)
    anomaly = models.IntegerField(default=0, choices=CHART_ANOMALY)

    @staticmethod
    def pt_validate_json(json_data):
        if 'data' not in json_data:
            raise SuspiciousOperation("Chart data is not specified: it must be 'data': <list>")
        if type(json_data['data']) is not list:
            raise SuspiciousOperation("Chart data must be a list: 'data': <list> ")
        for field in ['function_types', 'outliers', 'oscillation', 'anomaly']:
            if field not in json_data:
                raise SuspiciousOperation(f"{field} field is not specified: it must be '{field}': <int>")
