from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_add_user_api_key'),
    ]

    operations = [
        # TokenUsage: 每日用量追踪字段
        migrations.AddField(
            model_name='tokenusage',
            name='daily_date',
            field=models.DateField(blank=True, null=True, verbose_name='当日日期'),
        ),
        migrations.AddField(
            model_name='tokenusage',
            name='daily_prompt_count',
            field=models.PositiveIntegerField(default=0, verbose_name='今日提交次数'),
        ),
        migrations.AddField(
            model_name='tokenusage',
            name='daily_input_tokens',
            field=models.BigIntegerField(default=0, verbose_name='今日输入Token'),
        ),
        migrations.AddField(
            model_name='tokenusage',
            name='daily_output_tokens',
            field=models.BigIntegerField(default=0, verbose_name='今日输出Token'),
        ),
        # SiteConfig: 免费用户每日配额
        migrations.AddField(
            model_name='siteconfig',
            name='free_daily_input_tokens',
            field=models.PositiveIntegerField(
                default=50000,
                verbose_name='免费用户每日输入Token上限',
                help_text='免费用户（未配置自己API密钥）每自然日最多消耗的输入Token数，默认 50,000',
            ),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='free_daily_output_tokens',
            field=models.PositiveIntegerField(
                default=25000,
                verbose_name='免费用户每日输出Token上限',
                help_text='免费用户（未配置自己API密钥）每自然日最多消耗的输出Token数，默认 25,000',
            ),
        ),
        migrations.AddField(
            model_name='siteconfig',
            name='free_daily_prompt_count',
            field=models.PositiveIntegerField(
                default=10,
                verbose_name='免费用户每日提交次数上限',
                help_text='免费用户每自然日最多提交的AI请求次数，默认 10 次',
            ),
        ),
    ]
