import pytz
import datetime
from collections import OrderedDict

from django import forms
from django.db import models
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.core.exceptions import SuspiciousOperation

from rest_framework import serializers

from perftracker.helpers import ptDurationField
from perftracker.models.project import ProjectModel
from perftrackerlib.helpers.timeline import ptTimeline, ptDoc, ptSection, ptTimeline, ptTask


class HwFarmNodeLockModel(models.Model):
    title           = models.CharField(blank=True, max_length=128, help_text="My product perf job #123")
    owner           = models.CharField(blank=True, max_length=64, help_text="Jenkins")

    begin           = models.DateTimeField(default=timezone.now, help_text="2018-07-01 12:21:10", db_index=True)
    end             = models.DateTimeField(null=True, blank=True, help_text="2018-07-01 18:03:45", db_index=True)

    manual          = models.BooleanField(help_text="True means it was manually locked", default=True)
    deleted         = models.BooleanField(help_text="Lock deleted", default=False, db_index=True)

    hw_nodes        = models.ManyToManyField('HwFarmNodeModel', help_text="Host", limit_choices_to={'locked_by': None})

    planned_dur_hrs = models.IntegerField(default=24, help_text="Planned lock duration (hours)")

    def __str__(self):
        return "#%s, %s" % (str(self.id), self.title)

    class Meta:
        verbose_name = "Hw Node Lock"
        verbose_name_plural = "Hw Node Locks"

    def save(self):
        super(HwFarmNodeLockModel, self).save()

        for n in HwFarmNodeModel.objects.filter(locked_by=self):
            n.locked_by = None
            n.save()

        now = timezone.now()
        if self.end is None or (self.end > now and self.begin <= now):
            for n in self.hw_nodes.all():
                n.locked_by = self
                n.save()


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


class HwFarmNodesTimeline:
    def __init__(self, project_id):
        self.project_id = project_id

    def gen_html(self):
        nodes = HwFarmNodeModel.objects.filter(projects=self.project_id, hidden=False)

        now = datetime.datetime.now()
        now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

        range_begin = (now - datetime.timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        range_end = (now + datetime.timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)

        d = ptDoc(header=" ", footer=" ")
        s = d.add_section(ptSection())
        t = s.add_timeline(ptTimeline(title=None, begin=range_begin, end=range_end,
                                      js_opts={
                                               'groupsTitle': "'Host'",
                                               'groupsWidth': "'100px'",
                                               'groupsComments': "'host_status'",
                                               'axisOnTop': 'true',
                                               'showNavigation': 'true',
                                              }))

        since = range_begin - datetime.timedelta(days=60)
        default_end = now + datetime.timedelta(days=1)

        groups = OrderedDict()
        for n in nodes:
            groups[n.id] = n.name
            t.add_task(ptTask("1970-01-01 00:00:00", "1970-01-01 00:00:00", group=n.name))

            locks = HwFarmNodeLockModel.objects.filter(begin__gte=since, hw_nodes=n.pk, deleted=False)
            for l in locks:
                hint = l.title
                if l.owner:
                    hint += " (%s)" % l.owner
                hint += " | " + str(l.begin)
                if l.end:
                    hint += " - " + str(l.end)

                end = default_end
                if l.end:
                   end = l.end
                elif l.planned_dur_hrs:
                   end = l.begin + datetime.timedelta(hours=l.planned_dur_hrs)
                   if end < now_utc:
                       end = default_end

                t.add_task(ptTask(l.begin, end, group=n.name, hint=hint, title=l.title,
                                  cssClass='pt_timeline_task_manual' if l.manual else 'pt_timeline_task_auto'))

        return d.gen_html()
