import re
from core.llm import chat

DIFF_SYSTEM_PROMPT = """你是一个专门进行局部文本精确修改的AI助手。你的任务是根据用户的指令，对给定的原始文本进行修改。
为了能够让系统在前端精确显示“修改前”与“修改后”的差异(Diff)，你必须且只能使用搜索/替换块(Search/Replace Blocks)的格式来输出你的修改。

格式要求如下:
<<<<
[这里必须是能在原文本中完全精确匹配找到的一段原始文字，尽量多保留几句话或两端上下文以确保唯一性]
====
[这里是你修改后的新文字]
>>>>

示例:
用户要求: 把天气改冷一点
原始文本: ...那是一个温暖的春天早晨，微风拂过脸颊。村里的狗在叫...

你的回答应该像这样:
<<<<
那是一个温暖的春天早晨，微风拂过脸颊。
====
那是深秋刺骨的冷冽早晨，寒风如刀般刮过脸颊。
>>>>

注意：
1. `<<<<`、`====` 和 `>>>>` 必须单独占一行。
2. 原文本片段必须能100%在提供给你的全文中匹配（注意标点和换行）。
3. 如果需要进行多处不连续的修改，可以输出多个这样的替换块。
4. 如果你要在末尾添加一段话，你需要把现有的最后一段作为原文本一起包含进去替换，或者把最后一句作为原文本片段。
5. 千万不要输出不相关的闲聊或者只包含一部分需要替换的内容导致替换失败！
"""

def parse_diff_blocks(response_text):
    diffs = []
    # 匹配 <<<< 到 ==== 之间的原文本，以及 ==== 到 >>>> 之间的新文本
    pattern = re.compile(r'<<<<\n?(.*?)\n?====\n?(.*?)\n?>>>>', re.DOTALL)
    for match in pattern.finditer(response_text):
        original = match.group(1).strip('\r\n')
        replacement = match.group(2).strip('\r\n')
        # Skip empty ones just in case
        if original or replacement:
            diffs.append({
                "type": "replace",
                "original": original,
                "replacement": replacement
            })
    return diffs

def apply_diffs(original_text, diffs):
    current_text = original_text
    applied_diffs = []
    
    for diff in diffs:
        orig = diff["original"]
        repl = diff["replacement"]
        if orig in current_text:
            # 只替换第一次出现的
            current_text = current_text.replace(orig, repl, 1)
            applied_diffs.append(diff)
        else:
            # 容错降级：如果行首行尾带有空格导致未匹配，尝试宽松一点
            stripped_orig = orig.strip()
            if stripped_orig and stripped_orig in current_text:
                # 简单替换这个 stripped 版本，但这可能导致缩进或换行不一致
                # 为了简便，目前我们只把完全匹配成功或者是 strip 匹配的算作成功
                current_text = current_text.replace(stripped_orig, repl, 1)
                applied_diffs.append({"type": "replace", "original": stripped_orig, "replacement": repl})
            
    return current_text, applied_diffs

def edit_text_with_diff(project_id, original_text, instruction):
    prompt = f"""## 原始文本
{original_text}

## 修改要求
{instruction}

请使用带有 <<<< 和 ==== 和 >>>> 的搜索/替换块精确输出修改内容。
"""
    response = chat(
        [{"role": "user", "content": prompt}],
        system=DIFF_SYSTEM_PROMPT, 
        temperature=0.7, 
        project_id=project_id
    )
    
    parsed_diffs = parse_diff_blocks(response)
    new_text, applied_diffs = apply_diffs(original_text, parsed_diffs)
    
    return new_text, applied_diffs
