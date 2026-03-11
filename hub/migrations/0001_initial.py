from django.db import migrations, models


def seed_apps(apps, schema_editor):
    App = apps.get_model('hub', 'App')
    App.objects.create(
        name='记忆熔炉',
        slug='memoryforge',
        description='AI 辅助长篇小说创作引擎，基于分层记忆金字塔系统，帮助作者管理超长故事线与角色演变。',
        icon='🔥',
        color='#c9a86c',
        is_active=True,
        order=1,
    )


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='App',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='名称')),
                ('slug', models.SlugField(unique=True, verbose_name='标识符')),
                ('description', models.TextField(verbose_name='描述')),
                ('icon', models.CharField(max_length=10, verbose_name='图标')),
                ('color', models.CharField(default='#c9a86c', max_length=20, verbose_name='主题色')),
                ('is_active', models.BooleanField(default=True, verbose_name='启用')),
                ('order', models.IntegerField(default=0, verbose_name='排序')),
            ],
            options={
                'verbose_name': '应用',
                'verbose_name_plural': '应用列表',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.RunPython(seed_apps, migrations.RunPython.noop),
    ]
