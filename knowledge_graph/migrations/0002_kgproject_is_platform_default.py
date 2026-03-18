from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge_graph', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='kgproject',
            name='is_platform_default',
            field=models.BooleanField(default=False, verbose_name='是否平台默认图谱'),
        ),
    ]
