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

    class Meta:
        ordering = ['-create_time']

    def __str__(self):
        return self.title
