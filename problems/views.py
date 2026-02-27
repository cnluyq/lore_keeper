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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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

from .models import SiteConfig, CvBase
from .forms import SiteConfigForm, CvBaseForm
from hashlib import pbkdf2_hmac
import base64, gzip, tarfile, io, tempfile, shutil
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

# Multi-file constants
FILE_DELIMITER = '|||'


def parse_files(file_field_value):
    """Parse 'file1.pdf|||file2.doc' -> ['file1.pdf', 'file2.doc']"""
    if not file_field_value:
        return []
    return file_field_value.split(FILE_DELIMITER)


def build_filename_string(filenames):
    """Build ['file1.pdf', 'file2.doc'] -> 'file1.pdf|||file2.doc'"""
    return FILE_DELIMITER.join(filenames)


def delete_file_from_disk(problem, field_base, filename):
    """Delete a specific file from disk for a problem. Directory: uploads/<id>/<field_base>/"""
    file_path = os.path.join(settings.MEDIA_ROOT, str(problem.id), field_base, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f'Failed to delete {file_path}: {e}')
            return False
    return False
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
    # Get search query parameter
    search_query = request.GET.get('q', '')

    # Start with base query filtered by visibility
    # Handle both authenticated and anonymous users
    if request.user.is_authenticated:
        problems = Problem.objects.filter(
            Q(created_by=request.user) | Q(is_public=True)
        ).order_by('-create_time')
    else:
        # Anonymous users only see public problems
        problems = Problem.objects.filter(
            Q(created_by__isnull=True, is_public=True) | Q(is_public=True)
        ).order_by('-create_time')

    # Apply search filter if query exists (search across ALL fields)
    if search_query:
        problems = problems.filter(
            Q(key_words__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(root_cause__icontains=search_query) |
            Q(solutions__icontains=search_query) |
            Q(others__icontains=search_query) |
            Q(created_by__username__icontains=search_query)
        )

    # Paginate results (use site config)
    items_per_page = SiteConfig.get_config().items_per_page
    paginator = Paginator(problems, items_per_page)
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Serialize current page data only
    data = [
        {
            'id': p.id,
            'key_words': p.key_words,
            'title': p.title,
            'description': p.description,
            'description_editor_type': p.description_editor_type,
            'root_cause': p.root_cause,
            'root_cause_editor_type': p.root_cause_editor_type,
            'root_cause_file': p.root_cause_file.name if p.root_cause_file and p.root_cause_file.name else None,
            'solutions': p.solutions,
            'solutions_editor_type': p.solutions_editor_type,
            'solutions_file': p.solutions_file.name if p.solutions_file and p.solutions_file.name else None,
            'others': p.others,
            'others_editor_type': p.others_editor_type,
            'others_file': p.others_file.name if p.others_file and p.others_file.name else None,
            'create_time': p.create_time.strftime('%Y-%m-%d %H:%M'),
            'update_time': p.update_time.strftime('%Y-%m-%d %H:%M'),
            'created_by': p.created_by.username if p.created_by else '-',
            'public_token': str(p.public_token),
            'is_public': p.is_public,
        }
        for p in page_obj
    ]

    context = {
        'problems_json': json.dumps(data, ensure_ascii=False),
        'page_obj': page_obj,
        'search_query': search_query,
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
    if request.method == 'POST':
        form = ProblemForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, 'problems/problem_form.html', {
                'form': form,
                'action': 'Add'
            })

        # 敏感词验证
        processed_form, error_msg = SensitiveDataProcessor.validate_and_process_form(form, request)
        # 保存对象
        obj = processed_form.save(commit=False)
        obj.created_by = request.user

        # Store uploaded files info before saving (save won't be able to use FileField directly)
        file_info = {}

        # Use a unique temp directory for this request
        import time
        temp_id = str(int(time.time() * 1000))

        # Handle multiple file uploads for each field BEFORE saving obj
        for field_base in ['root_cause', 'solutions', 'others']:
            field_name = f'{field_base}_files'  # from request.FILES
            if field_name in request.FILES:
                files = request.FILES.getlist(field_name)
                filenames = []
                upload_dir = os.path.join(settings.MEDIA_ROOT, f'{field_base}/temp_{temp_id}/')
                os.makedirs(upload_dir, exist_ok=True)

                max_size = SiteConfig.get_config().get_max_file_size_bytes()
                config = SiteConfig.get_config()
                size_str = f"{config.max_file_size}{config.max_file_size_unit}"

                for f in files:
                    # Validate file size
                    if f.size > max_size:
                        messages.warning(request, f'File {f.name} exceeds {size_str} limit and was skipped.')
                        continue

                    # Clean filename
                    clean_name = f.name.replace(' ', '_').replace('/', '_').replace('\\', '_')

                    # Save file manually to temp directory first
                    fs = FileSystemStorage(location=upload_dir)
                    filename = fs.save(clean_name, f)
                    filenames.append(filename)

                file_info[field_base] = filenames

        # Now save the object to get an ID
        obj.save()

        # Move files from temp to final directory and update database
        from django.db import connection
        cursor = connection.cursor()

        for field_base, filenames in file_info.items():
            if filenames:
                # Create final directory: uploads/<obj.id>/<field_base>/
                final_dir = os.path.join(settings.MEDIA_ROOT, str(obj.id), field_base)
                os.makedirs(final_dir, exist_ok=True)

                # Move files from temp directory
                temp_dir = os.path.join(settings.MEDIA_ROOT, f'{field_base}/temp_{temp_id}/')
                for filename in filenames:
                    src = os.path.join(temp_dir, filename)
                    dst = os.path.join(final_dir, filename)
                    if os.path.exists(src):
                        os.rename(src, dst)
                    else:
                        # Already moved or doesn't exist
                        continue

                # Update database directly to store the concatenated string
                table_name = Problem._meta.db_table
                file_field_column = f'{field_base}_file'
                file_string = build_filename_string(filenames)

                cursor.execute(
                    f"UPDATE {table_name} SET {file_field_column} = %s WHERE id = %s",
                    [file_string, obj.id]
                )

        # Clean up temp directories (both old and new patterns)
        for field_base in ['root_cause', 'solutions', 'others']:
            # Clean up the temp directory we used for this request
            temp_dir = os.path.join(settings.MEDIA_ROOT, f'{field_base}/temp_{temp_id}/')
            if os.path.isdir(temp_dir):
                # Clean up remaining files
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass
                try:
                    os.rmdir(temp_dir)
                except:
                    pass

            # Clean up any leftover old temp directories
            old_temp_dir = os.path.join(settings.MEDIA_ROOT, f'{field_base}/temp/')
            if os.path.isdir(old_temp_dir):
                for filename in os.listdir(old_temp_dir):
                    file_path = os.path.join(old_temp_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass
                try:
                    os.rmdir(old_temp_dir)
                except:
                    pass

            # Clean up empty field directories at old path (field_base/)
            old_field_dir = os.path.join(settings.MEDIA_ROOT, field_base)
            if os.path.isdir(old_field_dir) and not os.listdir(old_field_dir):
                try:
                    os.rmdir(old_field_dir)
                except:
                    pass

        # Reload object from database to get updated file fields
        obj.refresh_from_db()

        # 将会话中的图片路径转移到 uploaded_images 字段中 (using direct SQL to avoid Django file validation)
        if 'uploaded_images' in request.session:
            from django.db import connection
            cursor = connection.cursor()
            table_name = Problem._meta.db_table
            cursor.execute(
                f"UPDATE {table_name} SET uploaded_images = %s WHERE id = %s",
                [json.dumps(request.session['uploaded_images']), obj.id]
            )
            del request.session['uploaded_images']

        # 如果有脱敏操作，可以给用户提示
        if error_msg and "Content has been desensitized" in error_msg:
            messages.info(request, error_msg)

        # 添加成功消息
        messages.success(request, 'Item added successfully!')

        return redirect('problem_list')
    else:
        form = ProblemForm()
        # Get file size config for frontend validation
        config = SiteConfig.get_config()
        max_file_size_bytes = config.get_max_file_size_bytes()
        max_file_size_str = f"{config.max_file_size}{config.max_file_size_unit}"
    return render(request, 'problems/problem_form.html', {
        'form': form,
        'action': 'Add',
        'max_file_size_bytes': max_file_size_bytes,
        'max_file_size_str': max_file_size_str
    })

@login_required
@owner_or_superuser_required
def problem_edit(request, pk):
    problem = get_object_or_404(Problem, pk=pk)
    if not problem.is_public and not (request.user == problem.created_by or request.user.is_superuser):
        raise PermissionDenied

    if request.method == 'POST':
        form = ProblemForm(request.POST, request.FILES, instance=problem)
        if not form.is_valid():
            return render(request, 'problems/problem_form.html', {
                'form': form,
                'action': 'Edit'
            })

        # 敏感词验证
        processed_form, error_msg = SensitiveDataProcessor.validate_and_process_form(form, request)

        try:
            # Store file deletions and updates for ALL fields that need changes
            files_to_remove = {}  # {field_base: [filenames to remove]}
            uploaded_files = {}

            # Handle file deletions from POST data
            for field_base in ['root_cause', 'solutions', 'others']:
                delete_list = request.POST.getlist(f'{field_base}_files_delete')
                if delete_list:
                    files_to_remove[field_base] = delete_list
                    # Delete from disk
                    for filename in delete_list:
                        delete_file_from_disk(problem, field_base, filename)

            # Handle new file uploads
            for field_base in ['root_cause', 'solutions', 'others']:
                field_name = f'{field_base}_files'
                if field_name in request.FILES:
                    files = request.FILES.getlist(field_name)
                    # Use correct directory structure: uploads/<id>/<field_base>/
                    upload_dir = os.path.join(settings.MEDIA_ROOT, str(problem.id), field_base)
                    os.makedirs(upload_dir, exist_ok=True)

                    filenames = []
                    # Get file size limit once for this upload batch
                    max_size = SiteConfig.get_config().get_max_file_size_bytes()
                    config = SiteConfig.get_config()
                    size_str = f"{config.max_file_size}{config.max_file_size_unit}"

                    for f in files:
                        # Validate file size
                        if f.size > max_size:
                            messages.warning(request, f'File {f.name} exceeds {size_str} limit and was skipped.')
                            continue

                        # Clean filename
                        clean_name = f.name.replace(' ', '_').replace('/', '_').replace('\\', '_')

                        # Save file manually to correct directory
                        fs = FileSystemStorage(location=upload_dir)
                        filename = fs.save(clean_name, f)
                        filenames.append(filename)

                    if filenames:
                        uploaded_files[field_base] = filenames

            # Save other form fields WITHOUT touching file fields
            problem.key_words = processed_form.cleaned_data.get('key_words', problem.key_words)
            problem.title = processed_form.cleaned_data.get('title', problem.title)
            problem.description = processed_form.cleaned_data.get('description', problem.description)
            problem.description_editor_type = processed_form.cleaned_data.get('description_editor_type', problem.description_editor_type)
            problem.root_cause = processed_form.cleaned_data.get('root_cause', problem.root_cause)
            problem.root_cause_editor_type = processed_form.cleaned_data.get('root_cause_editor_type', problem.root_cause_editor_type)
            problem.solutions = processed_form.cleaned_data.get('solutions', problem.solutions)
            problem.solutions_editor_type = processed_form.cleaned_data.get('solutions_editor_type', problem.solutions_editor_type)
            problem.others = processed_form.cleaned_data.get('others', problem.others)
            problem.others_editor_type = processed_form.cleaned_data.get('others_editor_type', problem.others_editor_type)
            problem.is_public = processed_form.cleaned_data.get('is_public', problem.is_public)

            # Use update_fields to only update specific fields (excluding file fields)
            update_fields = ['key_words', 'title', 'description', 'root_cause', 'solutions', 'others',
                            'description_editor_type', 'root_cause_editor_type', 'solutions_editor_type',
                            'others_editor_type', 'is_public', 'update_time']
            if 'uploaded_images' in request.session:
                if problem.uploaded_images:
                    uploaded_images = json.loads(problem.uploaded_images)
                else:
                    uploaded_images = []
                uploaded_images.extend(request.session['uploaded_images'])
                problem.uploaded_images = json.dumps(uploaded_images)
                del request.session['uploaded_images']
                update_fields.append('uploaded_images')

            # Process file field updates BEFORE saving the object
            # This ensures file updates are done correctly and won't be lost
            from django.db import connection

            # Only update if there are files to remove or new uploads
            fields_to_update = set(files_to_remove.keys()) | set(uploaded_files.keys())
            if fields_to_update:
                cursor = connection.cursor()
                table_name = Problem._meta.db_table

                for field_base in fields_to_update:
                    file_field_column = f'{field_base}_file'

                    # Get current value from database
                    cursor.execute(
                        f"SELECT {file_field_column} FROM {table_name} WHERE id = %s",
                        [problem.id]
                    )
                    current_value = cursor.fetchone()[0]

                    # Parse existing filenames
                    existing_filenames = []
                    if current_value:
                        existing_filenames = parse_files(current_value)

                    # Remove files marked for deletion
                    if field_base in files_to_remove:
                        for filename in files_to_remove[field_base]:
                            if filename in existing_filenames:
                                existing_filenames.remove(filename)

                    # Add new upload filenames
                    if field_base in uploaded_files:
                        existing_filenames.extend(uploaded_files[field_base])

                    # Update database with final file list
                    final_value = build_filename_string(existing_filenames) if existing_filenames else None
                    cursor.execute(
                        f"UPDATE {table_name} SET {file_field_column} = %s WHERE id = %s",
                        [final_value, problem.id]
                    )

            # Now save the object after file fields have been updated
            problem.save(update_fields=update_fields)

            # Reload object from database to get updated file fields
            problem.refresh_from_db()

            # 如果有脱敏操作，可以给用户提示
            if error_msg and "Content has been desensitized" in error_msg:
                messages.info(request, error_msg)

            messages.success(request, 'Item updated successfully!')

            return redirect('problem_list')
        except Exception as e:
            # 处理过程中出现异常
            print(f"Error during form processing: {e}")
            messages.error(request, f'Error saving item: {str(e)}')
            return render(request, 'problems/problem_form.html', {
                'form': form,
                'action': 'Edit',
                'problem': problem
            })
    else:
        form = ProblemForm(instance=problem)
        # Get file size config for frontend validation
        config = SiteConfig.get_config()
        max_file_size_bytes = config.get_max_file_size_bytes()
        max_file_size_str = f"{config.max_file_size}{config.max_file_size_unit}"
    return render(request, 'problems/problem_form.html', {
        'form': form,
        'action': 'Edit',
        'problem': problem,
        'max_file_size_bytes': max_file_size_bytes,
        'max_file_size_str': max_file_size_str
    })

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

    # 创建 tar.gz 打包：items.json + uploads/
    export_buffer = io.BytesIO()

    with tarfile.open(fileobj=export_buffer, mode='w:gz') as tar:
        # 1. 添加 items.json
        json_data = json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2).encode()
        json_file = io.BytesIO(json_data)
        tarinfo = tarfile.TarInfo(name='items.json')
        tarinfo.size = len(json_data)
        tar.addfile(tarinfo, json_file)

        # 2. 添加 uploads 目录
        uploads_path = Path(settings.MEDIA_ROOT)
        if uploads_path.exists():
            # 添加所有按 Problem ID 命名的目录
            for item_dir in uploads_path.iterdir():
                if item_dir.is_dir() and item_dir.name.isdigit():
                    # 递归添加整个目录，保持结构
                    tar.add(item_dir, arcname=f'uploads/{item_dir.name}')

            # 添加 upload_images 目录
            upload_images_dir = uploads_path / 'upload_images'
            if upload_images_dir.exists():
                tar.add(upload_images_dir, arcname='uploads/upload_images')

    # 加密整个 tar.gz 数据
    cipher = ChaCha20Poly1305(key)
    nonce = os.urandom(12)
    encrypted = cipher.encrypt(nonce, export_buffer.getvalue(), associated_data=None)

    blob = nonce + encrypted

    response = HttpResponse(blob, content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename="items_with_uploads.bin"'
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
            decrypted = cipher.decrypt(nonce, ct, associated_data=None)

            # 解压 tar.gz 到临时目录
            import_buffer = io.BytesIO(decrypted)
            tmp_dir = tempfile.mkdtemp()

            try:
                with tarfile.open(fileobj=import_buffer, mode='r:gz') as tar:
                    tar.extractall(tmp_dir)

                # 读取 items.json
                with open(os.path.join(tmp_dir, 'items.json'), 'r') as f:
                    data = json.loads(f.read())

                # ID 映射：original_id -> new_id
                id_mapping = {}

                for item in data:
                    original_id = item.get('id')

                    # 设置默认值
                    item.setdefault('description_editor_type', 'plain')
                    item.setdefault('root_cause_editor_type', 'plain')
                    item.setdefault('solutions_editor_type', 'plain')
                    item.setdefault('others_editor_type', 'plain')

                    # 处理 public_token
                    public_token = item.get('public_token')
                    if public_token:
                        try:
                            uuid.UUID(public_token)
                            if Problem.objects.filter(public_token=public_token).exists():
                                item['public_token'] = uuid.uuid4()
                        except (ValueError, AttributeError):
                            item['public_token'] = uuid.uuid4()
                    else:
                        item['public_token'] = uuid.uuid4()

                    # 移除 id，让 Django 生成新的
                    item.pop('id', None)

                    # 创建新 Problem
                    new_problem = Problem.objects.create(created_by=request.user, **item)

                    # 记录 ID 映射
                    id_mapping[original_id] = new_problem.id

                # 处理 uploads 目录
                import_dir = os.path.join(tmp_dir, 'uploads')
                if os.path.exists(import_dir):
                    uploads_root = Path(settings.MEDIA_ROOT)
                    uploads_root.mkdir(parents=True, exist_ok=True)

                    # 遍历 uploads 中的目录（按原始 ID 命名）
                    for original_id_dir_name in sorted(os.listdir(import_dir)):
                        # 跳过 upload_images（单独处理）
                        if original_id_dir_name == 'upload_images':
                            continue

                        if original_id_dir_name.isdigit():
                            original_id = int(original_id_dir_name)
                            new_id = id_mapping.get(original_id)

                            if new_id:
                                # 创建新目录
                                new_dir = uploads_root / str(new_id)
                                new_dir.mkdir(parents=True, exist_ok=True)

                                # 复制旧目录的所有内容到新目录
                                src_dir = os.path.join(import_dir, str(original_id))

                                for item_name in os.listdir(src_dir):
                                    src_item = os.path.join(src_dir, item_name)
                                    if os.path.isdir(src_item):
                                        # 复制子目录（root_cause, solutions, others）
                                        shutil.copytree(src_item, new_dir / item_name,
                                                      dirs_exist_ok=True)

                    # 处理 upload_images 目录
                    upload_images_src = os.path.join(import_dir, 'upload_images')
                    if os.path.exists(upload_images_src):
                        upload_images_dst = uploads_root / 'upload_images'
                        upload_images_dst.mkdir(parents=True, exist_ok=True)

                        for image_file in os.listdir(upload_images_src):
                            src_file = os.path.join(upload_images_src, image_file)
                            if os.path.isfile(src_file):
                                shutil.copy2(src_file, upload_images_dst / image_file)

                return JsonResponse({
                    'message': f'import {len(data)} items successfully',
                    'error': None,
                    'id_mapping_count': len(id_mapping)
                })

            finally:
                # 清理临时目录
                shutil.rmtree(tmp_dir, ignore_errors=True)

        except Exception as e:
            detail = f'{type(e).__name__}'
            return JsonResponse({
                'status': 'error',
                'error': f'failed to import：{detail}: please check inputted password firstly!'
            }, status=400)

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

        # Validate file size before saving
        max_size = SiteConfig.get_config().get_max_file_size_bytes()
        config = SiteConfig.get_config()
        size_str = f"{config.max_file_size}{config.max_file_size_unit}"

        if image.size > max_size:
            return JsonResponse({
                'error': f'Image size exceeds {size_str} limit'
            }, status=400)

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
    import re
    
    # 扫描 Problem 模型的 uploaded_images 字段
    for images_json in Problem.objects.exclude(uploaded_images__isnull=True).values_list('uploaded_images', flat=True):
        try:
            images = json.loads(images_json)
            if isinstance(images, list):
                referenced.update(images)
                referenced.update(f"upload_images/{name}" for name in images)
        except Exception:
            continue
    
    # 扫描 CvBase 模型的 content 字段中的图片引用
    cv_base_content_pattern = r'!\[.*?\]\(/uploads/upload_images/([^)]+)\)|<img[^>]+src=["\']/uploads/upload_images/([^"\']+)["\']'
    
    for record in CvBase.objects.filter(content_editor_type='markdown').exclude(content__isnull=True).exclude(content=''):
        content = record.content
        if content:
            matches = re.findall(cv_base_content_pattern, content)
            for match in matches:
                # match 是一个元组 (markdown_img_filename, html_img_filename)
                # 其中一个为空，另一个有值
                filename = match[0] if match[0] else match[1]
                if filename:
                    referenced.add(filename)
                    referenced.add(f"upload_images/{filename}")
    
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

    def has_filename_in_file_field(file_field_value, filename):
        """检查文件字段是否包含指定的文件名"""
        if not file_field_value:
            return False
        # 文件字段存储格式: 'file1.pdf|||file2.pdf'
        filenames = file_field_value.split(FILE_DELIMITER)
        return filename in filenames

    def has_filename_in_uploaded_images(uploaded_images_json, filename):
        """检查 uploaded_images JSON 是否包含指定文件名"""
        if not uploaded_images_json:
            return False
        try:
            images = json.loads(uploaded_images_json)
            if isinstance(images, list):
                return filename in images
        except (json.JSONDecodeError, TypeError):
            pass
        return False

    for p in root.rglob('*'):
        if p.is_file() and p.stat().st_size > threshold_kb * 1024:
            rel_path = str(p.relative_to(root))
            file_name = p.name

            owners = []

            # 解析路径结构
            parts = rel_path.split('/')
            if parts and parts[0].isdigit() and len(parts) >= 3:
                # MEDIA_ROOT 下：<id>/<field>/<filename>
                # 例如: 2/root_cause/ccr_config_example2.json
                try:
                    problem_id = int(parts[0])
                    field_name = parts[1]  # 'root_cause', 'solutions', 'others'

                    # 精确查询指定 ID 的 Problem
                    problem = Problem.objects.filter(id=problem_id).first()
                    if problem:
                        field_column = f'{field_name}_file'
                        file_field_obj = getattr(problem, field_column)
                        # 获取 FileField 的 name 属性（字符串）
                        file_field_value = file_field_obj.name if file_field_obj else None

                        # 检查该字段是否包含该文件名
                        if has_filename_in_file_field(file_field_value, file_name):
                            owners.append(problem)
                except (ValueError, IndexError):
                    pass

            elif parts and parts[0] == 'upload_images' and len(parts) >= 2:
                # upload_images/<filename> - 在所有 uploaded_images 中搜索
                for problem in Problem.objects.all():
                    if has_filename_in_uploaded_images(problem.uploaded_images, file_name):
                        owners.append(problem)

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



@superuser_required
def site_config_edit(request):
    config = SiteConfig.get_config()

    if request.method == 'POST':
        form = SiteConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuration updated successfully!')
            return redirect('site_config_edit')
    else:
        form = SiteConfigForm(instance=config)

    return render(request, 'problems/site_config_edit.html', {
        'form': form,
        'config': config,
    })

# ---------- CV Base Views ----------
@login_required
def cv_base_list(request):
    cv_records = CvBase.objects.filter(created_by=request.user).order_by('-record_date')
    
    # Group records by year and month
    grouped_records = {}
    for record in cv_records:
        year = record.record_date.year
        month = record.record_date.month
        if year not in grouped_records:
            grouped_records[year] = {}
        if month not in grouped_records[year]:
            grouped_records[year][month] = []
        grouped_records[year][month].append(record)

    context = {
        'grouped_records': grouped_records,
        'user': request.user,
    }
    return render(request, 'problems/cv_base_list.html', context)

@login_required
def cv_base_edit(request, pk):
    cv_record = get_object_or_404(CvBase, pk=pk)
    if cv_record.created_by != request.user and not request.user.is_superuser:
        raise PermissionDenied

    action = 'Edit' if cv_record.title or cv_record.content else 'Add'

    if request.method == 'POST':
        form = CvBaseForm(request.POST, request.FILES, instance=cv_record)
        if not form.is_valid():
            config = SiteConfig.get_config()
            max_file_size_bytes = config.get_max_file_size_bytes()
            max_file_size_str = f"{config.max_file_size}{config.max_file_size_unit}"
            return render(request, 'problems/cv_base_form.html', {
                'form': form,
                'action': action,
                'cv_record': cv_record,
                'max_file_size_bytes': max_file_size_bytes,
                'max_file_size_str': max_file_size_str
            })

        try:
            # Handle file deletions
            delete_list = request.POST.getlist('content_files_delete')
            if delete_list:
                for filename in delete_list:
                    delete_file_from_disk_cvbase(cv_record, 'content', filename)
                # Update database to remove deleted files from the list
                from django.db import connection
                cursor = connection.cursor()
                table_name = CvBase._meta.db_table
                
                # Get current file list from database
                cursor.execute(
                    f"SELECT content_file FROM {table_name} WHERE id = %s",
                    [cv_record.id]
                )
                current_value = cursor.fetchone()[0]
                
                # Parse existing filenames
                existing_filenames = []
                if current_value:
                    existing_filenames = parse_files(current_value)
                
                # Remove files marked for deletion
                for filename in delete_list:
                    if filename in existing_filenames:
                        existing_filenames.remove(filename)
                
                # Update database with final file list
                final_value = build_filename_string(existing_filenames) if existing_filenames else None
                cursor.execute(
                    f"UPDATE {table_name} SET content_file = %s WHERE id = %s",
                    [final_value, cv_record.id]
                )
                # Refresh the record to get updated file field
                cv_record.refresh_from_db()

            # Handle new file uploads
            if 'content_files' in request.FILES:
                files = request.FILES.getlist('content_files')
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'cv_base', str(cv_record.id), 'content')
                os.makedirs(upload_dir, exist_ok=True)

                filenames = []
                max_size = SiteConfig.get_config().get_max_file_size_bytes()
                config = SiteConfig.get_config()
                size_str = f"{config.max_file_size}{config.max_file_size_unit}"

                for f in files:
                    if f.size > max_size:
                        messages.warning(request, f'File {f.name} exceeds {size_str} limit and was skipped.')
                        continue

                    clean_name = f.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                    fs = FileSystemStorage(location=upload_dir)
                    filename = fs.save(clean_name, f)
                    filenames.append(filename)

                if filenames:
                    # Add new files to existing files
                    existing_files = cv_record.get_content_files()
                    existing_files.extend(filenames)
                    from django.db import connection
                    cursor = connection.cursor()
                    table_name = CvBase._meta.db_table
                    file_string = build_filename_string(existing_files) if existing_files else None
                    cursor.execute(
                        f"UPDATE {table_name} SET content_file = %s WHERE id = %s",
                        [file_string, cv_record.id]
                    )

            # Save form fields
            cv_record.title = form.cleaned_data.get('title', cv_record.title)
            cv_record.content = form.cleaned_data.get('content', cv_record.content)
            cv_record.content_editor_type = form.cleaned_data.get('content_editor_type', cv_record.content_editor_type)

            # Handle record_date update
            new_record_date_str = request.POST.get('record_date')
            if new_record_date_str:
                try:
                    from datetime import datetime
                    new_record_date = datetime.strptime(new_record_date_str, '%Y-%m-%d').date()

                    # Check if date is already used by another record
                    if CvBase.objects.filter(
                        created_by=request.user,
                        record_date=new_record_date
                    ).exclude(pk=cv_record.pk).exists():
                        messages.error(request, f'A record already exists for {new_record_date}. Please choose a different date.')
                        config = SiteConfig.get_config()
                        max_file_size_bytes = config.get_max_file_size_bytes()
                        max_file_size_str = f"{config.max_file_size}{config.max_file_size_unit}"
                        return render(request, 'problems/cv_base_form.html', {
                            'form': form,
                            'action': action,
                            'cv_record': cv_record,
                            'max_file_size_bytes': max_file_size_bytes,
                            'max_file_size_str': max_file_size_str
                        })

                    cv_record.record_date = new_record_date
                    update_fields = ['title', 'content', 'content_editor_type', 'record_date', 'update_time']
                except ValueError:
                    messages.error(request, 'Invalid date format')
                    config = SiteConfig.get_config()
                    max_file_size_bytes = config.get_max_file_size_bytes()
                    max_file_size_str = f"{config.max_file_size}{config.max_file_size_unit}"
                    return render(request, 'problems/cv_base_form.html', {
                        'form': form,
                        'action': action,
                        'cv_record': cv_record,
                        'max_file_size_bytes': max_file_size_bytes,
                        'max_file_size_str': max_file_size_str
                    })
            else:
                update_fields = ['title', 'content', 'content_editor_type', 'update_time']

            cv_record.save(update_fields=update_fields)
            
            cv_record.refresh_from_db()
            messages.success(request, 'CV record updated successfully!')
            return redirect('cv_base_list')
        
        except Exception as e:
            print(f"Error during form processing: {e}")
            messages.error(request, f'Error saving record: {str(e)}')
            return render(request, 'problems/cv_base_form.html', {
                'form': form,
                'action': action
            })
    else:
        form = CvBaseForm(instance=cv_record)
        config = SiteConfig.get_config()
        max_file_size_bytes = config.get_max_file_size_bytes()
        max_file_size_str = f"{config.max_file_size}{config.max_file_size_unit}"

    return render(request, 'problems/cv_base_form.html', {
        'form': form,
        'action': action,
        'cv_record': cv_record,
        'max_file_size_bytes': max_file_size_bytes,
        'max_file_size_str': max_file_size_str
    })

@login_required
def cv_base_add(request):
    if request.method == 'POST':
        form = CvBaseForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, 'problems/cv_base_form.html', {
                'form': form,
                'action': 'Add'
            })

        obj = form.save(commit=False)
        obj.created_by = request.user

        # Handle file uploads
        file_info = {}
        import time
        temp_id = str(int(time.time() * 1000))

        if 'content_files' in request.FILES:
            files = request.FILES.getlist('content_files')
            filenames = []
            upload_dir = os.path.join(settings.MEDIA_ROOT, f'content/temp_{temp_id}/')
            os.makedirs(upload_dir, exist_ok=True)

            max_size = SiteConfig.get_config().get_max_file_size_bytes()
            config = SiteConfig.get_config()
            size_str = f"{config.max_file_size}{config.max_file_size_unit}"

            for f in files:
                if f.size > max_size:
                    messages.warning(request, f'File {f.name} exceeds {size_str} limit and was skipped.')
                    continue

                clean_name = f.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                fs = FileSystemStorage(location=upload_dir)
                filename = fs.save(clean_name, f)
                filenames.append(filename)

            file_info['content'] = filenames

        obj.save()

        # Move files from temp to final directory
        from django.db import connection
        cursor = connection.cursor()

        for field_base, filenames in file_info.items():
            if filenames:
                final_dir = os.path.join(settings.MEDIA_ROOT, 'cv_base', str(obj.id), field_base)
                os.makedirs(final_dir, exist_ok=True)

                temp_dir = os.path.join(settings.MEDIA_ROOT, f'{field_base}/temp_{temp_id}/')
                for filename in filenames:
                    src = os.path.join(temp_dir, filename)
                    dst = os.path.join(final_dir, filename)
                    if os.path.exists(src):
                        os.rename(src, dst)

                table_name = CvBase._meta.db_table
                file_field_column = f'{field_base}_file'
                file_string = build_filename_string(filenames)

                cursor.execute(
                    f"UPDATE {table_name} SET {file_field_column} = %s WHERE id = %s",
                    [file_string, obj.id]
                )

        # Clean up temp directories
        for field_base in ['content']:
            temp_dir = os.path.join(settings.MEDIA_ROOT, f'{field_base}/temp_{temp_id}/')
            if os.path.isdir(temp_dir):
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass
                try:
                    os.rmdir(temp_dir)
                except:
                    pass

            old_temp_dir = os.path.join(settings.MEDIA_ROOT, f'{field_base}/temp/')
            if os.path.isdir(old_temp_dir):
                for filename in os.listdir(old_temp_dir):
                    file_path = os.path.join(old_temp_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass
                try:
                    os.rmdir(old_temp_dir)
                except:
                    pass

        obj.refresh_from_db()
        messages.success(request, 'CV record added successfully!')
        return redirect('cv_base_list')
    else:
        form = CvBaseForm()
        config = SiteConfig.get_config()
        max_file_size_bytes = config.get_max_file_size_bytes()
        max_file_size_str = f"{config.max_file_size}{config.max_file_size_unit}"

    return render(request, 'problems/cv_base_form.html', {
        'form': form,
        'action': 'Add',
        'max_file_size_bytes': max_file_size_bytes,
        'max_file_size_str': max_file_size_str
    })

@login_required
def cv_base_delete(request, pk):
    cv_record = get_object_or_404(CvBase, pk=pk)
    if cv_record.created_by != request.user and not request.user.is_superuser:
        raise PermissionDenied
    cv_record.delete()
    return redirect('cv_base_list')

@login_required
def cv_base_detail(request, pk):
    cv_record = get_object_or_404(CvBase, pk=pk)
    if cv_record.created_by != request.user and not request.user.is_superuser:
        raise HttpResponseForbidden("You don't have permission to view this record.")
    
    fields = {
        'content': {'text': cv_record.content, 'editor': cv_record.content_editor_type}
    }
    return render(request, 'problems/cv_base_detail.html', {
        'cv_record': cv_record,
        'cv_fields_json': json.dumps(fields, cls=DjangoJSONEncoder),
    })

@login_required
def cv_base_calendar_days(request):
    """API to get existing dates for calendar"""
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if not year or not month:
        return JsonResponse({'error': 'Year and month required'}, status=400)
    
    try:
        year = int(year)
        month = int(month)
    except ValueError:
        return JsonResponse({'error': 'Invalid year or month'}, status=400)
    
    existing_dates = list(
        CvBase.objects.filter(
            created_by=request.user,
            record_date__year=year,
            record_date__month=month
        ).values_list('record_date__day', flat=True)
    )
    
    return JsonResponse({'existing_dates': existing_dates})

@login_required
def cv_base_create_by_date(request):
    """Create CV record for specific date"""
    if request.method == 'POST':
        body = json.loads(request.body)
        date_str = body.get('date')
        if not date_str:
            return JsonResponse({'error': 'Date required'}, status=400)

        try:
            from datetime import datetime
            record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)

        # Check if date already exists
        existing_record = CvBase.objects.filter(
            created_by=request.user,
            record_date=record_date
        ).first()

        if existing_record:
            # Return URL to edit the existing record
            return JsonResponse({
                'redirect_url': f'/cv-base/edit/{existing_record.id}/',
                'record_id': existing_record.id,
                'existing': True
            })

        # Create new record and redirect to edit
        cv_record = CvBase.objects.create(
            record_date=record_date,
            title='',
            content='',
            created_by=request.user
        )

        return JsonResponse({
            'redirect_url': f'/cv-base/edit/{cv_record.id}/',
            'record_id': cv_record.id,
            'existing': False
        })

    return JsonResponse({'error': 'Method not allowed'}, status=405)

def delete_file_from_disk_cvbase(cv_base, field_base, filename):
    """Delete a specific file from disk for a cv_base record. Directory: uploads/cv_base/<id>/<field_base>/"""
    file_path = os.path.join(settings.MEDIA_ROOT, 'cv_base', str(cv_base.id), field_base, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f'Failed to delete {file_path}: {e}')
            return False
    return False

def cv_base_owner_or_superuser_required(view_func):
    """Allow creator or superuser"""
    def _wrapped_view(request, *args, **kwargs):
        pk = kwargs.get('pk')
        obj = get_object_or_404(CvBase, pk=pk)
        if request.user.is_superuser or obj.created_by == request.user:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view