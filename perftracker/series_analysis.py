import numpy as np
from scipy.optimize import curve_fit


def hyperbola(x, a, c):
    return a / x + c


def get_coordinates(s_data):
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
    return np.array(x_array), np.array(y_array), fails


def pt_comparison_series_analyze(data):
    round_to = 3

    mse_lin_categories = ('low', 'med', 'high')
    mse_lin_categories_amount = len(mse_lin_categories)
    mse_lin_values = []

    mse_hyp_values = []
    hyp_threshold = 5.

    rv = {}

    # coefficient belongs to (0, 1) for little outliers detection
    # coefficient belongs to (1, +inf) for rough outliers detection
    # default value is 1.
    outlier_coefficient = 1.

    for s_id, s_data in data.items():
        x_array, y_array, fails = get_coordinates(s_data)

        mean_y = y_array.mean()
        std_y = np.std(y_array)

        # desired equation: y = a / x + c
        x_arr = x_array[1:] if x_array[0] == 0 else x_array
        y_arr = y_array[1:] if x_array[0] == 0 else y_array

        optimal_parameters, _ = curve_fit(hyperbola, x_arr, y_arr)
        mse_hyp = np.square(np.subtract(y_arr, hyperbola(x_arr, *optimal_parameters))).mean()
        mse_hyp_values.append(mse_hyp)

        # desired equation: y = k * x + b
        k, b = np.linalg.lstsq(np.vstack([x_array, np.ones(len(x_array))]).T, y_array, rcond=None)[0]

        # mse <=> normalized mean squared error
        mse_lin_absolute = np.square(np.subtract(y_array, [k * x + b for x in x_array])).mean()
        mse_lin = mse_lin_absolute / (mean_y ** 2) if mean_y else 0
        mse_lin_values.append(mse_lin)

        outliers = [x_array[i] for i, y in enumerate(y_array) if abs(y - mean_y) >= 3 * std_y * outlier_coefficient]

        rv[s_id] = {
            'incline': round(k, round_to),
            'mse_lin': round(mse_lin, round_to),
            'mse_hyp': round(mse_hyp, round_to),
        }

        if outliers:
            rv[s_id]['outliers'] = [round(outlier, round_to) for outlier in outliers]
        if fails:
            rv[s_id]['fails'] = fails

    mse_lin_values.sort()
    boundaries = [mse_lin_values[int(len(mse_lin_values) / mse_lin_categories_amount) * i]
                  for i in range(1, mse_lin_categories_amount)]
    boundaries.append(mse_lin_values[-1])

    for s_data in rv.values():
        s_data['hyperbolic'] = int(s_data.get('mse_hyp') < hyp_threshold)
        mse_lin = s_data.get('mse_lin')
        for category in range(mse_lin_categories_amount):
            if mse_lin <= boundaries[category]:
                s_data['linear'] = int(mse_lin_categories[category] == 'low')
                break

    return rv
