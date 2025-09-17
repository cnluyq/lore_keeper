from django.db import models
from django.contrib.auth.models import User

class Problem(models.Model):
    key_words   = models.CharField(max_length=255)
    title       = models.CharField(max_length=255)
    description = models.TextField()
    root_cause  = models.TextField(blank=True)
    root_cause_file = models.FileField(upload_to='root_cause/', blank=True, null=True)
    solutions   = models.TextField(blank=True)
    solutions_file = models.FileField(upload_to='solutions/', blank=True, null=True)
    others      = models.TextField(blank=True)
    others_file = models.FileField(upload_to='others/', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_public = models.BooleanField(default=True, verbose_name="public view")
    description_editor_type = models.CharField(max_length=10, choices=[('markdown', 'Markdown'), ('plain', 'Plain Text')], default='plain')
    root_cause_editor_type = models.CharField(max_length=10, choices=[('markdown', 'Markdown'), ('plain', 'Plain Text')], default='plain')
    solutions_editor_type = models.CharField(max_length=10, choices=[('markdown', 'Markdown'), ('plain', 'Plain Text')], default='plain')
    others_editor_type = models.CharField(max_length=10, choices=[('markdown', 'Markdown'), ('plain', 'Plain Text')], default='plain')
    uploaded_images = models.TextField(blank=True, null=True) 

    class Meta:
        ordering = ['-create_time']

    def __str__(self):
        return self.title

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


import os
import json
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Problem

@receiver(post_delete, sender=Problem)
def auto_delete_files_on_problem_delete(sender, instance, **kwargs):
    # 删除 root_cause_file, solutions_file, others_file
    for field in ['root_cause_file', 'solutions_file', 'others_file']:
        file = getattr(instance, field, None)
        if file and os.path.isfile(file.path):
            os.remove(file.path)
