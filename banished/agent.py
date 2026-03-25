"""
AI 协同决策模块
调用 core/llm.py 的 chat_stream，生成结构化游戏决策。
"""

import json

BANISHED_TUTORIAL = """
# 放逐之城 — 游戏规则手册（AI 版）

## 时间系统
- 1 tick = 1 真实秒（1x速度）
- 1 年 = 1200 tick；1 季节 = 300 tick（春/夏/秋/冬）
- 速度档：1x / 5x / 10x

## 村民生理值（0~100）
| 属性 | 衰减 | 危险阈值 | 后果 |
|------|------|----------|------|
| hunger（饱食） | -0.5/tick | <30 饥饿 | <10 → health每tick-1 |
| thirst（水分） | -0.8/tick | <30 口渴 | <10 → health每tick-2 |
| warmth（保暖） | 冬季-1/tick | <20 冻伤 | <5 → 死亡 |
| health（健康） | 病时-1/tick | <30 生病 | =0 → 死亡 |

优先级：口渴 > 饥饿 > 保暖 > 工作

## 水源
- 水井（well）：容量200，每tick+2补充，最多5人同时使用
- 河流格（tile=1）：无限水源，需村民走到河边

## 资源
logs（木头）、stone（石料）、iron（铁矿）、coal（煤炭）、
firewood（木柴）、iron_tools（铁工具）、steel_tools（钢工具）、
wheat/vegetables/fruit/fish/venison/mushrooms/mutton（食物）、
wool/leather/herbs/ale/hide_coat/wool_coat/warm_coat（材料/成品）、
gold（金币）

## 建筑成本（logs, stone, iron）
| 建筑 | 成本 | 工人 | 尺寸 |
|------|------|------|------|
| house | 16L+8S | 0 | 4×4 |
| stone_house | 24L+40S+10I | 0 | 4×4 |
| woodcutter | 24L+8S | 2 | 6×6 |
| forester | 32L+12S | 4 | 5×5 |
| farm | 免费 | 1 | 自由 |
| gatherer | 30L+12S | 4 | 7×4 |
| hunter | 34L+12S | 3 | 8×5 |
| fishing_dock | 30L+16S | 4 | 4×9（需水边）|
| herbalist | 30L+12S | 2 | 6×6 |
| blacksmith | 32L+55S+3I | 2 | 7×4 |
| tailor | 32L+48S+16I | 2 | 7×5 |
| well | 4L+4S | 0 | 3×3 |
| school | 50L+16S+16I | 2 | 7×8 |
| hospital | 52L+78S+32I | 2 | 10×8 |
| barn | 48L+16S | 0 | 5×6 |
| trading_post | 62L+80S+40I | 3 | 10×14（需水边）|
| quarry | 80L+40S | 10 | 21×15 |
| mine | 48L+68S | 10 | 12×10 |

## 生产转化率（教育工人×2）
- 木头 → 木柴：2tick/原木，产4柴（教育）/3柴
- 铁工具：5tick，1木+1铁→2铁工具
- 钢工具：8tick，1木+1铁+1煤→2钢工具
- 衣物：4tick，1皮/羊毛→2衣
- 砍树：2tick/棵→2~3木头

## 行动指令格式
```json
{
  "reasoning": "分析当前局势和决策理由",
  "actions": [
    {"type": "build", "building": "house", "x": 20, "y": 15},
    {"type": "assign", "building_id": "uuid", "workers": 3},
    {"type": "trade", "resource": "logs", "order_type": "sell", "amount": 50, "price": 3}
  ]
}
```

## 建议优先级（早期）
1. 确保有水源（well 或河边）
2. 建造 house 保证人口有家
3. 建造 gatherer/farm 保证食物
4. 建造 woodcutter 保证木柴（冬季必需）
5. 建造 school 提升效率
6. 扩展人口
"""

AI_SYSTEM_PROMPT = """你是放逐之城的 AI 协同助手，负责帮助玩家管理城镇。
你只能执行玩家明确授权的操作，未授权操作不要输出。

请以严格的 JSON 格式回复，不要包含任何 Markdown 代码块标记，只输出纯 JSON：
{"reasoning": "...", "actions": [...]}

如果当前状态良好不需要操作，返回：
{"reasoning": "当前城镇运转正常", "actions": []}
"""


def build_state_summary(state: dict) -> str:
    """将游戏状态转换为 AI 可读的文字摘要"""
    t = state.get('time', {})
    res = state.get('resources', {})
    pop = state.get('population', {})
    buildings = state.get('buildings', [])
    villagers = state.get('villagers', [])

    lines = [
        f"年份:{t.get('year',1)} 季节:{t.get('season','spring')} tick:{t.get('tick',0)}",
        f"人口总计:{pop.get('total',0)} 工作中:{pop.get('working',0)} 空闲:{pop.get('idle',0)} 学生:{pop.get('students',0)}",
        "",
        "== 资源 ==",
    ]

    # 资源分组
    raw = ['logs', 'stone', 'iron', 'coal']
    processed = ['firewood', 'iron_tools', 'steel_tools']
    food = ['wheat', 'vegetables', 'fruit', 'fish', 'venison', 'mushrooms', 'mutton']
    other = ['wool', 'leather', 'herbs', 'ale', 'hide_coat', 'wool_coat', 'warm_coat']

    for group_name, keys in [('原料', raw), ('加工品', processed), ('食物', food), ('其他', other)]:
        items = [f"{k}:{res.get(k,0)}" for k in keys if res.get(k, 0) > 0]
        if items:
            lines.append(f"  {group_name}: {', '.join(items)}")
    lines.append(f"  金币: {res.get('gold', 0)}")

    lines.append("")
    lines.append(f"== 建筑（共{len(buildings)}座）==")
    for b in buildings:
        status = "建造中" if not b.get('built') else "运营中"
        lines.append(
            f"  [{b['type']}] id:{b['id'][:8]} 位置:({b['x']},{b['y']}) "
            f"工人:{b.get('workers_assigned',0)}/{b.get('workers_max',0)} {status}"
        )

    # 危急村民
    urgent = [v for v in villagers if v.get('thirst', 100) < 30 or v.get('hunger', 100) < 30]
    if urgent:
        lines.append("")
        lines.append(f"== 危急村民（{len(urgent)}人）==")
        for v in urgent[:5]:
            lines.append(
                f"  {v['name']} hunger:{v.get('hunger',100):.0f} "
                f"thirst:{v.get('thirst',100):.0f} health:{v.get('health',100):.0f}"
            )

    return '\n'.join(lines)


def ai_action_stream(game, permissions: dict, config=None, user_id=None):
    """
    生成 AI 决策，以 SSE 格式流式 yield。
    permissions: {build: bool, assign: bool, trade: bool}
    """
    from core.llm import chat_stream, _get_config

    if config is None:
        config = _get_config()

    state = game.state or {}
    state_summary = build_state_summary(state)

    allowed = []
    if permissions.get('build'):
        allowed.append('build（放置建筑）')
    if permissions.get('assign'):
        allowed.append('assign（分配工人）')
    if permissions.get('trade'):
        allowed.append('trade（挂单交易）')

    user_msg = f"""
## 允许的操作
{', '.join(allowed) if allowed else '（当前无授权操作，仅分析局势）'}

## 游戏规则
{BANISHED_TUTORIAL}

## 当前游戏状态
{state_summary}

请根据以上信息，输出 JSON 格式的决策：
"""

    messages = [{"role": "user", "content": user_msg}]

    full_text = []
    for chunk in chat_stream(
        messages,
        system=AI_SYSTEM_PROMPT,
        temperature=0.4,
        max_tokens=1500,
        config=config,
        user_id=user_id,
    ):
        full_text.append(chunk)
        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"

    raw = ''.join(full_text).strip()

    # 尝试解析 JSON
    try:
        # 去除可能的 markdown 代码块
        if raw.startswith('```'):
            lines = raw.split('\n')
            raw = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
        decision = json.loads(raw)
        yield f"data: {json.dumps({'type': 'decision', 'decision': decision}, ensure_ascii=False)}\n\n"
    except json.JSONDecodeError:
        yield f"data: {json.dumps({'type': 'decision', 'decision': {'reasoning': raw, 'actions': []}}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
