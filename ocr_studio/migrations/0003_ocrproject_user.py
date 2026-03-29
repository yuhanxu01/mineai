from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ocr_studio', '0002_ocr_worker_relay'),
    ]

    operations = [
        migrations.AddField(
            model_name='ocrproject',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='ocr_projects',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
