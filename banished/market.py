"""
全局交易市场撮合模块
价格优先 → 时间优先（FIFO）
- 卖单按价格 ASC 排序
- 买单按价格 DESC 排序
- 买价 >= 卖价 时撮合，成交价 = (买价 + 卖价) // 2
"""

from django.db import transaction
from .models import MarketOrder, TradeRecord


@transaction.atomic
def match_orders(resource: str):
    """
    对指定资源执行撮合，返回成交记录列表。
    """
    trades = []

    # 锁定行，避免并发撮合
    sell_orders = list(
        MarketOrder.objects.select_for_update()
        .filter(resource=resource, order_type='sell', status__in=['open', 'partial'])
        .order_by('price', 'created_at')
    )
    buy_orders = list(
        MarketOrder.objects.select_for_update()
        .filter(resource=resource, order_type='buy', status__in=['open', 'partial'])
        .order_by('-price', 'created_at')
    )

    si, bi = 0, 0
    while si < len(sell_orders) and bi < len(buy_orders):
        sell = sell_orders[si]
        buy = buy_orders[bi]

        # 同一用户不撮合（防止自买自卖）
        if sell.user_id == buy.user_id:
            bi += 1
            continue

        if buy.price < sell.price:
            break  # 无法撮合

        exec_price = (buy.price + sell.price) // 2
        exec_amount = min(sell.remaining, buy.remaining)

        if exec_amount <= 0:
            if sell.remaining <= 0:
                si += 1
            if buy.remaining <= 0:
                bi += 1
            continue

        # 更新卖单
        sell.filled += exec_amount
        if sell.filled >= sell.amount:
            sell.status = 'filled'
            si += 1
        else:
            sell.status = 'partial'
        sell.save(update_fields=['filled', 'status'])

        # 更新买单
        buy.filled += exec_amount
        if buy.filled >= buy.amount:
            buy.status = 'filled'
            bi += 1
        else:
            buy.status = 'partial'
        buy.save(update_fields=['filled', 'status'])

        # 写入成交记录
        record = TradeRecord.objects.create(
            resource=resource,
            amount=exec_amount,
            price=exec_price,
            buyer=buy.user,
            seller=sell.user,
        )
        trades.append({
            'resource': resource,
            'amount': exec_amount,
            'price': exec_price,
            'buyer_id': buy.user_id,
            'seller_id': sell.user_id,
            'executed_at': record.executed_at.isoformat(),
        })

    return trades


def get_market_summary(resource: str = None):
    """返回当前市场挂单摘要和最近成交价"""
    from django.db.models import Avg, Min, Max, Count
    from datetime import timedelta
    from django.utils import timezone

    resources = [resource] if resource else []
    if not resources:
        resources = list(
            MarketOrder.objects.filter(status__in=['open', 'partial'])
            .values_list('resource', flat=True)
            .distinct()
        )

    result = {}
    for res in resources:
        sells = MarketOrder.objects.filter(
            resource=res, order_type='sell', status__in=['open', 'partial']
        ).order_by('price')[:5]
        buys = MarketOrder.objects.filter(
            resource=res, order_type='buy', status__in=['open', 'partial']
        ).order_by('-price')[:5]

        recent = TradeRecord.objects.filter(
            resource=res,
            executed_at__gte=timezone.now() - timedelta(hours=24),
        ).order_by('-executed_at')[:1]

        last_price = recent.first().price if recent.exists() else None

        result[res] = {
            'sell_orders': [{'price': o.price, 'amount': o.remaining, 'id': o.id} for o in sells],
            'buy_orders': [{'price': o.price, 'amount': o.remaining, 'id': o.id} for o in buys],
            'last_price': last_price,
        }

    return result


def get_price_history(resource: str, limit: int = 50):
    """返回最近成交价历史"""
    records = TradeRecord.objects.filter(resource=resource).order_by('-executed_at')[:limit]
    return [
        {
            'price': r.price,
            'amount': r.amount,
            'executed_at': r.executed_at.isoformat(),
        }
        for r in reversed(list(records))
    ]
