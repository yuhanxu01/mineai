from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class BanishedGame(models.Model):
    """每个用户唯一的活跃游戏"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='banished_game')
    state = models.JSONField(default=dict, blank=True)
    year = models.IntegerField(default=1)
    population = models.IntegerField(default=0)
    gold = models.IntegerField(default=0)
    is_ai_active = models.BooleanField(default=False)
    ai_permissions = models.JSONField(default=dict, blank=True)  # {build:true, assign:true, trade:false}
    ai_log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '放逐之城游戏'
        verbose_name_plural = '放逐之城游戏'

    def __str__(self):
        return f'{self.user} — 年份:{self.year} 人口:{self.population}'


class BanishedSave(models.Model):
    """云存档，每用户最多 3 个 slot"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='banished_saves')
    slot = models.IntegerField()  # 1, 2, 3
    name = models.CharField(max_length=100, blank=True)
    state = models.JSONField(default=dict, blank=True)
    year = models.IntegerField(default=1)
    population = models.IntegerField(default=0)
    gold = models.IntegerField(default=0)
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'slot')]
        verbose_name = '放逐之城存档'
        verbose_name_plural = '放逐之城存档'

    def __str__(self):
        return f'{self.user} slot{self.slot}: {self.name}'


class MarketOrder(models.Model):
    """全局交易市场挂单"""
    ORDER_TYPES = [('buy', '买入'), ('sell', '卖出')]
    STATUS_CHOICES = [
        ('open', '挂单中'),
        ('partial', '部分成交'),
        ('filled', '已成交'),
        ('cancelled', '已撤单'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='banished_orders')
    resource = models.CharField(max_length=50)
    order_type = models.CharField(max_length=4, choices=ORDER_TYPES)
    amount = models.IntegerField()
    price = models.IntegerField()  # 金币/单位
    filled = models.IntegerField(default=0)
    status = models.CharField(max_length=10, default='open', choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '市场挂单'
        verbose_name_plural = '市场挂单'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user} {self.order_type} {self.resource} {self.amount}@{self.price}'

    @property
    def remaining(self):
        return self.amount - self.filled


class TradeRecord(models.Model):
    """成交记录，用于价格历史"""
    resource = models.CharField(max_length=50)
    amount = models.IntegerField()
    price = models.IntegerField()
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='banished_purchases')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='banished_sales')
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '成交记录'
        verbose_name_plural = '成交记录'
        ordering = ['-executed_at']

    def __str__(self):
        return f'{self.resource} {self.amount}@{self.price}'


class Leaderboard(models.Model):
    """排行榜快照，每次 sync 更新"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='banished_score')
    username = models.CharField(max_length=200)
    score = models.IntegerField(default=0)  # 人口*10 + 金币/10 + 年份*5
    population = models.IntegerField(default=0)
    year = models.IntegerField(default=0)
    gold = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '排行榜'
        verbose_name_plural = '排行榜'
        ordering = ['-score']

    def __str__(self):
        return f'{self.username}: {self.score}'
