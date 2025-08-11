from django.contrib import admin
from .models import Problem

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'key_words', 'created_by', 'create_time')
    search_fields = ('title', 'key_words', 'description')
