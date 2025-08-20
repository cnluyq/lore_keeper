import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse, HttpResponse
from .models import Problem
from .forms import ProblemForm
from django.db.models import Q 
from django.core.serializers.json import DjangoJSONEncoder
from .forms import RegisterForm
from django.conf import settings
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.exceptions import PermissionDenied

def owner_or_superuser_required(view_func):
    """允许创建者或超级用户"""
    def _wrapped_view(request, *args, **kwargs):
        # 仅针对需要 pk 的视图
        pk = kwargs.get('pk')
        obj = get_object_or_404(Problem, pk=pk)
        if request.user.is_superuser or obj.created_by == request.user:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view


def superuser_required(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)

# ---------- 游客可见 ----------
from django.core.serializers.json import DjangoJSONEncoder
def problem_list(request):
    # 一次性返回所有问题数据
    problems = Problem.objects.all().order_by('-create_time')
    data = [
        {
            'id': p.id,
            'key_words': p.key_words,
            'title': p.title,
            'description': p.description,
            'root_cause': p.root_cause,
            'root_cause_file': p.root_cause_file.url if p.root_cause_file else None,
            'solutions': p.solutions,
            'solutions_file': p.solutions_file.url if p.solutions_file else None,
            'others': p.others,
            'others_file': p.others_file.url if p.others_file else None,
            'create_time': p.create_time.strftime('%Y-%m-%d %H:%M'),
            'update_time': p.update_time.strftime('%Y-%m-%d %H:%M'),
            'created_by': p.created_by.username if p.created_by else '-',
        }
        for p in problems
        if (p.created_by == request.user or request.user.is_superuser or p.is_public)
    ]
    context = {
        'problems_json': json.dumps(data, ensure_ascii=False),
        'user': request.user,
    }
    return render(request, 'problems/problem_list.html', context)
# ---------- 登录/注册 ----------
def register_view(request):
    if not settings.REGISTRATION_OPEN:
        return HttpResponseForbidden("Registration is currently disabled.")

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('problem_list')
    else:
        form = RegisterForm()
    return render(request, 'problems/register.html', {'form': form})

def login_view(request):
    from django.contrib.auth.views import LoginView
    return LoginView.as_view(template_name='problems/login.html')(request)

# ---------- 需登录 ----------
@login_required
def problem_add(request):
    if request.method == 'POST':
        form = ProblemForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            return redirect('problem_list')
    else:
        form = ProblemForm()
    return render(request, 'problems/problem_form.html', {'form': form, 'action': 'Add'})

@login_required
@owner_or_superuser_required
def problem_edit(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    if not problem.is_public and not (request.user == problem.created_by or request.user.is_superuser):
        raise PermissionDenied

    if request.method == 'POST':
        form = ProblemForm(request.POST, request.FILES, instance=problem)
        if form.is_valid():
            form.save()
            return redirect('problem_list')
    else:
        form = ProblemForm(instance=problem)
    return render(request, 'problems/problem_form.html', {'form': form, 'action': 'Edit'})

@login_required
@owner_or_superuser_required
def problem_delete(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    problem.delete()
    return redirect('problem_list')

# ---------- 导入/导出 ----------
#@login_required
#def export_json(request):
#    data = list(Problem.objects.all().values(
#        'id', 'key_words', 'title', 'description',
#        'root_cause', 'solutions', 'others',
#       'create_time', 'update_time'
#    ))
#    response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=2),
#                            content_type='application/json')
#    response['Content-Disposition'] = 'attachment; filename="problems.json"'
#    return response

@login_required
@superuser_required
def export_json(request):
    data = list(
        Problem.objects.all().values(
            'id', 'key_words', 'title', 'description',
            'root_cause', 'solutions', 'others',
            'create_time', 'update_time'
        )
    )
    response = HttpResponse(
        json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = 'attachment; filename="problems.json"'
    return response

#@login_required
#def import_json(request):
#    if request.method == 'POST' and request.FILES.get('file'):
#        file = request.FILES['file']
#        try:
#            data = json.load(file)
#            for item in data:
#                item.pop('id', None)  # 避免主键冲突
#                Problem.objects.create(created_by=request.user, **item)
#            return JsonResponse({'status': 'success'})
#        except Exception as e:
#            return JsonResponse({'status': 'error', 'message': str(e)})
#    return JsonResponse({'status': 'invalid'})

@login_required
@superuser_required
def import_json(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        try:
            data = json.load(file)
            for item in data:
                item.pop('id', None)  # 防止主键冲突
                Problem.objects.create(created_by=request.user, **item)
            # 上传成功后直接跳转回列表页
            return redirect('problem_list')
        except Exception as e:
            # 出错时仍然返回 JSON，方便调试
            return JsonResponse({'status': 'error', 'message': str(e)})
    # GET 请求禁止访问
    return redirect('problem_list')


from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    return redirect('problem_list')

@superuser_required
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'problems/user_list.html', {'users': users})

@superuser_required
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user != request.user:            # 防止自锁
        user.is_active = not user.is_active
        user.save()
    return redirect('user_list')

#@superuser_required
#def user_delete(request, pk):
#    user = get_object_or_404(User, pk=pk)
#    if user != request.user:  # 防止删除自己
#        user.delete()
#    return redirect('user_list')

@superuser_required
def user_delete(request, pk):
    user_to_delete = get_object_or_404(User, pk=pk)
    if user_to_delete == request.user:
        messages.error(request, "Cannot delete yourself.")
        return redirect('user_list')

    problems = Problem.objects.filter(created_by=user_to_delete)

    if request.method == 'POST':
        # 获取要删除的问题 id
        selected_ids = request.POST.getlist('problem_ids')
        print('========== selected_ids ==========', selected_ids) 
        if selected_ids:
            Problem.objects.filter(id__in=selected_ids).delete()
            messages.success(request, f"Deleted {len(selected_ids)} problem(s).")
        else:
            messages.info(request, "No problem records were deleted.")

        user_to_delete.delete()
        messages.success(request, f"User {user_to_delete.username} deleted.")
        return redirect('user_list')

    return render(request, 'problems/user_delete_confirm.html', {
        'user_to_delete': user_to_delete,
        'problems': problems,
    })

from django.contrib.admin.views.decorators import staff_member_required
from .forms import StaffUserCreationForm

@staff_member_required
def user_add(request):
    if request.method == 'POST':
        form = StaffUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            # 保存后跳转回用户列表
            return redirect('user_list')
    else:
        form = StaffUserCreationForm()
    return render(request, 'problems/user_add.html', {'form': form})
