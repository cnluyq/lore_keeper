import json
import os
import uuid
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

from pathlib import Path
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .models import SensitiveWord
from .forms import SensitiveWordForm
from .sensitive_utils import SensitiveDataProcessor

from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.views.decorators.http import require_POST

from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView

from django.contrib.admin.views.decorators import staff_member_required
from .forms import StaffUserCreationForm

from django.contrib import messages
from .models import SensitiveWord
from .forms import SensitiveWordForm
from .sensitive_utils import SensitiveDataProcessor

from hashlib import pbkdf2_hmac
import base64, gzip
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
def pwd_to_chacha_key(password: str, salt: bytes = b'lore_keeper_sb') -> bytes:
    """PBKDF2 -> 32 B -> ChaCha20Poly1305 原生密钥"""
    key = pbkdf2_hmac('sha256', password.encode(), salt, 100_000, dklen=32)
    return key

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
def problem_list(request):
    # 一次性返回所有问题数据
    problems = Problem.objects.all().order_by('-create_time')
    data = [
        {
            'id': p.id,
            'key_words': p.key_words,
            'title': p.title,
            'description': p.description,
            'description_editor_type': p.description_editor_type,
            'root_cause': p.root_cause,
            'root_cause_editor_type': p.root_cause_editor_type,
            'root_cause_file': p.root_cause_file.url if p.root_cause_file else None,
            'solutions': p.solutions,
            'solutions_editor_type': p.solutions_editor_type,
            'solutions_file': p.solutions_file.url if p.solutions_file else None,
            'others': p.others,
            'others_editor_type': p.others_editor_type,
            'others_file': p.others_file.url if p.others_file else None,
            'create_time': p.create_time.strftime('%Y-%m-%d %H:%M'),
            'update_time': p.update_time.strftime('%Y-%m-%d %H:%M'),
            'created_by': p.created_by.username if p.created_by else '-',
            'public_token': str(p.public_token),
            'is_public': p.is_public,
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
    return LoginView.as_view(template_name='problems/login.html')(request)

# ---------- 需登录 ----------
@login_required
def problem_add(request):
    sensitive_words = list(SensitiveDataProcessor.get_active_sensitive_words())
    sensitive_words_json = json.dumps(sensitive_words, ensure_ascii=False)

    if request.method == 'POST':
        form = ProblemForm(request.POST, request.FILES)
        if form.is_valid():
            processed_data = SensitiveDataProcessor.process_form_data(request.POST)
            form = ProblemForm(processed_data, request.FILES)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.created_by = request.user
                obj.save()

                # 将会话中的图片路径转移到 uploaded_images 字段中
                if 'uploaded_images' in request.session:
                    obj.uploaded_images = json.dumps(request.session['uploaded_images'])
                    obj.save()
                    del request.session['uploaded_images']

                return redirect('problem_list')
    else:
        form = ProblemForm()
    return render(request, 'problems/problem_form.html', {'form': form, 'action': 'Add', 'sensitive_words_json': sensitive_words_json})

@login_required
@owner_or_superuser_required
def problem_edit(request, pk):
    sensitive_words = list(SensitiveDataProcessor.get_active_sensitive_words())
    sensitive_words_json = json.dumps(sensitive_words, ensure_ascii=False)

    problem = get_object_or_404(Problem, pk=pk)
    if not problem.is_public and not (request.user == problem.created_by or request.user.is_superuser):
        raise PermissionDenied

    if request.method == 'POST':
        old_files = {}
        for field in ['root_cause_file', 'solutions_file', 'others_file']:
            old_files[field] = getattr(problem, field)   # 这里一定是 FieldFile 或空

        form = ProblemForm(request.POST, request.FILES, instance=problem)
        if form.is_valid():
            processed_data = SensitiveDataProcessor.process_form_data(request.POST)
            form = ProblemForm(processed_data, request.FILES, instance=problem)
            if form.is_valid():

                # 将会话中的图片路径转移到 uploaded_images 字段中
                if 'uploaded_images' in request.session:
                    if problem.uploaded_images:
                        uploaded_images = json.loads(problem.uploaded_images)
                    else:
                        uploaded_images = []
                    uploaded_images.extend(request.session['uploaded_images'])
                    problem.uploaded_images = json.dumps(uploaded_images)
                    del request.session['uploaded_images']

                # 处理信息中的附件 
                file_fields = ['root_cause_file', 'solutions_file', 'others_file']
                for field in file_fields:
                    new_file = form.cleaned_data.get(field)  # 上传的新文件或 False/None(False 表示勾了 clear)
                    old_file = old_files[field]
                    print(f'[DEBUG] new_file:',new_file)
                    print(f'[DEBUG] old_file:',old_file)
                    if old_file and (not new_file or new_file != old_file):
                        path = old_file.path
                        print(f'[DEBUG] will delete {field}: {path}')
                        try:
                            if os.path.isfile(path):
                                os.remove(path)
                                print(f'[DEBUG] {path} is deleted')
                            else:
                                print(f'[DEBUG] {path} does not exist')
                        except Exception as e:
                            print(f'[DEBUG] failed to delete {path}: {e}')
                        # 数据库置空
                        old_file.delete(save=False)

                    if new_file is False:
                        setattr(problem, field, None)  # 如果是 False，则置空
                    else:
                        setattr(problem, field, new_file)  # 否则赋上新值


                form.save()
                return redirect('problem_list')
    else:
        form = ProblemForm(instance=problem)
    return render(request, 'problems/problem_form.html', {'form': form, 'action': 'Edit', 'sensitive_words_json': sensitive_words_json})

@login_required
@owner_or_superuser_required
def problem_delete(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    problem.delete()
    return redirect('problem_list')

@login_required
@superuser_required
def export_json(request):
    body = json.loads(request.body)
    password = body.get('password')
    if not password:
        return JsonResponse({'error': 'need password'}, status=400)

    key = pwd_to_chacha_key(password)

    data = list(
        Problem.objects.all().values(
            'id', 'key_words', 'title', 'description', 'description_editor_type',
            'root_cause', 'root_cause_editor_type', 'solutions', 'solutions_editor_type',
            'others', 'others_editor_type', 'create_time', 'update_time',
            'root_cause_file','solutions_file','others_file','uploaded_images',
            'is_public', 'public_token'
        )
    )

    raw  = json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2).encode()
    zipped = gzip.compress(raw)

    cipher = ChaCha20Poly1305(key)
    nonce  = os.urandom(12)
    encrypted = cipher.encrypt(nonce, zipped, associated_data=None)

    blob = nonce + encrypted

    response = HttpResponse(blob, content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename="items.bin"'
    return response

@login_required
@superuser_required
def import_json(request):
    if request.method == 'POST' and request.FILES.get('file'):
        password = request.POST.get('password')
        file_size = request.FILES['file'].size
        if not password:
            return JsonResponse({'error': 'need password'}, status=400)

        try:
            blob = request.FILES['file'].read()
            if len(blob) < 12:
                raise ValueError('file is too short')

            key = pwd_to_chacha_key(password)
            nonce, ct = blob[:12], blob[12:]

            cipher = ChaCha20Poly1305(key)
            zipped = cipher.decrypt(nonce, ct, associated_data=None)
            data = json.loads(gzip.decompress(zipped).decode())

            for item in data:
                item.setdefault('description_editor_type', 'plain')
                item.setdefault('root_cause_editor_type', 'plain')
                item.setdefault('solutions_editor_type', 'plain')
                item.setdefault('others_editor_type', 'plain')

                # 处理 public_token
                public_token = item.get('public_token')
                if public_token:
                    # 检查该 public_token 是否已存在
                    try:
                        uuid.UUID(public_token)
                        # 如果已存在相同 public_token 的记录，生成新的
                        if Problem.objects.filter(public_token=public_token).exists():
                            item['public_token'] = uuid.uuid4()
                        else:
                            item['public_token'] = public_token
                    except (ValueError, AttributeError):
                        # 如果 public_token 格式无效，生成新的
                        item['public_token'] = uuid.uuid4()
                else:
                    # 如果没有 public_token，生成新的
                    item['public_token'] = uuid.uuid4()

                item.pop('id', None)  # 防止主键冲突
                Problem.objects.create(created_by=request.user, **item)

            #messages.success(request, f'import {len(data)} items successfully！')
            return JsonResponse({'message': f'import {len(data)} items successfully', 'error': None})
        except Exception as e:
            detail = f'{type(e).__name__}' 
            return JsonResponse({'status': 'error', 'error': f'failed to import：{detail}: please check inputted password firstly!'}, status=400)
    # GET 请求禁止访问
    return redirect('problem_list')



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
        print('[DEBUG]========== selected_ids ==========', selected_ids) 
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



@superuser_required
def sensitive_word_list(request):
    """敏感词列表"""
    words = SensitiveWord.objects.all().order_by('-created_at')
    return render(request, 'problems/sensitive_word_list.html', {'words': words})

@superuser_required
def sensitive_word_add(request):
    """添加敏感词"""
    if request.method == 'POST':
        form = SensitiveWordForm(request.POST)
        if form.is_valid():
            form.save()
            # 清除缓存
            SensitiveDataProcessor.clear_sensitive_words_cache()
            messages.success(request, 'Succeed to add')
            return redirect('sensitive_word_list')
    else:
        form = SensitiveWordForm()
    return render(request, 'problems/sensitive_word_form.html', {'form': form, 'action': 'Add'})

@superuser_required
def sensitive_word_edit(request, pk):
    """编辑敏感词"""
    word = get_object_or_404(SensitiveWord, pk=pk)
    if request.method == 'POST':
        form = SensitiveWordForm(request.POST, instance=word)
        if form.is_valid():
            form.save()
            # 清除缓存
            SensitiveDataProcessor.clear_sensitive_words_cache()
            messages.success(request, 'Succeed to update')
            return redirect('sensitive_word_list')
    else:
        form = SensitiveWordForm(instance=word)
    return render(request, 'problems/sensitive_word_form.html', {'form': form, 'action': 'Edit'})

@superuser_required
def sensitive_word_toggle(request, pk):
    """启用/禁用敏感词"""
    word = get_object_or_404(SensitiveWord, pk=pk)
    word.is_active = not word.is_active
    word.save()
    # 清除缓存
    SensitiveDataProcessor.clear_sensitive_words_cache()
    status = "Actived" if word.is_active else "Deactived"
    messages.success(request, f'sensitive has been {status}')
    return redirect('sensitive_word_list')

@superuser_required
def sensitive_word_delete(request, pk):
    """删除敏感词"""
    word = get_object_or_404(SensitiveWord, pk=pk)
    word.delete()
    # 清除缓存
    SensitiveDataProcessor.clear_sensitive_words_cache()
    messages.success(request, '敏感词已删除')
    return redirect('sensitive_word_list')


@csrf_exempt
def upload_image(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image = request.FILES['image']
        clean_name = image.name.replace(' ', '_')
        upload_images_path = os.path.join(settings.MEDIA_ROOT, 'upload_images')
        fs = FileSystemStorage(location=upload_images_path)
        filename = fs.save(clean_name, image)
        # 将图片名存储在会话中
        if 'uploaded_images' not in request.session:
            request.session['uploaded_images'] = []
        request.session['uploaded_images'].append(filename)
        request.session.modified = True

        image_url = os.path.join(settings.MEDIA_URL, 'upload_images', filename)
        return JsonResponse({'url': image_url})
    return JsonResponse({'error': 'Invalid request'}, status=400)

# 工具：列出磁盘上 upload_images 目录所有文件
def _scan_disk_upload_images():
    root = Path(settings.MEDIA_ROOT) / 'upload_images'
    if not root.exists():
        return set()
    # 保存相对路径（相对于 MEDIA_ROOT）
    return {str(p.relative_to(settings.MEDIA_ROOT)) for p in root.rglob('*') if p.is_file()}

# 工具：汇总数据库 uploaded_images 字段里所有文件
def _scan_db_referenced_images():
    referenced = set()
    for images_json in Problem.objects.exclude(uploaded_images__isnull=True).values_list('uploaded_images', flat=True):
        try:
            images = json.loads(images_json)
            if isinstance(images, list):
                referenced.update(images)
                referenced.update(f"upload_images/{name}" for name in images)
        except Exception:
            continue
    return referenced

def image_size(size_bytes):
    """把字节转成人可读单位"""
    for unit in ['B', 'KB', 'MB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} GB"

import subprocess

def home_du_human_linux():
    try:
        completed = subprocess.run(
            ['du', '-sh', os.path.expanduser('~')],
            text=True,
            capture_output=True,
            check=True
        )
        return completed.stdout.split()[0]
    except Exception as e:
        return 0

# 删除接口：POST 接受文件名列表
@require_POST
@csrf_exempt   # 如果你打算用 fetch 手动带 X-CSRFToken
@user_passes_test(lambda u: u.is_superuser)
def isolated_images_delete(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    paths = request.POST.getlist('files')  # 相对路径
    root = Path(settings.MEDIA_ROOT)
    deleted = 0
    for f in paths:
        # 简单安全校验：只允许 upload_images 下的文件
        abs_path = (root / f).resolve()
        if abs_path.is_file() and 'upload_images' in abs_path.parts:
            abs_path.unlink()
            deleted += 1
    #return JsonResponse({'deleted': deleted})
    return redirect('resource_management')

@require_POST
def clear_uploaded_images(request):
    request.session.pop('uploaded_images', None)
    return JsonResponse({'status': 'ok'})

@user_passes_test(lambda u: u.is_superuser)
def resource_management(request):

    disk_files = _scan_disk_upload_images()
    db_files = _scan_db_referenced_images()
    isolates = disk_files - db_files

    # 构造可访问的完整 URL（浏览器查看用）
    isolated_data = []
    for f in sorted(isolates):
        abs_path = Path(settings.MEDIA_ROOT) / f
        size = abs_path.stat().st_size if abs_path.is_file() else 0
        isolated_data.append({
            'path': f,
            'url': settings.MEDIA_URL.rstrip('/') + '/' + f.lstrip('/'),
            'size': size,
        })

    home_size = home_du_human_linux()

    # 大文件扫描
    threshold_kb = int(request.GET.get('kb', 512))
    large_files  = []
    root = Path(settings.MEDIA_ROOT)
    for p in root.rglob('*'):
        if p.is_file() and p.stat().st_size > threshold_kb * 1024:
            rel_path = str(p.relative_to(root))
            file_name = p.name

            # 附件匹配（相对路径）
            owners_att = Problem.objects.filter(
                Q(root_cause_file=rel_path) |
                Q(solutions_file=rel_path) |
                Q(others_file=rel_path)
            )

            # upload_images 匹配（仅文件名）
            owners_up = Problem.objects.filter(
                uploaded_images__icontains=file_name     # JSON 里包含文件名
            )

            owners = (owners_att | owners_up).distinct()

            large_files.append({
                'path': rel_path,
                'url' : settings.MEDIA_URL.rstrip('/') + '/' + rel_path.lstrip('/'),
                'size': p.stat().st_size,
                'owners': owners,
            })

    return render(request, 'problems/resource_management.html', {
        'isolates'      : isolated_data,
        'large_files'   : large_files,
        'threshold_kb'  : threshold_kb,
        'home_size'     : home_size,
    })

def view_detail(request, token):
    problem = get_object_or_404(Problem, public_token=token)
    if not problem.is_public and not (request.user.is_superuser or request.user == problem.created_by):
        return HttpResponseForbidden("This item is not publicly accessible.")


    # 一次性给前端：原始文本 + 编辑器类型
    fields = {
        f: {'text': getattr(problem, f), 'editor': getattr(problem, f'{f}_editor_type')}
        for f in ['description','root_cause','solutions','others']
    }
    return render(request, 'problems/view_detail.html', {
        'problem': problem,
        'problem_fields_json': json.dumps(fields, cls=DjangoJSONEncoder),
    })
