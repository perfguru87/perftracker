import uuid
import os

from rest_framework import serializers


class ptDurationField(serializers.DurationField):
    def to_representation(self, value):
        # get rid of microseconds
        v = super().to_representation(value)
        return ':'.join(v.split(':')[0:2])


def pt_float2human(value, MK=False):
    if str(value) == "":
        return "0"
    val = abs(float(value))
    if MK and val > 100000000:
        return str(int(round(value / 1000000))) + "M"
    elif MK and val > 100000:
        return str(int(round(value / 1000))) + "K"
    elif val > 100:
        return str(int(round(value)))
    elif val < 0.00000001:
        return "0"
    else:
        thr = 100
        prec = 0
        while val < thr:
            prec += 1
            thr /= 10.0
        fmt = "%." + str(prec) + "f"
        return float(fmt % (val)) * (1 if value > 0 else -1)


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


def pt_cut_common_sfx(lines, separators=None):
    if separators is None:
        separators = (' ', ';', '-', ',', '.')
    common_sfx = os.path.commonprefix([s[::-1] for s in lines])[::-1]

    # try to find separator...
    while common_sfx and not common_sfx[0] in separators:
        common_sfx = common_sfx[1:]

    # trim it...
    if common_sfx:
        sep = common_sfx[0]
        while common_sfx and common_sfx[0] == sep:
            common_sfx = common_sfx[1:]

    # and cut it...
    ret = []
    length = len(common_sfx)
    if not length:
        return common_sfx, lines

    for line in lines:
        l = line[:-length]
        if len(l):
            while l[-1] in separators:
                l = l[:-1]
        ret.append(l)
    return common_sfx, ret
