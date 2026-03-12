"""
文献分块索引器
- 按段落分块，保留精确行号
- 提取关键词
- 识别区块类型（公式、表格、标题等）
"""
import re
from .models import Literature, LiteratureChunk

CHUNK_SIZE = 600       # 目标块大小（字符）
CHUNK_OVERLAP_LINES = 1  # 重叠行数


def _detect_chunk_type(text):
    """识别块类型"""
    stripped = text.strip()
    if stripped.startswith('$$') or stripped.startswith('\\[') or re.search(r'\$\$.+\$\$', stripped, re.DOTALL):
        return 'formula'
    if stripped.startswith('|') and '|' in stripped[1:]:
        return 'table'
    if re.match(r'^\!\[', stripped):
        return 'figure'
    if re.match(r'^#+\s*(references|bibliography|参考文献)', stripped, re.IGNORECASE):
        return 'reference'
    if re.match(r'^#+\s*(abstract|摘要)', stripped, re.IGNORECASE):
        return 'abstract'
    return 'text'


def _extract_keywords(text):
    """从文本中提取关键词（中英文）"""
    # 去除markdown标记
    clean = re.sub(r'[#*_`\[\]()>|]', ' ', text)
    clean = re.sub(r'\$[^$]+\$', ' FORMULA ', clean)  # 替换公式

    # 英文单词（长度≥3）
    en_words = re.findall(r'\b[a-zA-Z]{3,}\b', clean)
    en_words = [w.lower() for w in en_words if w.lower() not in _STOP_EN]

    # 中文词（2-4字）
    zh_chars = re.findall(r'[\u4e00-\u9fff]{2,4}', clean)
    zh_words = [w for w in zh_chars if w not in _STOP_ZH]

    # 合并，去重，取top30
    all_kw = list(dict.fromkeys(en_words + zh_words))[:30]
    return all_kw


_STOP_EN = {
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all',
    'can', 'has', 'her', 'was', 'one', 'our', 'out', 'day',
    'get', 'how', 'its', 'may', 'new', 'now', 'own', 'see',
    'two', 'way', 'who', 'did', 'use', 'with', 'from', 'this',
    'that', 'have', 'been', 'they', 'will', 'when', 'what',
    'also', 'than', 'then', 'them', 'such', 'more', 'into',
    'which', 'there', 'their', 'about', 'these', 'would',
    'other', 'after', 'first', 'well', 'being', 'over',
    'both', 'each', 'many', 'most', 'must', 'only', 'same',
    'some', 'take', 'time', 'very', 'make', 'like', 'just',
    'show', 'used', 'were', 'data', 'model', 'based', 'using',
    'paper', 'section', 'figure', 'table',
}

_STOP_ZH = {
    '我们', '他们', '这个', '那个', '一个', '可以', '因为', '所以',
    '但是', '如果', '这些', '那些', '通过', '进行', '对于', '关于',
    '在于', '由于', '然而', '此外', '另外', '同时', '其中', '其他',
    '方面', '问题', '方法', '结果', '分析', '研究', '论文', '文章',
}


def _get_current_heading(lines, line_idx):
    """往前找最近的标题行"""
    for i in range(line_idx, -1, -1):
        if lines[i].startswith('#'):
            return lines[i].lstrip('#').strip()
    return ''


def chunk_literature(literature: Literature):
    """
    对文献内容进行分块并建立索引。
    保留精确的行号（1-based）。
    """
    # 清理旧索引
    LiteratureChunk.objects.filter(literature=literature).delete()

    lines = literature.content.splitlines()
    total_lines = len(lines)
    literature.total_lines = total_lines
    literature.is_indexed = False
    literature.save(update_fields=['total_lines', 'is_indexed'])

    if not lines:
        return []

    chunks = []
    chunk_index = 0
    i = 0
    current_heading = ''

    while i < total_lines:
        # 更新当前标题
        if lines[i].startswith('#'):
            current_heading = lines[i].lstrip('#').strip()

        chunk_lines = []
        chunk_start = i + 1  # 1-based

        # 积累行直到达到块大小
        char_count = 0
        while i < total_lines:
            line = lines[i]
            if lines[i].startswith('#') and chunk_lines and char_count > 100:
                # 遇到新标题且已有内容，切块
                break
            chunk_lines.append(line)
            char_count += len(line)
            i += 1
            if char_count >= CHUNK_SIZE:
                break

        if not chunk_lines:
            i += 1
            continue

        chunk_text = '\n'.join(chunk_lines).strip()
        if not chunk_text:
            continue

        chunk_end = chunk_start + len(chunk_lines) - 1  # 1-based

        chunk_type = _detect_chunk_type(chunk_text)
        keywords = _extract_keywords(chunk_text)

        # 计算重要度：标题块更重要，公式块特殊
        importance = 0.5
        if chunk_type == 'abstract':
            importance = 0.9
        elif chunk_type == 'formula':
            importance = 0.7
        elif current_heading:
            importance = 0.6

        obj = LiteratureChunk(
            literature=literature,
            chunk_index=chunk_index,
            line_start=chunk_start,
            line_end=chunk_end,
            content=chunk_text,
            heading=current_heading,
            chunk_type=chunk_type,
            keywords=keywords,
            importance=importance,
        )
        chunks.append(obj)
        chunk_index += 1

    LiteratureChunk.objects.bulk_create(chunks)
    literature.is_indexed = True
    literature.save(update_fields=['is_indexed'])

    return chunks


def search_chunks(project_id, query, user_id, top_k=10, lit_ids=None):
    """
    在指定项目的文献块中进行关键词检索。
    返回按相关度排序的 LiteratureChunk 列表，含分数。
    """
    from .models import Literature, LiteratureChunk
    from django.db.models import Q

    # 构建查询集：当前用户的文献 + 共享文献
    lit_qs = Literature.objects.filter(
        project_id=project_id,
        is_indexed=True,
    ).filter(
        Q(user_id=user_id) | Q(is_shared=True)
    )

    if lit_ids:
        lit_qs = lit_qs.filter(id__in=lit_ids)

    lit_ids_list = list(lit_qs.values_list('id', flat=True))
    if not lit_ids_list:
        return []

    chunks = LiteratureChunk.objects.filter(
        literature_id__in=lit_ids_list
    ).select_related('literature')

    query_keywords = set(_extract_keywords(query))
    # 也加入原始词（不过滤停用词）
    raw_words = set(re.findall(r'\b[a-zA-Z]{2,}\b', query.lower()))
    raw_zh = set(re.findall(r'[\u4e00-\u9fff]{2,}', query))
    query_keywords |= raw_words | raw_zh

    if not query_keywords:
        return list(chunks[:top_k])

    scored = []
    for chunk in chunks:
        chunk_kw = set(chunk.keywords)
        # 加入块文本的实际词
        chunk_text_lower = chunk.content.lower()
        score = 0.0
        for kw in query_keywords:
            if kw in chunk_kw:
                score += 2.0  # 索引命中权重高
            elif kw in chunk_text_lower:
                score += 1.0  # 文本命中
        # 重要度加成
        score *= (0.5 + chunk.importance)
        if score > 0:
            scored.append((chunk, score))

    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]
