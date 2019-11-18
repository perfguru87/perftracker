import numpy as np
from scipy.optimize import curve_fit


def hyperbola(x, a, c):
    return a / x + c


def get_coordinates(s_data, eps=1e3):
    x_array, y_array, fails = [], [], []
    for point in s_data:
        try:
            x_array.append(float(point[0]))
            y_array.append(float(point[1]))
        except KeyError:
            x_array.append(float(point['value'][0]))
            y_array.append(float(point['value'][1]))
            fails.append(point['value'])
            continue
        except TypeError:
            break

    x_array, y_array = np.array(x_array), np.array(y_array)
    max_x, max_y = np.max(x_array), np.max(y_array)

    for x, y in zip(x_array, y_array):
        x /= max_x if abs(max_x) > eps else 1
        x /= max_y if abs(max_y) > eps else 1

    return x_array, y_array, fails


def get_thresholds(categories, values):
    categories = ['min'] + [c for c in categories] + ['max']
    return {category: threshold for (category, threshold) in
            zip(categories, np.linspace(min(values), max(values), len(categories)))}


def pt_comparison_series_analyze(data):
    round_to = 3
    eps = 1e-3

    # coefficient belongs to (0, 1) for little outliers detection
    # coefficient belongs to (1, +inf) for rough outliers detection
    # default value is 1.
    outlier_coefficient = 1.

    mse_lin_values, mse_hyp_values, rv = [], [], {}

    for s_id, s_data in data.items():
        x_array, y_array, fails = get_coordinates(s_data)

        mean_y, max_y, std_y = np.mean(y_array), np.max(y_array), np.std(y_array)

        # desired equation: y = a / x + c
        x_array[0] += eps if abs(x_array[0]) < eps else 0

        optimal_parameters, _ = curve_fit(hyperbola, x_array, y_array)
        mse_hyp_absolute = np.square(np.subtract(y_array, hyperbola(x_array, *optimal_parameters))).mean()
        mse_hyp = mse_hyp_absolute / (max_y ** 2) if abs(max_y) > eps else mse_hyp_absolute
        mse_hyp_values.append(mse_hyp)

        # desired equation: y = k * x + b
        k, b = np.linalg.lstsq(np.vstack([x_array, np.ones(len(x_array))]).T, y_array, rcond=None)[0]
        mse_lin_absolute = np.square(np.subtract(y_array, [k * x + b for x in x_array])).mean()
        mse_lin = mse_lin_absolute / (max_y ** 2) if abs(max_y) > eps else mse_lin_absolute
        mse_lin_values.append(mse_lin)

        outliers = [x_array[i] for i, y in enumerate(y_array) if abs(y - mean_y) >= 3 * std_y * outlier_coefficient]

        rv[s_id] = {
            'incline': k,
            'mse_lin': mse_lin,
            'mse_hyp': mse_hyp,
            'first_is_max': int(max_y == y_array[0])
        }

        if outliers:
            rv[s_id]['outliers'] = [round(outlier, round_to) for outlier in outliers]

        if fails:
            rv[s_id]['fails'] = fails

    thresholds = get_thresholds(('low', 'med', 'high'), mse_lin_values + mse_hyp_values)

    for s_data in rv.values():
        if s_data['incline'] < 0 and s_data.pop('first_is_max', False) and s_data['mse_lin'] > s_data['mse_hyp']:
            function_type = 'hyp'
        else:
            function_type = 'lin'

        if s_data[f'mse_{function_type}'] < thresholds['low']:
            confidence_level = 'high'
        elif thresholds['low'] < s_data[f'mse_{function_type}'] < thresholds['med']:
            confidence_level = 'med'
        else:
            confidence_level = 'low'

        s_data['type'] = function_type
        s_data['confidence'] = confidence_level

        for key in s_data.keys():
            if isinstance(s_data[key], float):
                s_data[key] = round(s_data[key], round_to)

    return rv
