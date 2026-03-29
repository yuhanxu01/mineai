from django.db import migrations, models


def update_existing_site_config(apps, schema_editor):
    SiteConfig = apps.get_model('accounts', 'SiteConfig')
    cfg = SiteConfig.objects.filter(pk=1).first()
    if not cfg:
        return

    changed = False
    if (cfg.site_title or '').strip() in ('', '应用平台'):
        cfg.site_title = 'MineAI'
        changed = True
    if (cfg.site_favicon or '').strip() == '':
        cfg.site_favicon = '/static/favicon-mineai.svg'
        changed = True
    if changed:
        cfg.save(update_fields=['site_title', 'site_favicon'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_cloudfile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='siteconfig',
            name='site_title',
            field=models.CharField(
                default='MineAI',
                help_text='显示在浏览器标签页、导航栏和登录页的网站名称',
                max_length=100,
                verbose_name='网站标题',
            ),
        ),
        migrations.AlterField(
            model_name='siteconfig',
            name='site_favicon',
            field=models.CharField(
                blank=True,
                default='/static/favicon-mineai.svg',
                help_text='浏览器标签页图标：填写图片URL（如 /static/favicon.ico）或直接填写 emoji（如 🚀）',
                max_length=500,
                verbose_name='网站图标',
            ),
        ),
        migrations.RunPython(update_existing_site_config, migrations.RunPython.noop),
    ]
