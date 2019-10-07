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
    function_type = models.IntegerField(default=0, choices=CHART_FUNCTION_TYPES)
    outliers = models.IntegerField(default=0, choices=CHART_OUTLIERS)
    oscillation = models.IntegerField(default=0, choices=CHART_OSCILLATION)
    anomaly = models.IntegerField(default=0, choices=CHART_ANOMALY)

    @staticmethod
    def pt_format_data(data):
        points, fails = [], []
        for point in data['points']:
            try:
                points.append([float(point[0]), float(point[1])])
            except KeyError:
                if isinstance(point, dict):
                    points.append(point['value'])
                    fails.append(point['value'])
                else:
                    return HttpResponseBadRequest('Wrong data')
            except Exception as e:
                return HttpResponseBadRequest(f'Wrong data; exception: {type(e).__name__}')

        def pt_list2str(lst):
            return '|'.join([f'{x};{y}' for x, y in lst])

        return pt_list2str(points), pt_list2str(fails) or None

    @staticmethod
    def pt_validate_json(json_data):
        points = json_data.get('points')
        if not points:
            raise SuspiciousOperation('Chart points are not specified: it must be "data": <list>')

        if not isinstance(points, list):
            raise SuspiciousOperation('Chart points must be a list: "points": <list>')

        try:
            _ = [(float(point[0]), float(point[1])) for point in points]
        except KeyError:
            pass
        except Exception as e:
            raise SuspiciousOperation(
                f'Points must be float lists: "point": <[float, float]>; exception: {type(e).__name__}'
            )

        for field in ('function_types', 'outliers', 'oscillation', 'anomaly'):
            if field not in json_data:
                raise SuspiciousOperation(f'{field} field is not specified: it must be "{field}": <int>')
