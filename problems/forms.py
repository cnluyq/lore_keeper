from django import forms
from .models import Problem, SensitiveWord, SiteConfig, CvBase
from django.core.exceptions import ValidationError
import re
import html

html_regex = re.compile(r'</?[a-zA-Z][a-zA-Z0-9-]*\b[^>]*>', re.IGNORECASE)
class ProblemForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = [
            'key_words', 'title', 'description', 'description_editor_type',
            'root_cause', 'root_cause_editor_type',
            'solutions', 'solutions_editor_type',
            'others', 'others_editor_type', 'is_public'
        ]
        widgets = {
            'description_editor_type': forms.HiddenInput(),
            'root_cause_editor_type': forms.HiddenInput(),
            'solutions_editor_type': forms.HiddenInput(),
            'others_editor_type': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        # 自动转义HTML字符
        text_fields = ['description', 'root_cause', 'solutions', 'others', 'key_words', 'title']
        for field_name in text_fields:
            text = cleaned_data.get(field_name, '')
            if text:
                # 将 < > & " ' 转义为 HTML 实体，防止XSS和页面结构破坏
                cleaned_data[field_name] = html.escape(text)

        return cleaned_data

from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')   # 注：password1、password2 会自动带上


class StaffUserCreationForm(UserCreationForm):
    # 把 email 设为必填
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class SensitiveWordForm(forms.ModelForm):
    class Meta:
        model = SensitiveWord
        fields = ['word', 'replacement', 'is_active']
        widgets = {
            'word': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Input sensitive word'}),
            'replacement': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Input replacement word'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'word': 'sensitive word',
            'replacement': 'replacement word',
            'is_active': 'active',
        }

class SiteConfigForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        fields = ['items_per_page', 'max_file_size', 'max_file_size_unit']
        widgets = {
            'items_per_page': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100,
                'placeholder': 'Items per page (1-100)'
            }),
            'max_file_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 1000,
                'placeholder': 'File size value (1-1000)'
            }),
            'max_file_size_unit': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'items_per_page': 'Items per page',
            'max_file_size': 'Max file size',
            'max_file_size_unit': 'Unit',
        }

    def clean_items_per_page(self):
        items_per_page = self.cleaned_data['items_per_page']
        if items_per_page < 1 or items_per_page > 100:
            raise forms.ValidationError('Items per page must be between 1 and 100.')
        return items_per_page

    def clean_max_file_size(self):
        max_file_size = self.cleaned_data['max_file_size']
        if max_file_size < 1:
            raise forms.ValidationError('Max file size must be at least 1.')
        if max_file_size > 1000:
            raise forms.ValidationError('Max file size cannot exceed 1000.')
        return max_file_size

class CvBaseForm(forms.ModelForm):
    class Meta:
        model = CvBase
        fields = ['record_date', 'title', 'content']
        widgets = {
            'record_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default editor type is markdown
        if self.instance.pk:
            self.initial['content_editor_type'] = self.instance.content_editor_type or 'markdown'
        else:
            self.initial['content_editor_type'] = 'markdown'

    def clean(self):
        cleaned_data = super().clean()

        # 自动转义HTML字符
        text_fields = ['title', 'content']
        for field_name in text_fields:
            text = cleaned_data.get(field_name, '')
            if text:
                cleaned_data[field_name] = html.escape(text)

        return cleaned_data

