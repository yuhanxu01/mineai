from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TavernDeployment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('base_url', models.CharField(default='http://localhost:8001', help_text='SillyTavern 服务地址', max_length=300)),
                ('data_dir', models.CharField(blank=True, help_text='SillyTavern 的 data 目录绝对路径', max_length=500)),
                ('admin_handle', models.CharField(default='admin', help_text='SillyTavern 管理员账号 handle', max_length=50)),
                ('allow_frame_embed', models.BooleanField(default=True, help_text='是否允许在 MineAI 内嵌 iframe')),
                ('setup_note', models.TextField(blank=True, help_text='给用户看的说明文字')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'SillyTavern 部署配置',
            },
        ),
        migrations.CreateModel(
            name='TavernAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('handle', models.CharField(help_text='SillyTavern 用户 handle', max_length=50, unique=True)),
                ('password', models.CharField(help_text='明文密码（用于展示给用户）', max_length=200)),
                ('provisioned_at', models.DateTimeField(auto_now_add=True)),
                ('last_accessed', models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tavern_account',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'SillyTavern 账号',
                'ordering': ['-provisioned_at'],
            },
        ),
    ]
