import copy
import re

from django.core.exceptions import SuspiciousOperation, ValidationError
from django.db import models
from rest_framework import serializers
from django.conf import settings


class HwChassisModel(models.Model):
    model      = models.CharField(max_length=64, help_text="Dell Rx730, Azure D3v2", null=True, blank=True, db_index=True)
    hw_uuid    = models.CharField(max_length=64, help_text="80A21512-79BA-12C3-0083-E12089140FA2", null=True, blank=True, db_index=True)
    serial_num = models.CharField(max_length=64, help_text="123456-789", null=True, blank=True)
    numa_nodes = models.IntegerField(help_text='Number of numa nodes', null=True, blank=True)
    ram_info   = models.CharField(max_length=64, help_text="DDR3 @ 1333MHz", null=True, blank=True)
    cpu_info   = models.CharField(max_length=128, help_text="Intel Xeon Processor E5450 12M Cache, 3.00 GHz, 1333 MHz FSB", blank=True)

    class Meta:
        verbose_name = "Host"
        verbose_name_plural = "Hosts"

    @staticmethod
    def pt_get_by_json(json, parent=None):
        """ Find (or automatically create) the object by json key:values"""
        _j = {}
        o = HwChassisModel()
        for f in HwChassisModel._meta.get_fields():
            if f.name in json and f.validate(json[f.name], o):
                _j[f.name] = json[f.name]

        if not _j:
            return None

        try:
            return HwChassisModel.objects.filter(**_j)[0]  # take the last one
        except (IndexError, HwChassisModel.DoesNotExist):
            pass

        for key in ('hw_uuid', 'serial_num'):
            if key not in _j or not _j[key]:
                continue

            f = HwChassisModel._meta.get_field(key)
            try:
                f.validate(_j[key], o)
            except ValidationError as e:
                raise SuspiciousOperation(e)

            try:
                return HwChassisModel.objects.get(**{key: _j[key]})
            except HwChassisModel.DoesNotExist:
                continue

        return None


class HwChassisSerializer(serializers.ModelSerializer):
    class Meta:
        model = HwChassisModel
        fields = ('model', 'hw_uuid', 'serial_num', 'numa_nodes', 'ram_info', 'cpu_info')


class EnvNodeTypeModel(models.Model):
    name       = models.CharField(max_length=64, db_index=True, help_text="Host, KVM VM, k8s pod, docker image, cluster")
    css        = models.CharField(max_length=256, help_text="glyphicon glyphicon-tasks", blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Environment type"
        verbose_name_plural = "Environment types"

    @staticmethod
    def pt_get_by_json(json):
        if 'node_type' not in json:
            raise SuspiciousOperation("'node_type' is not set in: %s" % json)
        try:
            return EnvNodeTypeModel.objects.get(name=json['node_type'])
        except EnvNodeTypeModel.DoesNotExist:
            t = EnvNodeTypeModel(name=json['node_type'])
            t.save()
            return t


class EnvNodeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvNodeTypeModel
        fields = ('name', )


class EnvNodeModel(models.Model):
    name       = models.CharField(max_length=128, help_text="server1", db_index=True)
    uuid       = models.UUIDField(help_text="env node uuid", db_index=True)
    version    = models.CharField(max_length=128, help_text="CentOS7, 3.10.0-693.17.1.el7.x86_64", db_index=True, blank=True)
    node_type  = models.ForeignKey(EnvNodeTypeModel, blank=True, on_delete=models.CASCADE, null=True)
    ip         = models.CharField(max_length=32, help_text="192.168.0.1", blank=True, db_index=True)
    hostname   = models.CharField(max_length=256, help_text="server1.intranet.localdomain", blank=True, db_index=True)

    params     = models.CharField(max_length=512, help_text="DMA disabled", null=True, blank=True)
    cpus       = models.IntegerField(help_text="32", null=True, blank=True)
    cpus_topology = models.CharField(max_length=128, help_text="32 (2S x 8C x 2T)", null=True, blank=True)
    ram_mb     = models.IntegerField(help_text="131072", null=True, blank=True)
    disk_gb    = models.IntegerField(help_text="4096", null=True, blank=True)

    links      = models.CharField(max_length=512, help_text="{'grafana': 'http://192.168.100.1/grafana'}", blank=True)

    parent     = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE, related_name='children')
    hw_chassis = models.ForeignKey(HwChassisModel, blank=True, null=True, on_delete=models.CASCADE, default=None)
    job        = models.ForeignKey('perftracker.JobModel', help_text="Job", on_delete=models.CASCADE, related_name='env_nodes')

    @property
    def display_name(self):
        if not hasattr(settings, 'ENV_NODE_DISPLAY_NAME_RE'):
            return self.name
        return re.sub(*settings.ENV_NODE_DISPLAY_NAME_RE, self.name)

    def __str__(self):
        ret = "%s %s %s" % (self.node_type, self.name, self.version)
        if self.params:
            ret += " (%s)" % self.params
        return ret

    @staticmethod
    def pt_find_env_nodes_for_update(job, json):
        # performance optimization to avoid full nodes rewrite on each job results upload
        try:
            db_uuid2node = set([n.uuid for n in EnvNodeModel.objects.filter(job=job)])
        except EnvNodeModel.DoesNotExist:
            db_uuid2node = set()

        nodes_from_json = []
        for j in json:
            EnvNodeModel._pt_scan_env_nodes_from_json(j, nodes_from_json, None)
        if db_uuid2node == set([n['uuid'] for n in nodes_from_json]):
            return None

        return nodes_from_json

    def _pt_scan_env_nodes_from_json(json, result_nodes_list, parent_uuid):
        _j = copy.copy(json)
        if 'children' in _j:
            _j.pop('children')
        if 'uuid' not in _j:
            raise SuspiciousOperation("'uuid' is not set in: %s" % _j)
        _j['parent_uuid'] = parent_uuid
        result_nodes_list.append(_j)
        for child in json.get('children', []):
            EnvNodeModel._pt_scan_env_nodes_from_json(child, result_nodes_list, _j['uuid'])

    @staticmethod
    def pt_get_by_uuid(uuid, job):
        try:
            return EnvNodeModel.objects.get(uuid=uuid)
        except EnvNodeModel.DoesNotExist:
            t = EnvNodeModel(uuid=uuid, job=job)
            t.save()
            return t


class EnvNodeUploadSerializer(serializers.ModelSerializer):

    def __init__(self, *args, job=None, **kwargs):
        super(EnvNodeUploadSerializer, self).__init__(*args, **kwargs)

        if hasattr(self, 'initial_data'):
            self.initial_data['job'] = job.id

            if 'parent_uuid' in self.initial_data:
                uuid = self.initial_data.pop('parent_uuid')
                if uuid:
                    parent = EnvNodeModel.pt_get_by_uuid(uuid, job)
                    self.initial_data['parent'] = parent.id if parent else None
                else:
                    self.fields.pop('parent')
                    self.initial_data['parent'] = None

            if 'node_type' in self.initial_data:
                env_node_type = EnvNodeTypeModel.pt_get_by_json(self.initial_data)
                self.initial_data['node_type'] = env_node_type.id if env_node_type else None

            if 'hw_uuid' in self.initial_data:
                hw_chassis = HwChassisModel.pt_get_by_json(self.initial_data)
                self.initial_data['hw_chassis'] = hw_chassis.id if hw_chassis else None

    class Meta:
        model = EnvNodeModel
        fields = ('name', 'uuid', 'version', 'node_type', 'ip', 'hostname', 'params',
                  'cpus', 'cpus_topology', 'ram_mb', 'disk_gb',
                  'links', 'parent', 'job', 'hw_chassis')


class EnvNodeSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvNodeModel
        fields = ('name', 'display_name', 'id')


class RecursiveField(serializers.Serializer):
    def to_representation(self, data):
        serializer = self.parent.parent.__class__(data, context=self.context)
        return serializer.data


class EnvNodeNestedSerializer(serializers.ModelSerializer):
    children = RecursiveField(many=True)
    node_type = EnvNodeTypeSerializer()
    hw_chassis = HwChassisSerializer()

    class Meta:
        model = EnvNodeModel
        fields = ('name', 'display_name', 'id', 'uuid', 'version', 'node_type', 'ip', 'hostname', 'params',
                  'cpus', 'cpus_topology', 'ram_mb', 'disk_gb',
                  'links', 'parent', 'job', 'hw_chassis', 'children')
