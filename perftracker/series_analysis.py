import numpy as np


def pt_comparison_series_analyze(data):
    round_to = 3
    mse_categories = ('low', 'med', 'high')
    mse_categories_amount = len(mse_categories)
    mse_values = []
    rv = {}

    # coefficient belongs to (0, 1) for little outliers detection
    # coefficient belongs to (1, +inf) for rough outliers detection
    # default value is 1.
    outlier_coefficient = 1.

    for s_id, s_data in data.items():
        try:
            # point(x, y)
            x_array = np.array([float(point[0]) for point in s_data])
            y_array = np.array([float(point[1]) for point in s_data])
        except (TypeError, KeyError):
            continue

        # desired equation: y = k * x + b
        k, b = np.linalg.lstsq(np.vstack([x_array, np.ones(len(x_array))]).T, y_array, rcond=None)[0]

        mean_y = y_array.mean()
        std_y = np.std(y_array)

        # mse <=> normalized mean squared error
        mse_absolute = np.square(np.subtract(y_array, [k * x + b for x in x_array])).mean()
        mse = round(mse_absolute / (mean_y ** 2), round_to) if mean_y else 0
        mse_values.append(mse)

        outliers = [x_array[i] for i, y in enumerate(y_array) if abs(y - mean_y) >= 3 * std_y * outlier_coefficient]

        rv[s_id] = {
            'incline': round(k, round_to),
            'mean_counted': round(b, round_to),
            'mse_absolute': round(mse_absolute, round_to),
            'mean_true': round(mean_y, round_to),
            'mse': mse,
            'outliers': outliers,
        }

    mse_values.sort()
    boundaries = [mse_values[int(len(mse_values) / mse_categories_amount) * i] for i in range(1, mse_categories_amount)]
    boundaries.append(mse_values[-1])

    for s_data in rv.values():
        for category in range(mse_categories_amount):
            if s_data['mse'] <= boundaries[category]:
                s_data['mse_category'] = mse_categories[category]
                break

    return rv
