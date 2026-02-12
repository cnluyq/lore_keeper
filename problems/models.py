import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

class Problem(models.Model):
    key_words   = models.CharField(max_length=255)
    title       = models.CharField(max_length=255)
    description = models.TextField()
    root_cause  = models.TextField(blank=True)
    root_cause_file = models.FileField(upload_to='', blank=True, null=True)
    solutions   = models.TextField(blank=True)
    solutions_file = models.FileField(upload_to='', blank=True, null=True)
    others      = models.TextField(blank=True)
    others_file = models.FileField(upload_to='', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_public = models.BooleanField(default=True, verbose_name="public view")
    description_editor_type = models.CharField(max_length=10, choices=[('markdown', 'Markdown'), ('plain', 'Plain Text')], default='plain')
    root_cause_editor_type = models.CharField(max_length=10, choices=[('markdown', 'Markdown'), ('plain', 'Plain Text')], default='plain')
    solutions_editor_type = models.CharField(max_length=10, choices=[('markdown', 'Markdown'), ('plain', 'Plain Text')], default='plain')
    others_editor_type = models.CharField(max_length=10, choices=[('markdown', 'Markdown'), ('plain', 'Plain Text')], default='plain')
    uploaded_images = models.TextField(blank=True, null=True)
    public_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Delimiter for storing multiple filenames
    FILE_DELIMITER = '|||'

    class Meta:
        ordering = ['-create_time']

    def __str__(self):
        return self.title

    def _parse_files(self, file_field_value):
        """Parse 'file1.pdf|||file2.doc' -> ['file1.pdf', 'file2.doc']"""
        if not file_field_value:
            return []
        return file_field_value.split(self.FILE_DELIMITER)

    def _build_filename_string(self, filenames):
        """Build ['file1.pdf', 'file2.doc'] -> 'file1.pdf|||file2.doc'"""
        return self.FILE_DELIMITER.join(filenames)

    def get_root_cause_files(self):
        """Return list of root_cause filenames"""
        return self._parse_files(self.root_cause_file.name if self.root_cause_file else None)

    def get_solutions_files(self):
        """Return list of solutions filenames"""
        return self._parse_files(self.solutions_file.name if self.solutions_file else None)

    def get_others_files(self):
        """Return list of others filenames"""
        return self._parse_files(self.others_file.name if self.others_file else None)

    def set_root_cause_files(self, filenames):
        """Set root_cause files from a list of filenames"""
        self.root_cause_file.name = self._build_filename_string(filenames)

    def set_solutions_files(self, filenames):
        """Set solutions files from a list of filenames"""
        self.solutions_file.name = self._build_filename_string(filenames)

    def set_others_files(self, filenames):
        """Set others files from a list of filenames"""
        self.others_file.name = self._build_filename_string(filenames)

    def add_root_cause_file(self, filename):
        """Add a root_cause file to the list"""
        files = self.get_root_cause_files()
        files.append(filename)
        self.root_cause_file.name = self._build_filename_string(files)

    def add_solutions_file(self, filename):
        """Add a solutions file to the list"""
        files = self.get_solutions_files()
        files.append(filename)
        self.solutions_file.name = self._build_filename_string(files)

    def add_others_file(self, filename):
        """Add an others file to the list"""
        files = self.get_others_files()
        files.append(filename)
        self.others_file.name = self._build_filename_string(files)

    def remove_root_cause_file(self, filename):
        """Remove a root_cause file from the list"""
        files = self.get_root_cause_files()
        if filename in files:
            files.remove(filename)
        self.root_cause_file.name = self._build_filename_string(files)

    def remove_solutions_file(self, filename):
        """Remove a solutions file from the list"""
        files = self.get_solutions_files()
        if filename in files:
            files.remove(filename)
        self.solutions_file.name = self._build_filename_string(files)

    def remove_others_file(self, filename):
        """Remove an others file from the list"""
        files = self.get_others_files()
        if filename in files:
            files.remove(filename)
        self.others_file.name = self._build_filename_string(files)

class SensitiveWord(models.Model):
    word = models.CharField(max_length=100, unique=True, verbose_name="sensitive word")
    replacement = models.CharField(max_length=100, default="***", verbose_name="replacement word")
    is_active = models.BooleanField(default=True, verbose_name="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "sensitive word"
        verbose_name_plural = "sensitive word"

    def __str__(self):
        return f"{self.word} -> {self.replacement} ({'enable' if self.is_active else 'disable'})"


class SiteConfig(models.Model):
    items_per_page = models.IntegerField(
        default=10,
        verbose_name="Items per page",
        help_text="Number of items to display per page"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site configuration"
        verbose_name_plural = "site configuration"

    def __str__(self):
        return f"Site Config (items_per_page: {self.items_per_page})"

    @classmethod
    def get_config(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        if created:
            obj.save()
        return obj


import os
import json
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Problem

@receiver(post_delete, sender=Problem)
def auto_delete_files_on_problem_delete(sender, instance, **kwargs):
    # Delete all files in the problem's directory structure: uploads/<id>/<field_base>/
    if instance.id:
        problem_dir = os.path.join(settings.MEDIA_ROOT, str(instance.id))
        if os.path.isdir(problem_dir):
            for field_base in ['root_cause', 'solutions', 'others']:
                field_dir = os.path.join(problem_dir, field_base)
                if os.path.isdir(field_dir):
                    for filename in os.listdir(field_dir):
                        file_path = os.path.join(field_dir, filename)
                        if os.path.isfile(file_path):
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                print(f'Failed to delete {file_path}: {e}')
                    # Remove the field directory if empty
                    try:
                        os.rmdir(field_dir)
                    except Exception:
                        pass
            # Remove the problem directory if empty
            try:
                os.rmdir(problem_dir)
            except Exception:
                pass

    # Delete uploaded_images
    if instance.uploaded_images:
        try:
            uploaded_images = json.loads(instance.uploaded_images)
        except json.JSONDecodeError:
            uploaded_images = []
        print(f"auto_delete_files_on_problem_delete::uploaded_images:", uploaded_images)
        for image_name in uploaded_images:
            image_path = os.path.join(settings.MEDIA_ROOT, 'upload_images', image_name.lstrip('/'))
            print(f"auto_delete_files_on_problem_delete::image_path", image_path)
            if os.path.isfile(image_path):
                os.remove(image_path)
