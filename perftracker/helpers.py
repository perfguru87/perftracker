import os
import uuid
import json

from rest_framework import serializers
from django.utils.dateparse import parse_datetime


class PTDurationField(serializers.DurationField):
    def to_representation(self, value):
        return int(round(value.total_seconds()))

def pt_round_float(val):
    abs_val = abs(float(val))

    if abs_val > 100:
        return int(round(val))
    elif abs_val < 0.00000001:
        return 0

    thr = 100
    prec = 0
    while abs_val < thr:
        prec += 1
        thr /= 10.0
    fmt = "%." + str(prec) + "f"
    return float(fmt % (val))


def pt_float2human(val, MK=False):
    if str(val) == "":
        return 0

    if not MK:
        return pt_round_float(val)

    abs_val = abs(float(val))
    if abs_val < 1000:
        return pt_round_float(val)

    g = 1000000000.0
    m = 1000000.0
    k = 1000.0

    suffix = ""
    if abs_val >= g:
        suffix = "G"
        val /= g
    elif abs_val >= m:
        suffix = "M"
        val /= m
    elif abs_val >= k:
        suffix = "K"
        val /= k

    return str(pt_round_float(val)) + suffix


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


def pt_is_valid_uuid(uuid_to_test):
    try:
        uuid_to_test = uuid_to_test.lower()
    except:
        return False

    try:
        uuid_obj = uuid.UUID(uuid_to_test)
    except ValueError:
        return False

    return str(uuid_obj) == uuid_to_test


def _pt_cut_common_sfx(lines, separators=None):
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

def pt_cut_common_sfx(lines, separators=None):
    common_sfx, prefixes = _pt_cut_common_sfx(lines, separators)
    numeric = {}
    for orig_idx, p in enumerate(prefixes):
        try:
            numeric[float(p)] = orig_idx
        except ValueError:
            break
    if len(numeric) == len(lines):  # all unique prefixes are numeric
        num_ordered = sorted(numeric.items())
        order = [orig_idx for (_, orig_idx) in num_ordered]
        def str2num(s):
            return float(s) if "." in s else int(s)
        prefixes = [str2num(prefixes[orig_idx]) for orig_idx in order]
    else:
        order = list(range(len(lines)))
    line2seqnum = {}
    for n in range(0, len(lines)):
        line2seqnum[lines[order[n]]] = n
    return common_sfx, prefixes, line2seqnum


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
                self._raise("%s: fetching '%s' key of type '%s', got unexpected: %s (of type '%s')" % (self.obj_name, key, type_str, v, type(v)))
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
        def _bool(v):
            return v in ("True", "true", True, "Yes", "yes", "y", 1)
        return self._get_value(key, defval, require, _bool, 'boolean')

    def get_list(self, key, defval=None, require=False):
        return self._get_structure(key, [] if defval is None else defval, require, list)

    def get_dict(self, key, defval=None, require=False):
        return self._get_structure(key, {} if defval is None else defval, require, dict)

    def get_uuid(self, key, defval=None, require=False):
        v = self._get_value(key, defval, require, str, 'uuid')
        if v:
            v = v.lower()
        if v and not pt_is_valid_uuid(v):
            self._raise("%s: '%s' key value '%s' is not a valid UUID1" % (self.obj_name, key, v))
        return v
