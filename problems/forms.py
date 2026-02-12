from django import forms
from .models import Problem, SensitiveWord, SiteConfig
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
        fields = ['items_per_page']
        widgets = {
            'items_per_page': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100,
                'placeholder': 'Items per page (1-100)'
            }),
        }
        labels = {
            'items_per_page': 'Items per page',
        }

    def clean_items_per_page(self):
        items_per_page = self.cleaned_data['items_per_page']
        if items_per_page < 1 or items_per_page > 100:
            raise forms.ValidationError('Items per page must be between 1 and 100.')
        return items_per_page

