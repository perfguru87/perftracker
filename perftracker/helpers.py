import uuid

from rest_framework import serializers


class ptDurationField(serializers.DurationField):
    def to_representation(self, value):
        # get rid of microseconds
        v = super().to_representation(value)
        return ':'.join(v.split(':')[0:2])


def pt_float2human(value, MK=False):
    if str(value) == "":
        return "0"
    value = float(value)
    if MK and value > 100000000:
        return str(int(round(value / 1000000))) + "M"
    elif MK and value > 100000:
        return str(int(round(value / 1000))) + "K"
    elif value > 100:
        return str(int(round(value)))
    elif value < 0.00000001:
        return "0"
    else:
        thr = 100
        prec = 0
        while value < thr:
            prec += 1
            thr /= 10.0
        fmt = "%." + str(prec) + "f"
        return float(fmt % (value))


class ptRoundedFloatField(serializers.FloatField):
    def to_representation(self, value):
        return pt_float2human(value)


class ptRoundedFloatMKField(serializers.FloatField):
    def to_representation(self, value):
        return pt_float2human(value, MK=True)


def pt_dur2str(duration):
    days = duration.days
    seconds = duration.seconds

    minutes = seconds // 60
    hours = minutes // 60
    minutes = minutes % 60

    ret = "{:02d}:{:02d}".format(hours, minutes)
    if days:
        return "%dd %s" % (days, ret)
    return ret


def pt_is_valid_uuid(uuid_to_test, version=1):
    try:
        uuid_obj = uuid.UUID(uuid_to_test, version=version)
    except ValueError:
        return False

    return str(uuid_obj) == uuid_to_test
