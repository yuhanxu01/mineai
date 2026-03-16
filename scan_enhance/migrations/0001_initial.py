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
            name='ScanProject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=512, verbose_name='文件名')),
                ('total_pages', models.IntegerField(default=1, verbose_name='总页数')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                           related_name='scan_projects', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '扫描项目',
                'verbose_name_plural': '扫描项目列表',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ScanPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_num', models.IntegerField(verbose_name='页码')),
                ('original_path', models.CharField(max_length=1024, verbose_name='原始图片路径')),
                ('processed_path', models.CharField(blank=True, max_length=1024, verbose_name='处理后图片路径')),
                ('last_ops', models.JSONField(blank=True, default=dict, verbose_name='最近处理参数')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               related_name='pages', to='scan_enhance.scanproject')),
            ],
            options={
                'verbose_name': '扫描页面',
                'verbose_name_plural': '扫描页面列表',
                'ordering': ['page_num'],
                'unique_together': {('project', 'page_num')},
            },
        ),
    ]
