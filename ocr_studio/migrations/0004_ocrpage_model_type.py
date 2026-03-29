from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ocr_studio', '0003_ocrproject_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='ocrpage',
            name='model_type',
            field=models.CharField(
                max_length=20,
                choices=[('qing', '青·小模型'), ('xuan', '玄·大模型')],
                default='xuan',
                verbose_name='OCR 模型',
            ),
        ),
    ]
