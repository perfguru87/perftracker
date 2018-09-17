import os
import uuid
import json

from rest_framework import serializers
from django.utils.dateparse import parse_datetime


class PTDurationField(serializers.DurationField):
    def to_representation(self, value):
        return int(round(value.total_seconds()))


def pt_float2human(value, MK=False):
    if str(value) == "":
        return 0
    val = abs(float(value))
    if MK and val > 100000000:
        return str(int(round(value / 1000000))) + "M"
    elif MK and val > 100000:
        return str(int(round(value / 1000))) + "K"
    elif val > 100:
        return int(round(value))
    elif val < 0.00000001:
        return 0
    else:
        thr = 100
        prec = 0
        while val < thr:
            prec += 1
            thr /= 10.0
        fmt = "%." + str(prec) + "f"
        return float(fmt % (val)) * (1 if value > 0 else -1)


class PTRoundedFloatField(serializers.FloatField):
    def to_representation(self, value):
        return pt_float2human(value)


class PTRoundedFloatMKField(serializers.FloatField):
    def to_representation(self, value):
        return pt_float2human(value, MK=True)


def pt_dur2str(duration):
    days = duration.days
    seconds = duration.seconds

    minutes = seconds // 60
    hours = minutes // 60
    minutes = minutes % 60

    ret = "{:02d}:{:02d}".format(hours, minutes)
    if days > 1:
        return "%d days %s" % (days, ret)
    elif days == 1:
        return "%d day %s" % (days, ret)
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


class PTJson:
    def __init__(self, json_data, obj_name="json", exception_type=None, known_nones=None):
        self.json_data = json_data
        self.obj_name = obj_name
        self.exception_type = exception_type
        self.known_nones = known_nones if known_nones else (None, 'null', 'None')

    def get(self, key, defval=None):
        return self.json_data.get(key, defval)

    def _raise(self, msg):
        if self.exception_type:
            raise self.exception_type(msg)

    def _get_value(self, key, defval, require, cb, type_str):
        v = self.json_data.get(key, defval)
        if v in self.known_nones:
            ret = defval
        else:
            try:
                ret = cb(v)
            except TypeError as e:
                self._raise("%s: key '%s' type must be '%s', got '%s'; %s" % (self.obj_name, key, type(v), type(v), str(e)))
                ret = defval
            except ValueError as e:
                self._raise("%s: fetching '%s' key of type '%s', got unexpected: %s" % (self.obj_name, key, type(v), v))
                ret = defval

        if ret == defval and require:
            self._raise("%s: key '%s' is not found" % (self.obj_name, key))
        return ret

    def _get_structure(self, key, defval, require, key_type):
        if defval is None:
            defval = []

        v = self.json_data.get(key, None)
        if v is None:
            if require:
                self._raise("%s: key '%s' is not found" % (self.obj_name, key))
            return defval
        elif type(v) is key_type:
            return self._get_value(key, defval, require, key_type, 'json')
        else:
            return self._get_value(key, str(defval), require, json.loads, 'json')

    def get_float(self, key, defval=0, require=False):
        return self._get_value(key, defval, require, float, 'float')

    def get_int(self, key, defval=0, require=False):
        return self._get_value(key, defval, require, int, 'integer')

    def get_str(self, key, defval="", require=False):
        return self._get_value(key, defval, require, str, 'string')

    def get_datetime(self, key, defval=None, require=False):
        return self._get_value(key, defval, require, parse_datetime, 'datetime')

    def get_bool(self, key, defval=False, require=False):
        return self._get_value(key, defval, require, bool, 'boolean')

    def get_list(self, key, defval=None, require=False):
        return self._get_structure(key, [] if defval is None else defval, require, list)

    def get_dict(self, key, defval=None, require=False):
        return self._get_structure(key, {} if defval is None else defval, require, dict)

    def get_uuid(self, key, defval=None, require=False):
        v = self._get_value(key, defval, require, str, 'uuid')

        if v and not pt_is_valid_uuid(v):
            self._raise("%s: '%s' key value '%s' is not a valid UUID1" % (self.obj_name, key, v))
        return v
