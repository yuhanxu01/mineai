"""
服务端合理性检查模块
基于游戏时间参数（1x速度：砍树2秒/格，采石4秒等）推算最大产出上限。
"""

# 每工人每秒最大产出（1x基准，已含3倍容差缓冲留给速度切换/网络延迟）
MAX_RATES_PER_WORKER_PER_SECOND = {
    'logs':       0.5,   # 砍树2秒→2.5木，上限0.5/s
    'stone':      0.25,  # 采石4秒/块
    'iron':       0.17,  # 挖铁6秒/块
    'coal':       0.2,   # 挖煤5秒/块
    'firewood':   2.0,   # 劈柴2秒→4柴（转化快）
    'food_total': 0.4,   # 所有食物合计（采集+钓鱼+狩猎）
    'gold':       5.0,   # 贸易所得，宽松
}

TOLERANCE = 3  # 整体3倍容差（速度10x时最差情况/延迟补偿）

FOOD_KEYS = [
    'wheat', 'vegetables', 'fruit', 'fish', 'venison',
    'mushrooms', 'mutton', 'chicken',
]


def _get(state, key):
    return state.get('resources', {}).get(key, 0)


def _food_total(state):
    return sum(_get(state, k) for k in FOOD_KEYS)


def sanity_check(old_state, new_state, elapsed_seconds):
    """
    检查 30 秒 sync 的增量是否合理。
    返回 (ok: bool, message: str)
    """
    pop = max(old_state.get('population', {}).get('total', 1), 1)
    elapsed = max(float(elapsed_seconds), 1.0)

    for resource, rate in MAX_RATES_PER_WORKER_PER_SECOND.items():
        if resource == 'food_total':
            old_val = _food_total(old_state)
            new_val = _food_total(new_state)
        else:
            old_val = _get(old_state, resource)
            new_val = _get(new_state, resource)

        gain = new_val - old_val
        max_gain = pop * rate * elapsed * TOLERANCE

        if gain > max_gain:
            return False, (
                f'{resource} 增长异常：增加 {gain:.0f}，'
                f'上限 {max_gain:.0f}（{pop}人 × {rate}/s × {elapsed:.0f}s × {TOLERANCE}）'
            )

    # 人口检查：30秒内最多增加 2 人（出生后立即到达不合理）
    old_pop = old_state.get('population', {}).get('total', 0)
    new_pop = new_state.get('population', {}).get('total', 0)
    if new_pop - old_pop > 2:
        return False, f'人口暴增：从 {old_pop} 到 {new_pop}'

    # 金币检查（仅限制暴增，负值允许：可能花了金币）
    old_gold = _get(old_state, 'gold')
    new_gold = _get(new_state, 'gold')
    gold_gain = new_gold - old_gold
    max_gold = MAX_RATES_PER_WORKER_PER_SECOND['gold'] * pop * elapsed * TOLERANCE
    if gold_gain > max_gold:
        return False, f'金币暴增：增加 {gold_gain:.0f}，上限 {max_gold:.0f}'

    return True, 'ok'
