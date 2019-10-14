import bz2
import http.client
import mimetypes
import os
import sys
from datetime import timedelta
from distutils.dir_util import mkpath

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers

from perftracker.helpers import PTJson, pt_is_valid_uuid
from perftracker.rest import pt_rest_err, pt_rest_bad_req, pt_rest_ok

IS_WINDOWS = sys.platform.startswith('win')
if not IS_WINDOWS:
    import fcntl

# Artifact is a file (tgz, txt, log, html, etc) which can be linked (many to many) to some object (Test, Job, Regression, Host, etc)

class ArtifactMetaModel(models.Model):
    uuid        = models.UUIDField(editable=False, help_text="Artifact file uuid", db_index=True)
    filename    = models.CharField(max_length=128, default="artifact", help_text="Artifact file name (for download)")
    description = models.CharField(max_length=256, help_text="Artifact description")
    mime        = models.CharField(max_length=32,  default="", help_text="Artifact file mime type")
    deleted     = models.BooleanField(help_text="Artifact is deleted", db_index=True, default=False, blank=True)
    uploaded_dt = models.DateTimeField(help_text="Datetime when artifact was uploaded", default=timezone.now)
    ttl_days    = models.IntegerField(help_text="Artifact time to live (days)", default=180)
    deleted_dt  = models.DateTimeField(help_text="Datetime when artifact was deleted by garbage collector", blank=True, null=True, default=None)
    expires_dt  = models.DateTimeField(help_text="Datetime when artifact can be deleted by GC", db_index=True)
    size        = models.IntegerField(help_text="Artifact file size in bytes")
    inline      = models.BooleanField(help_text="View document in browser (do not download)", default=False)
    compression = models.BooleanField(help_text="Decompress on download/view", default=False)

    @staticmethod
    def pt_artifacts_enabled():
        return hasattr(settings, 'ARTIFACTS_STORAGE_DIR') and settings.ARTIFACTS_STORAGE_DIR

    def _pt_gen_data_dir_path(self):
        if not hasattr(settings, 'ARTIFACTS_STORAGE_DIR') or not settings.ARTIFACTS_STORAGE_DIR:
             raise SuspiciousOperation("Artifacts storage is not enabled")

        return settings.ARTIFACTS_STORAGE_DIR

    def _pt_gen_file_path(self):
        uuid = str(self.uuid)
        return os.path.join(self._pt_gen_data_dir_path(), uuid[0:2], uuid[2:4], uuid[4:6], uuid[6:8], uuid[9:], uuid)

    def _pt_save_file(self, bytes):
        p = self._pt_gen_file_path()
        exists = os.path.exists(p)

        if not exists:
            d = os.path.dirname(p)
            try:
                 mkpath(d)
            except:
                 return pt_rest_err(http.client.INTERNAL_SERVER_ERROR, "Can't create directory %s" % d)

        flags = os.O_RDWR | os.O_EXCL | os.O_TRUNC
        if not self.id:
            flags |= os.O_CREAT

        do_locks = not sys.platform.startswith('win')

        try:
            f = os.fdopen(os.open(p, flags), "wb")
            if not IS_WINDOWS:  # FIXME
                fcntl.flock(f, fcntl.LOCK_EX)
            f.write(bytes)
            if not IS_WINDOWS:  # FIXME
                fcntl.flock(f, fcntl.LOCK_UN)
            f.close()
        except IOError as e:
            return pt_rest_err(http.client.INTERNAL_SERVER_ERROR, "Can't store artifact to file %s, %s" % (p, str(e)))

        self.size = os.path.getsize(p)
        return None

    def pt_update(self, json_data, file_data=None):
        j = PTJson(json_data, obj_name="artifact json", exception_type=SuspiciousOperation)

        try:
            self.description = j.get_str('description', defval=self.description)
            self.ttl_days = j.get_int('ttl_days', defval=self.ttl_days)
            self.uploaded_dt = timezone.now()
            self.filename = j.get_str('filename', defval=self.filename, require=False if self.filename else True)
            self.mime = j.get_str('mime', defval=self.mime)
            self.expires_dt = timezone.now() + timedelta(days=self.ttl_days)
            self.inline = j.get_bool('inline', defval=self.inline)
            self.compression = j.get_bool('compression', defval=self.compression)
            linked_uuids = j.get_list('linked_uuids', [])
            unlinked_uuids = j.get_list('unlinked_uuids', [])
        except SuspiciousOperation as e:
            return pt_rest_bad_req(str(e))

        if not self.mime:
            self.mime = mimetypes.guess_type(self.filename)[0]
        if not self.mime:
            self.mime = 'application/octet-stream'

        if file_data:
            data = file_data.get('file', None)
            if data is None:
                return pt_rest_bad_req("can't get file data")
            ret = self._pt_save_file(data.read())
            if ret is not None:
                return ret

        for uuid in linked_uuids:
            if not pt_is_valid_uuid(uuid):
                return pt_rest_bad_req("trying to link resource with invalid UUID format: %s" % uuid)

        for uuid in unlinked_uuids:
            if not pt_is_valid_uuid(uuid):
                return pt_rest_bad_req("trying to unlink resource with invalid UUID format: %s" % uuid)

        exists = self.id
        self.save()

        for uuid in linked_uuids:
            try:
                al = ArtifactLinkModel.objects.get(artifact=self, linked_uuid=uuid)
                if al.deleted:
                   al.deleted = False
                   al.save()
                continue
            except ArtifactLinkModel.DoesNotExist as e:
                al = ArtifactLinkModel(artifact=self, linked_uuid=uuid)
                al.save()

        for uuid in unlinked_uuids:
            try:
                al = ArtifactLinkModel.objects.get(artifact=self, linked_uuid=uuid)
            except ArtifactLinkModel.DoesNotExist as e:
                continue
            al.deleted = True
            al.save()

        return pt_rest_ok(message="Artifact has been %s, uuid: %s" % ("updated" if exists else "created", self.uuid), uuid=self.uuid)

    def pt_delete(self):
        p = self._pt_gen_file_path()
        if os.path.exists(p):
            os.unlink(p)

        self.deleted = True
        self.deleted_dt = timezone.now()
        self.save()

        return pt_rest_ok(message="Artifact has been deleted, uuid: %s" % self.uuid)

    def pt_get_http_content(self):
        p = self._pt_gen_file_path()
        if not p or not os.path.exists(p):
            if self.deleted:
                return pt_rest_err(http.client.GONE, "Data with UUID %s was deleted @ %s" % (self.uuid, str(self.deleted_dt)))
            else:
                return pt_rest_err(http.client.NOT_FOUND, "Can't find artifact file for UUID %s" % self.uuid, uuid=self.uuid)

        try:
            if self.compression:
                f = bz2.BZ2File(p, 'rb')
            else:
                f = open(p, 'rb')
            content = f.read()
            f.close()
        except IOError:
            return pt_rest_err(http.client.INTERNAL_SERVER_ERROR, "Internal error, can't read artifact for UUID %s" % self.uuid)

        resp = HttpResponse(content, content_type=self.mime)
        if self.inline:
            resp['Content-Disposition'] = 'inline'
        else:
            resp['Content-Disposition'] = 'attachment; filename=%s' % self.filename
        return resp


class ArtifactLinkModel(models.Model):
    artifact    = models.ForeignKey(ArtifactMetaModel, help_text="Artifact", on_delete=models.CASCADE)
    linked_uuid = models.UUIDField(editable=False, help_text="any object uuid", db_index=True, blank=False)
    deleted     = models.BooleanField(help_text="Artifact link is deleted", db_index=True, default=False, blank=True)


class ArtifactLinkSerializer(serializers.ModelSerializer):

    class Meta:
        model = ArtifactLinkModel
        fields = '__all__'


class ArtifactMetaSerializer(serializers.ModelSerializer):

    links = serializers.SerializerMethodField()

    def get_links(self, artifact):
        links = [a.linked_uuid for a in ArtifactLinkModel.objects.filter(deleted=False, artifact=artifact)]
        return links

    class Meta:
        model = ArtifactMetaModel
        fields = '__all__'
