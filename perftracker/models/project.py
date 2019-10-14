from django.core.exceptions import SuspiciousOperation
from django.db import models
from rest_framework import serializers


class ProjectModel(models.Model):
    name = models.CharField(max_length=64, help_text="Project name: Browsers, Clients, Servers...")
    description = models.CharField(max_length=256, help_text="Project description")
    nav_prio = models.IntegerField(help_text="Priority in the navigation dropdown list (1 - top, 100 - bottom)")
    nav_visible = models.BooleanField(help_text="Do display in the navigation bar", default=True)

    def __str__(self):
        return self.name + (" (hidden)" if not self.nav_visible else "")

    @staticmethod
    def pt_initialize():
        if not len(ProjectModel.objects.all()):
            ProjectModel(id=1, name="Default project", description="Default PerfTracker project", nav_prio=100).save()

    @staticmethod
    def pt_get_by_id(proj_id):
        proj_id = int(proj_id)

        if proj_id == 0:
            p = ProjectModel()
            p.name = "All projects"
            p.description = "Container for all projects"
            p.id = 0
            return p

        try:
            return ProjectModel.objects.get(pk=proj_id)
        except ProjectModel.DoesNotExist:
            ProjectModel.pt_initialize()

        try:
            return ProjectModel.objects.get(pk=proj_id)
        except ProjectModel.DoesNotExist:
            return None

    @staticmethod
    def pt_get_by_name(proj_name):
        try:
            return ProjectModel.objects.get(name=proj_name)
        except ProjectModel.DoesNotExist:
            ProjectModel.pt_initialize()

        try:
            return ProjectModel.objects.get(name=proj_name)
        except ProjectModel.DoesNotExist:
            projects = ["'%s'" % p.name for p in ProjectModel.objects.all()]
            raise SuspiciousOperation("Project '%s' doesn't exist. Use: %s" % (proj_name, ", ".join(projects)))

    def pt_get_all(self):
        try:
            return ProjectModel.objects.filter(nav_visible=True).order_by('nav_prio')
        except ProjectModel.DoesNotExist:
            self.pt_initialize()

        try:
            return ProjectModel.objects.filter(nav_visible=True).order_by('nav_prio')
        except ProjectModel.DoesNotExist:
            return None

    class Meta:
        verbose_name = "PerfTracker Project"
        verbose_name_plural = "PerfTracker Projects"


class ProjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProjectModel
        fields = ('id', 'name')
