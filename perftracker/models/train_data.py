from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.http import HttpResponseBadRequest


class PTChartFunctionType:
    NOT_SPECIFIED = 0
    CONST = 1
    LINEAR = 2
    LOGARITHM = 3
    SQUARE_OR_EXP = 4
    HYPERBOLA = 5


CHART_FUNCTION_TYPE = (
    (PTChartFunctionType.NOT_SPECIFIED, 'Not specified'),
    (PTChartFunctionType.CONST, 'Constant'),
    (PTChartFunctionType.LINEAR, 'Linear'),
    (PTChartFunctionType.LOGARITHM, 'Logarithm'),
    (PTChartFunctionType.SQUARE_OR_EXP, 'Square or exp'),
    (PTChartFunctionType.HYPERBOLA, 'Hyperbola'),
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


class PTChartDeviation:
    FALSE = 0
    TRUE = 1


CHART_DEVIATION = (
    (PTChartDeviation.FALSE, 'False'),
    (PTChartDeviation.TRUE, 'True'),
)


class PTChartAnomaly:
    FALSE = 0
    TRUE = 1


CHART_ANOMALY = (
    (PTChartAnomaly.FALSE, 'False'),
    (PTChartAnomaly.TRUE, 'True'),
)


class PTChartIsOk:
    FALSE = 0
    TRUE = 1


CHART_IS_OK = (
    (PTChartIsOk.FALSE, 'False'),
    (PTChartIsOk.TRUE, 'True'),
)


class TrainDataModel(models.Model):
    data = models.TextField(null=False)
    section_id = models.IntegerField(null=False, db_index=True)
    job_id = models.IntegerField(null=False, db_index=True)
    less_better = models.TextField(null=False)
    chart_is_ok = models.IntegerField(blank=False, default=None, choices=CHART_IS_OK)
    fails = models.TextField(null=True)
    function_type = models.IntegerField(null=True, choices=CHART_FUNCTION_TYPE)
    outliers = models.IntegerField(null=True, choices=CHART_OUTLIERS)
    deviation = models.IntegerField(null=True, choices=CHART_DEVIATION)
    anomaly = models.IntegerField(null=True, choices=CHART_ANOMALY)

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

        require_all_fields = False
        required_fields = ['less_better', 'chart_is_ok']
        if require_all_fields:
            required_fields += ['function_type', 'outliers', 'deviation', 'anomaly']

        for field in required_fields:
            if field not in json_data:
                raise SuspiciousOperation(f'{field} field is not specified: it must be "{field}": <int>')
