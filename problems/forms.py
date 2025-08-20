from django import forms
from .models import Problem
from django.core.exceptions import ValidationError

class ProblemForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = [
            'key_words', 'title', 'description',
            'root_cause', 'root_cause_file',
            'solutions', 'solutions_file',
            'others', 'others_file', 'is_public'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['root_cause_file'].label = 'Root cause file (no more than 2M)'
        self.fields['solutions_file'].label  = 'Solutions file (no more than 2M)'
        self.fields['others_file'].label     = 'Others file (no more than 2M)'

    def clean(self):
        cleaned_data = super().clean()
        # 检查所有文件字段的大小
        file_fields = ['root_cause_file', 'solutions_file', 'others_file']
        max_size = 2 * 1024 * 1024  # 2MB

        for field_name in file_fields:
            file = cleaned_data.get(field_name)
            if file and hasattr(file, 'size'):
                if file.size > max_size:
                    raise ValidationError(
                        f"{field_name.replace('_', ' ').title()}: File size must be no more than 2MB."
                    )
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
