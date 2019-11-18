import datetime
from collections import OrderedDict

import pytz
from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.db.models import Q
from django.utils import timezone
from perftrackerlib.helpers.timeline import ptTimeline, ptDoc, ptSection, ptTask
from rest_framework import serializers

from perftracker.models.hw_farm_node import HwFarmNodeModel, HwFarmNodeNestedSerializer


class HwFarmNodeLockTypeModel(models.Model):
    name     = models.CharField(max_length=128, help_text="Lock type name", blank=False)
    bg_color = models.CharField(max_length=7, help_text="The background color: #003399")
    fg_color = models.CharField(max_length=7, help_text="The foreground color: #ffffff")
    order    = models.IntegerField(default=1, help_text="Priority in the list")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Hw Node Lock Type"
        verbose_name_plural = "Hw Node Lock Types"

    @staticmethod
    def _pt_get_default():
        return HwFarmNodeLockTypeModel(name="Default lock type", bg_color="#777", fg_color="#fff")

    @staticmethod
    def pt_get_by_id(id):
        if isinstance(id, HwFarmNodeLockTypeModel):
            return id

        if not id:
            return HwFarmNodeLockTypeModel._pt_get_default()
        try:
            return HwFarmNodeLockTypeModel.objects.get(id=id)
        except HwFarmNodeLockTypeModel.DoesNotExist:
            return HwFarmNodeLockTypeModel._pt_get_default()

    @staticmethod
    def pt_get_by_name(name):
        if not name:
            return HwFarmNodeLockTypeModel._pt_get_default()
        try:
            return HwFarmNodeLockTypeModel.objects.get(name=name)
        except HwFarmNodeLockTypeModel.DoesNotExist:
            return HwFarmNodeLockTypeModel._pt_get_default()

    @staticmethod
    def pt_get_all():
        all = HwFarmNodeLockTypeModel.objects.all().order_by('order')
        if len(all):
            return all
        return [HwFarmNodeLockTypeModel._pt_get_default()]


class HwFarmNodeLockTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HwFarmNodeLockTypeModel
        fields = ('name', 'bg_color', 'fg_color')


class HwFarmNodeLockModel(models.Model):
    title           = models.CharField(blank=True, max_length=128, help_text="My product perf job #123")
    owner           = models.CharField(blank=True, max_length=64, help_text="Jenkins")

    begin           = models.DateTimeField(default=timezone.now, help_text="2018-07-01 12:21:10", db_index=True)
    end             = models.DateTimeField(null=True, blank=True, help_text="2018-07-01 18:03:45", db_index=True)

    manual          = models.BooleanField(help_text="True means it was manually locked", default=True)
    deleted         = models.BooleanField(help_text="Lock deleted", default=False, db_index=True)

    hw_nodes        = models.ManyToManyField(HwFarmNodeModel, help_text="Host", limit_choices_to={'locked_by': None})

    planned_dur_hrs = models.IntegerField(default=24, help_text="Planned lock duration (hours)")

    lock_type       = models.ForeignKey(HwFarmNodeLockTypeModel, help_text="Lock type", blank=True, default=None,
                                        null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "#%s, %s" % (str(self.id), self.title)

    def is_active(self):
        return self.end is None or (self.end > timezone.now())

    class Meta:
        verbose_name = "Hw Node Lock"
        verbose_name_plural = "Hw Node Locks"

    def save(self):
        super(HwFarmNodeLockModel, self).save()

        for n in HwFarmNodeModel.objects.filter(locked_by=self):
            n.locked_by = None
            n.save()

        if self.deleted:
            return

        now = timezone.now()
        if self.end is None or (self.end > now and self.begin <= now):
            for n in self.hw_nodes.all():
                n.locked_by = self
                n.save()

    # Fixme. This is bad idea to write own validator
    @staticmethod
    def pt_validate_json(json_data):
        if 'title' not in json_data:
            raise SuspiciousOperation("'title' is not specified: it must be 'title': '...'")
        if 'planned_dur_hrs' not in json_data:
            raise SuspiciousOperation("'planned_dur_hrs' is not specified: it must be 'planned_dur_hrs': 12")
        if type(json_data['hw_nodes']) is not list:
            raise SuspiciousOperation("'hw_nodes' must be a list: 'hw_nodes': [1, 3, ...] ")
        if (type(json_data['lock_type']) is not dict) or 'name' not in json_data['lock_type']:
            raise SuspiciousOperation("'lock_type.name' is not set")
        try:
            x = int(json_data['planned_dur_hrs'])
        except ValueError:
            raise SuspiciousOperation("'planned_dur_hrs' must be an int")

    def pt_update(self, json_data):
        self.title = json_data['title']
        self.deleted = False
        self.lock_type = HwFarmNodeLockTypeModel.pt_get_by_name(json_data['lock_type']['name'])
        if self.lock_type.id is None:
            self.lock_type = None

        if not self.is_active():
            super(HwFarmNodeLockModel, self).save()
            return

        self.planned_dur_hrs = int(json_data['planned_dur_hrs'])

        hw_nodes = []

        for id in json_data['hw_nodes']:
            id = int(id)
            try:
                hw_node = HwFarmNodeModel.objects.get(id=id)
                if hw_node.locked_by and hw_node.locked_by != self:
                    raise SuspiciousOperation("Hw node #%d is already locked by lock #%d" % (id, hw_node.locked_by.id))

            except HwFarmNodeModel.DoesNotExist:
                raise SuspiciousOperation("Hw node #%d doesn't exist" % id)
            hw_nodes.append(hw_node)

        self.save()
        self.hw_nodes.clear()
        for node in hw_nodes:
            self.hw_nodes.add(node)
        self.save()

    def pt_unlock(self):
        self.end = timezone.now()
        self.deleted = False
        self.save()


class HwFarmNodeLockSimpleSerializer(serializers.ModelSerializer):
    lock_type = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()

    def get_active(self, lock):
        return lock.is_active()

    def get_lock_type(self, lock):
        lock_type = HwFarmNodeLockTypeModel.pt_get_by_id(lock.lock_type)
        return HwFarmNodeLockTypeSerializer(lock_type).data

    class Meta:
        model = HwFarmNodeLockModel
        fields = ('title', 'owner', 'begin', 'end', 'manual', 'planned_dur_hrs', 'hw_nodes', 'lock_type', 'active')


class HwFarmNodeLockNestedSerializer(HwFarmNodeLockSimpleSerializer):
    hw_nodes = serializers.SerializerMethodField()

    def get_hw_nodes(self, lock):
        nodes = HwFarmNodeModel.objects.filter(Q(locked_by=lock.id) | Q(locked_by=None))
        return HwFarmNodeNestedSerializer(nodes, many=True).data


class HwFarmNodesLocksTimeline:
    def __init__(self, project_id):
        self.project_id = project_id

    def gen_html(self):
        if self.project_id:
            nodes = HwFarmNodeModel.objects.filter(projects=self.project_id, hidden=False)
        else:
            nodes = HwFarmNodeModel.objects.filter(hidden=False)

        if len(nodes) == 0:
            return None

        now = datetime.datetime.now()
        now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

        range_begin = (now - datetime.timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        range_end = (now + datetime.timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0)

        d = ptDoc(header=" ", footer=" ")

        def gen_group(node):
            return "%s%s" % (n.name, " (%s)" % n.purpose if n.purpose else "") 

        width = 100  # an ugly hack...
        for n in nodes:
            width = max(width, len(gen_group(n)) * 6.5)

        s = d.add_section(ptSection())
        t = s.add_timeline(
            ptTimeline(
                title=None,
                begin=range_begin,
                end=range_end,
                groups_title='Hosts',
                cluster=False,
                js_opts={
                    'groupsTitle': "'Host'",
                    'groupsWidth': "'%dpx'" % int(width),
                    'groupsComments': "'host_status'",
                    'axisOnTop': 'true',
                    'showNavigation': 'true',}))

        since = range_begin - datetime.timedelta(days=60)
        default_end = now + datetime.timedelta(days=1)

        groups = OrderedDict()
        for n in nodes:
            group = gen_group(n);

            groups[n.id] = group
            t.add_task(ptTask("1970-01-01 00:00:00", "1970-01-01 00:00:00", group=group))

            locks = HwFarmNodeLockModel.objects.filter(Q(begin__gte=since) | Q(end=None), hw_nodes=n.pk, deleted=False)
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

                t.add_task(ptTask(l.begin, end, group=group, hint=hint, title=l.title, data_id=l.id,
                                  cssClass='pt_timeline_task_%s' % (l.lock_type.id if l.lock_type else 'default')))

        return d.gen_html()
