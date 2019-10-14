from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.http import HttpResponseBadRequest


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


class TrainDataModel(models.Model):
    data = models.TextField()
    fails = models.TextField(null=True, blank=True)
    less_better = models.TextField(default='_')
    function_type = models.IntegerField(default=0, choices=CHART_FUNCTION_TYPES)
    outliers = models.IntegerField(default=0, choices=CHART_OUTLIERS)
    oscillation = models.IntegerField(default=0, choices=CHART_OSCILLATION)
    anomaly = models.IntegerField(default=0, choices=CHART_ANOMALY)

    @staticmethod
    def pt_format_data(data):
        serie, fails = [], []
        for point in data['serie']:
            try:
                serie.append([float(point[0]), float(point[1])])
            except KeyError as e:
                if isinstance(point, dict):
                    serie.append(point['value'])
                    fails.append(point['value'])
                else:
                    return HttpResponseBadRequest(f'Wrong data; exception: {type(e).__name__}')
            except Exception as e:
                return HttpResponseBadRequest(f'Wrong data; exception: {type(e).__name__}')

        serie_str = '|'.join([f'{x};{y}' for x, y in serie])
        fails_str = '|'.join([f'{x};{y}' for x, y in fails])

        less_better = data['less_better']
        if isinstance(less_better, int):
            less_better = str(less_better)
        elif isinstance(less_better, list):
            less_better = '|'.join([str(i) for i in less_better])

        return serie_str, fails_str or None, less_better

    @staticmethod
    def pt_validate_json(json_data):
        serie = json_data.get('serie')
        if not serie:
            raise SuspiciousOperation('Chart serie is not specified: it must be "data": <list>')

        if not isinstance(serie, list):
            raise SuspiciousOperation('Chart serie must be a list: "serie": <list>')

        try:
            _ = [(float(point[0]), float(point[1])) for point in serie]
        except KeyError:
            pass
        except Exception as e:
            raise SuspiciousOperation(
                f'Serie must be float lists: "point": <[float, float]>; exception: {type(e).__name__}'
            )

        for field in ('function_types', 'outliers', 'oscillation', 'anomaly', 'less_better'):
            if field not in json_data:
                raise SuspiciousOperation(f'{field} field is not specified: it must be "{field}": <int>')
