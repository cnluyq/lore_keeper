from django import forms
from .models import Problem

class ProblemForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = [
            'key_words', 'title', 'description',
            'root_cause', 'root_cause_file',
            'solutions', 'solutions_file',
            'others', 'others_file'
        ]

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