from django.db import models
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.core.exceptions import SuspiciousOperation

from rest_framework import serializers

from perftracker.helpers import ptDurationField
from perftracker.models.project import ProjectModel


class HwFarmNodeLockModel(models.Model):
    title           = models.CharField(blank=True, max_length=128, help_text="My product perf job #123")
    owner           = models.CharField(blank=True, max_length=64, help_text="Jenkins")

    color_rgb       = models.CharField(blank=True, max_length=6, help_text="003399")
    begin           = models.DateTimeField(default=timezone.now, help_text="2018-07-01 12:21:10")
    end             = models.DateTimeField(null=True, blank=True, help_text="2018-07-01 18:03:45")

    manual          = models.BooleanField(help_text="True means it was manually locked", default=False)
    deleted         = models.BooleanField(help_text="Lock deleted", default=False)

    planned_dur_hrs = models.DurationField(default=24, help_text="Planned lock duration (hours)")

    def __str__(self):
        return "#%d, %s" % (self.id, self.name)

    class Meta:
        verbose_name = "Hw Node Lock"
        verbose_name_plural = "Hw Node Locks"


class HwFarmNodeModel(models.Model):
    name            = models.CharField(max_length=64, help_text="s1")
    hostname        = models.CharField(max_length=256, help_text="s1.perfteam.example.com")
    ip              = models.CharField(blank=True, max_length=64, help_text="10.0.0.1")
    projects        = models.ManyToManyField(ProjectModel, related_name="hw_node_projects", help_text="Project")
    hidden          = models.BooleanField(help_text="Set to True to hide from the nodes list", default=False)
    order           = models.IntegerField(blank=True, default=10, help_text="Node order on the dashboard")

    ssh_user        = models.CharField(blank=True, max_length=64, help_text="user")
    ssh_passwd      = models.CharField(blank=True, max_length=64, help_text="passwd")
    ipmi_ip         = models.CharField(blank=True, max_length=64,  help_text="10.0.0.1")
    ipmi_user       = models.CharField(blank=True, max_length=64,  help_text="user")
    ipmi_passwd     = models.CharField(blank=True, max_length=64,  help_text="passwd")

    locked_by       = models.ForeignKey(HwFarmNodeLockModel, null=True, blank=True, help_text="Host is locked by given lock", on_delete=models.CASCADE)

    icon_url        = models.CharField(blank=True, max_length=512, help_text="HW node icon URL")
    dashboard       = models.CharField(blank=True, max_length=512, help_text="Node dashboard link (e.g. Grafana)")
    details_url     = models.CharField(blank=True, max_length=512, help_text="Node details URL")
    notes           = models.CharField(blank=True, max_length=512, help_text="HW node notes")
    description     = models.TextField(blank=True, help_text="HW node description")

    inv_id          = models.CharField(blank=True, max_length=64,  help_text="Inventory ID")
    phys_location   = models.CharField(blank=True, max_length=128, help_text="4-2-1-15")
    vendor          = models.CharField(blank=True, max_length=64,  help_text="HP")
    model           = models.CharField(blank=True, max_length=128, help_text="Proliant DL380")
    os              = models.CharField(blank=True, max_length=128, help_text="ESXi")

    numa_nodes      = models.IntegerField(blank=True, null=True, help_text="2")

    cpus_count      = models.IntegerField(blank=True, null=True, help_text="16")
    ram_gb          = models.FloatField(blank=True, null=True, help_text="32")
    network_gbs     = models.FloatField(blank=True, null=True, help_text="10")
    storage_tb      = models.FloatField(blank=True, null=True, help_text="3.2")

    cpu_info        = models.CharField(blank=True, max_length=64,  help_text="16 (2Sx4Cx2T) @ 2.5GHz, Intel E5450 v2")
    ram_info        = models.CharField(blank=True, max_length=64,  help_text="32G (1333 GHz)")
    network_info    = models.CharField(blank=True, max_length=64,  help_text="10GBit X710-DA2")
    storage_info    = models.CharField(blank=True, max_length=64,  help_text="RAID0, 4x SATA 7200rpm")

    cpu_score_up    = models.FloatField(blank=True, null=True, help_text="1.01")
    ram_score_up    = models.FloatField(blank=True, null=True, help_text="1.85")
    disk_score_up   = models.FloatField(blank=True, null=True, help_text="0.92")
    network_score_up = models.FloatField(blank=True, null=True, help_text="1.21")
    storage_flush_per_sec_up = models.IntegerField(blank=True, null=True, help_text="20124")

    cpu_score_smp   = models.FloatField(blank=True, null=True, help_text="1.01")
    ram_score_smp   = models.FloatField(blank=True, null=True, help_text="1.85")
    disk_score_smp  = models.FloatField(blank=True, null=True, help_text="0.92")
    network_score_smp = models.FloatField(blank=True, null=True, help_text="1.21")
    storage_flush_per_sec_smp = models.IntegerField(blank=True, null=True, help_text="20124")


    def __str__(self):
        return "#%d, %s" % (self.id, self.name)

    class Meta:
        verbose_name = "Hw Node"
        verbose_name_plural = "Hw Nodes"


class HwFarmNodeBaseSerializer(serializers.ModelSerializer):
    pass


class HwFarmNodeSimpleSerializer(HwFarmNodeBaseSerializer):
    class Meta:
        model = HwFarmNodeModel
        fields = ('order', 'id', 'name', 'os', 'hostname', 'vendor', 'model', 'cpus_count', 'ram_gb', 'storage_tb', 'network_gbs', 'notes', 'locked_by')


class HwFarmNodeNestedSerializer(HwFarmNodeBaseSerializer):
    class Meta:
        model = HwFarmNodeModel
        fields = ('order', 'id', 'name', 'os', 'hostname', 'vendor', 'model', 'cpus_count', 'ram_gb', 'storage_tb', 'network_gbs', 'notes', 'locked_by')
