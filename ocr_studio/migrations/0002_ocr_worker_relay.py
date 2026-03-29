from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('ocr_studio', '0001_initial'),
    ]

    operations = [
        # OCRPage 新增字段
        migrations.AddField(
            model_name='ocrpage',
            name='image_file',
            field=models.ImageField(upload_to='ocr_pages/%Y/%m/', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='ocrpage',
            name='binary_image',
            field=models.ImageField(upload_to='ocr_pages_binary/%Y/%m/', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='ocrpage',
            name='feedback_type',
            field=models.CharField(
                max_length=20,
                choices=[('like', '点赞'), ('dislike', '点踩')],
                null=True,
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='ocrpage',
            name='feedback_text',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='ocrpage',
            name='callback_token',
            field=models.CharField(max_length=100, null=True, blank=True, unique=True),
        ),
        # OCRProject 新增字段
        migrations.AddField(
            model_name='ocrproject',
            name='processing_mode',
            field=models.CharField(
                max_length=20,
                choices=[('api', '直连API模式'), ('worker', 'Worker中继模式')],
                default='api'
            ),
        ),
        migrations.AddField(
            model_name='ocrproject',
            name='redis_channel',
            field=models.CharField(max_length=100, default='ocr_tasks'),
        ),
        # 新增 OCRUsageQuota 模型
        migrations.CreateModel(
            name='ocrusagequota',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ocr_quota')),
                ('quota_date', models.DateField(verbose_name='配额日期')),
                ('upload_count', models.IntegerField(default=0, verbose_name='上传次数')),
                ('like_count', models.IntegerField(default=0, verbose_name='点赞次数')),
                ('dislike_count', models.IntegerField(default=0, verbose_name='点踩次数')),
                ('nonfeedback_count', models.IntegerField(default=0, verbose_name='未反馈次数')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': 'OCR配额',
                'verbose_name_plural': 'OCR配额列表',
                'unique_together': {('user', 'quota_date')},
            },
        ),
    ]
