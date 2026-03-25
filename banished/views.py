import json
import uuid
import random
import math

from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import BanishedGame, BanishedSave, MarketOrder, TradeRecord, Leaderboard
from .sanity import sanity_check
from .market import match_orders, get_market_summary, get_price_history


def token_auth_user(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Token '):
        return None
    try:
        from rest_framework.authtoken.models import Token
        return Token.objects.select_related('user').get(key=auth[6:].strip()).user
    except Exception:
        return None


def _make_initial_state():
    """生成新游戏初始状态"""
    tiles = _generate_map(64, 64)
    villagers = _generate_starting_villagers(4)
    # 起始购买区域：中心区域 16×16
    cx, cy = 24, 24
    purchased_regions = [{"x": cx, "y": cy, "w": 16, "h": 16}]

    return {
        "version": 1,
        "map": {
            "width": 64,
            "height": 64,
            "tiles": tiles,
            "purchased_regions": purchased_regions,
        },
        "time": {"year": 1, "tick": 0, "season": "spring", "speed": 1},
        "resources": {
            "logs": 100, "stone": 100, "iron": 0, "coal": 0,
            "firewood": 50, "iron_tools": 0, "steel_tools": 0,
            "wheat": 0, "vegetables": 0, "fruit": 0, "fish": 0,
            "venison": 0, "mushrooms": 0, "mutton": 0,
            "wool": 0, "leather": 0, "herbs": 0, "ale": 0,
            "hide_coat": 0, "wool_coat": 0, "warm_coat": 0,
            "chickens": 0, "sheep": 0, "cattle": 0,
            "food": 200,
            "gold": 100,
        },
        "population": {"total": 4, "working": 0, "students": 0, "homeless": 4, "idle": 4},
        "buildings": [],
        "villagers": villagers,
        "stats": {"peak_pop": 4, "total_gold_earned": 0, "years_survived": 0},
    }


def _generate_map(width, height):
    """生成地图，使用简化的噪声算法"""
    tiles = []

    # 简单伪随机地形生成（Babel 前端也会做同样的，这里只是初始化）
    rng = random.Random(42)

    # 先全部草地
    for y in range(height):
        row = []
        for x in range(width):
            row.append(0)  # grass
        tiles.append(row)

    # 生成河流（随机游走，从顶部到底部）
    rx = rng.randint(20, 44)
    for y in range(height):
        tiles[y][rx] = 1  # river
        if rx > 1:
            tiles[y][rx - 1] = 1
        if rx < width - 2:
            tiles[y][rx + 1] = 1
        rx += rng.randint(-1, 1)
        rx = max(4, min(width - 5, rx))

    # 山脉（左侧和右侧各一片）
    for _ in range(20):
        mx = rng.randint(2, 12)
        my = rng.randint(5, height - 10)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = mx + dx, my + dy
                if 0 <= nx < width and 0 <= ny < height and tiles[ny][nx] != 1:
                    tiles[ny][nx] = 2  # mountain
        mx = rng.randint(width - 15, width - 4)
        my = rng.randint(5, height - 10)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = mx + dx, my + dy
                if 0 <= nx < width and 0 <= ny < height and tiles[ny][nx] != 1:
                    tiles[ny][nx] = 2

    # 森林（分散）
    for _ in range(80):
        fx = rng.randint(2, width - 3)
        fy = rng.randint(2, height - 3)
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = fx + dx, fy + dy
                if 0 <= nx < width and 0 <= ny < height and tiles[ny][nx] == 0:
                    tiles[ny][nx] = 3  # forest

    # 石矿
    for _ in range(8):
        sx = rng.randint(5, width - 6)
        sy = rng.randint(5, height - 6)
        if tiles[sy][sx] not in (1, 2):
            tiles[sy][sx] = 4  # stone deposit

    # 铁矿
    for _ in range(5):
        ix = rng.randint(5, width - 6)
        iy = rng.randint(5, height - 6)
        if tiles[iy][ix] not in (1, 2):
            tiles[iy][ix] = 5  # iron deposit

    # 边界外（四周4格）
    for y in range(height):
        for x in range(width):
            if x < 4 or x >= width - 4 or y < 4 or y >= height - 4:
                tiles[y][x] = 7  # border

    return tiles


NAMES_MALE = ['张三', '李四', '王五', '赵六', '陈七', '刘八', '周九', '吴十',
              '郑一', '孙二', '马三', '朱四', '胡五', '林六', '何七', '高八']
NAMES_FEMALE = ['小红', '小花', '小英', '小芳', '小燕', '小兰', '小梅', '小雪',
                '小玲', '小丽', '小娟', '小颖', '小静', '小莉', '小华', '小云']


def _generate_starting_villagers(count):
    villagers = []
    rng = random.Random(99)
    cx, cy = 32, 32  # 中心位置附近
    for i in range(count):
        gender = 'm' if i % 2 == 0 else 'f'
        names = NAMES_MALE if gender == 'm' else NAMES_FEMALE
        name = names[i % len(names)]
        villagers.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "age": rng.randint(20, 35),
            "gender": gender,
            "x": float(cx + rng.randint(-3, 3)),
            "y": float(cy + rng.randint(-3, 3)),
            "state": "idle",
            "job": None,
            "building_id": None,
            "home_id": None,
            "health": 100,
            "happiness": 80,
            "educated": False,
            "partner_id": None,
            "hunger": 100,
            "thirst": 80,
            "warmth": 100,
            "action": None,
            "action_ticks_left": 0,
            "carrying": None,
        })
    return villagers


def _compute_score(state):
    pop = state.get('population', {}).get('total', 0)
    gold = state.get('resources', {}).get('gold', 0)
    year = state.get('time', {}).get('year', 1)
    return pop * 10 + gold // 10 + year * 5


# ─────────────────────────────────────────────────────────────────
# 游戏管理
# ─────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class GameView(View):
    def get(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            game = BanishedGame.objects.get(user=user)
            return JsonResponse({
                'id': game.id,
                'year': game.year,
                'population': game.population,
                'gold': game.gold,
                'is_ai_active': game.is_ai_active,
                'ai_permissions': game.ai_permissions,
                'state': game.state,
                'created_at': game.created_at.isoformat(),
                'last_saved_at': game.last_saved_at.isoformat(),
            })
        except BanishedGame.DoesNotExist:
            return JsonResponse({'error': 'no_game'}, status=404)

    def delete(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            game = BanishedGame.objects.get(user=user)
            game.delete()
            return JsonResponse({'ok': True})
        except BanishedGame.DoesNotExist:
            return JsonResponse({'error': 'no_game'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class GameNewView(View):
    def post(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)

        # 如果已有游戏，先删除
        BanishedGame.objects.filter(user=user).delete()

        state = _make_initial_state()
        game = BanishedGame.objects.create(
            user=user,
            state=state,
            year=1,
            population=4,
            gold=100,
            ai_permissions={'build': True, 'assign': True, 'trade': False},
        )
        return JsonResponse({
            'id': game.id,
            'state': state,
            'year': 1,
            'population': 4,
            'gold': 100,
        })


@method_decorator(csrf_exempt, name='dispatch')
class GameSyncView(View):
    """30 秒自动同步 + 合理性检查"""
    def post(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)

        try:
            game = BanishedGame.objects.get(user=user)
        except BanishedGame.DoesNotExist:
            return JsonResponse({'error': 'no_game'}, status=404)

        data = json.loads(request.body or b'{}')
        new_state = data.get('state', {})
        elapsed = float(data.get('elapsed_seconds', 30))

        old_state = game.state or {}
        ok, msg = sanity_check(old_state, new_state, elapsed)

        warnings = []
        if not ok:
            warnings.append(msg)
            # 不拒绝，只警告（前期宽松策略）

        # 更新游戏状态
        year = new_state.get('time', {}).get('year', game.year)
        pop = new_state.get('population', {}).get('total', game.population)
        gold = new_state.get('resources', {}).get('gold', game.gold)

        game.state = new_state
        game.year = year
        game.population = pop
        game.gold = gold
        game.save()

        # 更新排行榜
        score = _compute_score(new_state)
        Leaderboard.objects.update_or_create(
            user=user,
            defaults={
                'username': user.email,
                'score': score,
                'population': pop,
                'year': year,
                'gold': gold,
            }
        )

        return JsonResponse({'ok': True, 'score': score, 'warnings': warnings})


# ─────────────────────────────────────────────────────────────────
# 存档
# ─────────────────────────────────────────────────────────────────

class SaveListView(View):
    def get(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        saves = BanishedSave.objects.filter(user=user).order_by('slot')
        return JsonResponse({'saves': [
            {
                'slot': s.slot,
                'name': s.name,
                'year': s.year,
                'population': s.population,
                'gold': s.gold,
                'saved_at': s.saved_at.isoformat(),
            } for s in saves
        ]})


@method_decorator(csrf_exempt, name='dispatch')
class SaveSlotView(View):
    def post(self, request, slot):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        if slot not in (1, 2, 3):
            return JsonResponse({'error': '无效 slot'}, status=400)
        try:
            game = BanishedGame.objects.get(user=user)
        except BanishedGame.DoesNotExist:
            return JsonResponse({'error': 'no_game'}, status=404)

        data = json.loads(request.body or b'{}')
        name = data.get('name', f'存档{slot}')

        BanishedSave.objects.update_or_create(
            user=user, slot=slot,
            defaults={
                'name': name,
                'state': game.state,
                'year': game.year,
                'population': game.population,
                'gold': game.gold,
            }
        )
        return JsonResponse({'ok': True})


@method_decorator(csrf_exempt, name='dispatch')
class SaveLoadView(View):
    def post(self, request, slot):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            save = BanishedSave.objects.get(user=user, slot=slot)
        except BanishedSave.DoesNotExist:
            return JsonResponse({'error': '存档不存在'}, status=404)

        game, _ = BanishedGame.objects.get_or_create(user=user)
        game.state = save.state
        game.year = save.year
        game.population = save.population
        game.gold = save.gold
        game.save()
        return JsonResponse({'ok': True, 'state': save.state})


# ─────────────────────────────────────────────────────────────────
# 交易市场
# ─────────────────────────────────────────────────────────────────

class MarketView(View):
    def get(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        summary = get_market_summary()
        my_orders = MarketOrder.objects.filter(
            user=user, status__in=['open', 'partial']
        ).values('id', 'resource', 'order_type', 'amount', 'price', 'filled', 'status', 'created_at')
        return JsonResponse({
            'market': summary,
            'my_orders': list(my_orders),
        })


@method_decorator(csrf_exempt, name='dispatch')
class MarketOrderView(View):
    def post(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)

        data = json.loads(request.body or b'{}')
        resource = data.get('resource', '')
        order_type = data.get('order_type', '')
        amount = int(data.get('amount', 0))
        price = int(data.get('price', 0))

        if not resource or order_type not in ('buy', 'sell') or amount <= 0 or price <= 0:
            return JsonResponse({'error': '参数错误'}, status=400)

        order = MarketOrder.objects.create(
            user=user,
            resource=resource,
            order_type=order_type,
            amount=amount,
            price=price,
        )

        # 尝试撮合
        trades = match_orders(resource)

        return JsonResponse({'ok': True, 'order_id': order.id, 'trades': trades})


@method_decorator(csrf_exempt, name='dispatch')
class MarketCancelView(View):
    def post(self, request, order_id):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            order = MarketOrder.objects.get(id=order_id, user=user)
        except MarketOrder.DoesNotExist:
            return JsonResponse({'error': '订单不存在'}, status=404)
        if order.status not in ('open', 'partial'):
            return JsonResponse({'error': '订单已结束'}, status=400)
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        return JsonResponse({'ok': True})


class MarketHistoryView(View):
    def get(self, request, resource):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        history = get_price_history(resource, limit=100)
        return JsonResponse({'resource': resource, 'history': history})


# ─────────────────────────────────────────────────────────────────
# 排行榜
# ─────────────────────────────────────────────────────────────────

class LeaderboardView(View):
    def get(self, request):
        entries = Leaderboard.objects.order_by('-score')[:50]
        return JsonResponse({'leaderboard': [
            {
                'rank': i + 1,
                'username': e.username,
                'score': e.score,
                'population': e.population,
                'year': e.year,
                'gold': e.gold,
            }
            for i, e in enumerate(entries)
        ]})


# ─────────────────────────────────────────────────────────────────
# AI 协同
# ─────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class AIToggleView(View):
    def post(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            game = BanishedGame.objects.get(user=user)
        except BanishedGame.DoesNotExist:
            return JsonResponse({'error': 'no_game'}, status=404)
        data = json.loads(request.body or b'{}')
        game.is_ai_active = data.get('active', not game.is_ai_active)
        game.save(update_fields=['is_ai_active'])
        return JsonResponse({'ok': True, 'is_ai_active': game.is_ai_active})


@method_decorator(csrf_exempt, name='dispatch')
class AIPermissionsView(View):
    def post(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            game = BanishedGame.objects.get(user=user)
        except BanishedGame.DoesNotExist:
            return JsonResponse({'error': 'no_game'}, status=404)
        data = json.loads(request.body or b'{}')
        perms = {
            'build': bool(data.get('build', game.ai_permissions.get('build', True))),
            'assign': bool(data.get('assign', game.ai_permissions.get('assign', True))),
            'trade': bool(data.get('trade', game.ai_permissions.get('trade', False))),
        }
        game.ai_permissions = perms
        game.save(update_fields=['ai_permissions'])
        return JsonResponse({'ok': True, 'ai_permissions': perms})


@method_decorator(csrf_exempt, name='dispatch')
class AIActionView(View):
    """请求 AI 决策，SSE 流式返回"""
    def post(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            game = BanishedGame.objects.get(user=user)
        except BanishedGame.DoesNotExist:
            return JsonResponse({'error': 'no_game'}, status=404)

        from core.llm import _get_config
        try:
            config = _get_config()
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        permissions = game.ai_permissions or {'build': True, 'assign': True, 'trade': False}

        from .agent import ai_action_stream

        def generate():
            try:
                yield from ai_action_stream(game, permissions, config=config, user_id=user.id)
            except Exception as e:
                import json as _json
                yield f"data: {_json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


# ─────────────────────────────────────────────────────────────────
# Agent Tutorial
# ─────────────────────────────────────────────────────────────────

class AgentTutorialView(View):
    def get(self, request):
        from .agent import BANISHED_TUTORIAL
        return JsonResponse({'tutorial': BANISHED_TUTORIAL})
