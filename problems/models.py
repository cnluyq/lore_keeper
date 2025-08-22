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

