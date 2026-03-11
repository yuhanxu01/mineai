from functools import wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect

from accounts.models import TokenUsage, SiteConfig, VerificationCode
from hub.models import App
from memory.models import MemoryNode, Character
from novel.models import Project, Chapter
from novel_share.models import SharedNovel, SharedChapter, NovelComment, NovelFavorite
from ocr_studio.models import OCRProject, OCRPage

User = get_user_model()


def superuser_required(view_func):
    @wraps(view_func)
    @login_required(login_url='/admin/login/')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden('需要超级管理员权限')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── 首页概览 ─────────────────────────────────────────────────────────────────

@superuser_required
def index(request):
    stats = {
        'user_count': User.objects.count(),
        'active_user_count': User.objects.filter(is_active=True).count(),
        'project_count': Project.objects.count(),
        'chapter_count': Chapter.objects.count(),
        'novel_count': SharedNovel.objects.count(),
        'published_novel_count': SharedNovel.objects.filter(status='published').count(),
        'comment_count': NovelComment.objects.count(),
        'ocr_count': OCRProject.objects.count(),
        'memory_node_count': MemoryNode.objects.count(),
        'character_count': Character.objects.count(),
        'app_count': App.objects.count(),
        'code_count': VerificationCode.objects.count(),
    }
    token_agg = TokenUsage.objects.aggregate(
        total=Sum('total_tokens'),
        total_prompt=Sum('prompt_count'),
    )
    stats['total_tokens'] = token_agg['total'] or 0
    stats['total_prompts'] = token_agg['total_prompt'] or 0

    recent_users = User.objects.order_by('-date_joined' if hasattr(User, 'date_joined') else '-id')[:5]
    recent_novels = SharedNovel.objects.order_by('-created_at')[:5]
    recent_comments = NovelComment.objects.order_by('-created_at')[:5]

    return render(request, 'dashboard/index.html', {
        'stats': stats,
        'recent_users': recent_users,
        'recent_novels': recent_novels,
        'recent_comments': recent_comments,
        'active_nav': 'index',
    })


# ─── 用户管理 ──────────────────────────────────────────────────────────────────

@superuser_required
def user_list(request):
    q = request.GET.get('q', '')
    qs = User.objects.all().order_by('-id')
    if q:
        qs = qs.filter(email__icontains=q)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/users.html', {
        'page_obj': page,
        'q': q,
        'active_nav': 'users',
    })


@superuser_required
def user_create(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        is_superuser = request.POST.get('is_superuser') == 'on'
        if not email or not password:
            messages.error(request, '邮箱和密码不能为空')
        elif User.objects.filter(email=email).exists():
            messages.error(request, f'邮箱 {email} 已存在')
        else:
            if is_superuser:
                User.objects.create_superuser(email, password)
            else:
                User.objects.create_user(email, password)
            messages.success(request, f'用户 {email} 创建成功')
            return redirect('dashboard:user_list')
    return render(request, 'dashboard/user_form.html', {
        'action': '创建用户',
        'active_nav': 'users',
    })


@superuser_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        new_password = request.POST.get('password', '').strip()
        user.is_active = is_active
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        if new_password:
            user.set_password(new_password)
        user.save()
        messages.success(request, f'用户 {user.email} 已更新')
        return redirect('dashboard:user_list')
    try:
        token_usage = user.token_usage
    except TokenUsage.DoesNotExist:
        token_usage = None
    return render(request, 'dashboard/user_form.html', {
        'action': '编辑用户',
        'edit_user': user,
        'token_usage': token_usage,
        'active_nav': 'users',
    })


@superuser_required
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, '不能禁用自己的账号')
    else:
        user.is_active = not user.is_active
        user.save()
        status = '激活' if user.is_active else '禁用'
        messages.success(request, f'用户 {user.email} 已{status}')
    return redirect('dashboard:user_list')


@superuser_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, '不能删除自己的账号')
        else:
            email = user.email
            user.delete()
            messages.success(request, f'用户 {email} 已删除')
        return redirect('dashboard:user_list')
    return render(request, 'dashboard/confirm_delete.html', {
        'object_name': f'用户 {user.email}',
        'back_url': 'dashboard:user_list',
        'active_nav': 'users',
    })


# ─── 系统配置 ──────────────────────────────────────────────────────────────────

@superuser_required
def site_config(request):
    from core.models import APIConfig
    config = SiteConfig.get()
    api_config = APIConfig.get_active()

    if request.method == 'POST':
        form_type = request.POST.get('form_type', '')

        if form_type == 'site':
            try:
                config.code_cooldown_seconds = int(request.POST.get('code_cooldown_seconds', 300))
                config.code_expire_minutes = int(request.POST.get('code_expire_minutes', 30))
                config.code_daily_limit = int(request.POST.get('code_daily_limit', 100))
                config.code_minute_limit = int(request.POST.get('code_minute_limit', 5))
                config.save()
                messages.success(request, '验证码配置已保存')
            except (ValueError, TypeError):
                messages.error(request, '请输入有效的数字')

        elif form_type == 'api':
            new_key = request.POST.get('api_key', '').strip()
            api_base = request.POST.get('api_base', '').strip() or 'https://open.bigmodel.cn/api/paas/v4'
            chat_model = request.POST.get('chat_model', '').strip() or 'glm-4.7-flash'
            if not new_key and api_config:
                # Keep existing key if blank submitted (don't wipe it)
                new_key = api_config.api_key
            if new_key:
                if api_config:
                    api_config.api_key = new_key
                    api_config.api_base = api_base
                    api_config.chat_model = chat_model
                    api_config.save()
                else:
                    api_config = APIConfig.objects.create(
                        api_key=new_key, api_base=api_base, chat_model=chat_model
                    )
                messages.success(request, '系统 API 密钥已更新')
            else:
                messages.error(request, 'API 密钥不能为空')

        return redirect('dashboard:site_config')

    return render(request, 'dashboard/site_config.html', {
        'config': config,
        'api_config': api_config,
        'active_nav': 'config',
    })


# ─── 验证码记录 ────────────────────────────────────────────────────────────────

@superuser_required
def verification_codes(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    qs = VerificationCode.objects.order_by('-created_at')
    if q:
        qs = qs.filter(email__icontains=q)
    if status == 'used':
        qs = qs.filter(is_used=True)
    elif status == 'unused':
        qs = qs.filter(is_used=False)
    paginator = Paginator(qs, 30)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/verification_codes.html', {
        'page_obj': page,
        'q': q,
        'status': status,
        'active_nav': 'codes',
    })


@superuser_required
def code_delete(request, pk):
    code = get_object_or_404(VerificationCode, pk=pk)
    if request.method == 'POST':
        code.delete()
        messages.success(request, '验证码记录已删除')
    return redirect('dashboard:verification_codes')


# ─── 写作项目 ──────────────────────────────────────────────────────────────────

@superuser_required
def project_list(request):
    q = request.GET.get('q', '')
    qs = Project.objects.annotate(chapter_count=Count('chapters')).order_by('-updated_at')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(genre__icontains=q))
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/projects.html', {
        'page_obj': page,
        'q': q,
        'active_nav': 'projects',
    })


@superuser_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        title = project.title
        project.delete()
        messages.success(request, f'项目《{title}》已删除')
    return redirect('dashboard:project_list')


# ─── 共享小说 ──────────────────────────────────────────────────────────────────

@superuser_required
def novel_list(request):
    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    qs = SharedNovel.objects.annotate(
        chapter_count=Count('chapters', distinct=True),
        comment_count=Count('comments', distinct=True),
        favorite_count=Count('favorited_by', distinct=True),
    ).order_by('-updated_at')
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(author__email__icontains=q))
    if status_filter:
        qs = qs.filter(status=status_filter)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/novels.html', {
        'page_obj': page,
        'q': q,
        'status_filter': status_filter,
        'active_nav': 'novels',
    })


@superuser_required
def novel_toggle_status(request, pk):
    novel = get_object_or_404(SharedNovel, pk=pk)
    if request.method == 'POST':
        novel.status = 'draft' if novel.status == 'published' else 'published'
        novel.save()
        messages.success(request, f'《{novel.title}》状态已更新为 {novel.get_status_display()}')
    return redirect('dashboard:novel_list')


@superuser_required
def novel_delete(request, pk):
    novel = get_object_or_404(SharedNovel, pk=pk)
    if request.method == 'POST':
        title = novel.title
        novel.delete()
        messages.success(request, f'小说《{title}》已删除')
    return redirect('dashboard:novel_list')


# ─── 评论管理 ──────────────────────────────────────────────────────────────────

@superuser_required
def comment_list(request):
    q = request.GET.get('q', '')
    qs = NovelComment.objects.select_related('user', 'novel', 'chapter').order_by('-created_at')
    if q:
        qs = qs.filter(Q(content__icontains=q) | Q(user__email__icontains=q) | Q(novel__title__icontains=q))
    paginator = Paginator(qs, 30)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/comments.html', {
        'page_obj': page,
        'q': q,
        'active_nav': 'comments',
    })


@superuser_required
def comment_delete(request, pk):
    comment = get_object_or_404(NovelComment, pk=pk)
    if request.method == 'POST':
        comment.delete()
        messages.success(request, '评论已删除')
    return redirect('dashboard:comment_list')


# ─── Hub 应用管理 ──────────────────────────────────────────────────────────────

@superuser_required
def app_list(request):
    apps = App.objects.all()
    return render(request, 'dashboard/apps_list.html', {
        'apps': apps,
        'active_nav': 'apps',
    })


@superuser_required
def app_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip()
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon', '📦').strip()
        color = request.POST.get('color', '#c9a86c').strip()
        order = int(request.POST.get('order', 0) or 0)
        is_active = request.POST.get('is_active') == 'on'
        if not name or not slug:
            messages.error(request, '名称和标识符不能为空')
        elif App.objects.filter(slug=slug).exists():
            messages.error(request, f'标识符 {slug} 已存在')
        else:
            App.objects.create(name=name, slug=slug, description=description,
                               icon=icon, color=color, order=order, is_active=is_active)
            messages.success(request, f'应用 {name} 创建成功')
            return redirect('dashboard:app_list')
    return render(request, 'dashboard/app_form.html', {
        'action': '新建应用',
        'active_nav': 'apps',
    })


@superuser_required
def app_edit(request, pk):
    app = get_object_or_404(App, pk=pk)
    if request.method == 'POST':
        app.name = request.POST.get('name', app.name).strip()
        app.slug = request.POST.get('slug', app.slug).strip()
        app.description = request.POST.get('description', app.description).strip()
        app.icon = request.POST.get('icon', app.icon).strip()
        app.color = request.POST.get('color', app.color).strip()
        app.order = int(request.POST.get('order', app.order) or 0)
        app.is_active = request.POST.get('is_active') == 'on'
        app.save()
        messages.success(request, f'应用 {app.name} 已更新')
        return redirect('dashboard:app_list')
    return render(request, 'dashboard/app_form.html', {
        'action': '编辑应用',
        'app': app,
        'active_nav': 'apps',
    })


@superuser_required
def app_delete(request, pk):
    app = get_object_or_404(App, pk=pk)
    if request.method == 'POST':
        name = app.name
        app.delete()
        messages.success(request, f'应用 {name} 已删除')
    return redirect('dashboard:app_list')


# ─── OCR 项目 ──────────────────────────────────────────────────────────────────

@superuser_required
def ocr_list(request):
    q = request.GET.get('q', '')
    qs = OCRProject.objects.annotate(done_pages=Count('pages')).order_by('-created_at')
    if q:
        qs = qs.filter(name__icontains=q)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/ocr_projects.html', {
        'page_obj': page,
        'q': q,
        'active_nav': 'ocr',
    })


@superuser_required
def ocr_delete(request, pk):
    project = get_object_or_404(OCRProject, pk=pk)
    if request.method == 'POST':
        name = project.name
        project.delete()
        messages.success(request, f'OCR 项目 {name} 已删除')
    return redirect('dashboard:ocr_list')
