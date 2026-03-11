from django.db import models


class App(models.Model):
    name = models.CharField(max_length=100, verbose_name='名称')
    slug = models.SlugField(unique=True, verbose_name='标识符')
    description = models.TextField(verbose_name='描述')
    icon = models.CharField(max_length=10, verbose_name='图标')
    color = models.CharField(max_length=20, default='#c9a86c', verbose_name='主题色')
    is_active = models.BooleanField(default=True, verbose_name='启用')
    order = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        ordering = ['order', 'name']
        verbose_name = '应用'
        verbose_name_plural = '应用列表'

    def __str__(self):
        return self.name
