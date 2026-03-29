#!/usr/bin/env python3
"""
ocr_worker.py  —  MineAI OCR Worker
=====================================
支持两种模型后端，通过 --model-type 选择：

  青 (qing)  MixTeX tiny-ZhEn   VisionEncoderDecoderModel  快速，手写公式
  玄 (xuan)  GLM-OCR 微调版     AutoModelForImageTextToText 精准，复杂公式/表格

运行示例：
  python ocr_worker.py --model-type qing --site http://127.0.0.1:8001
  python ocr_worker.py --model-type xuan --site http://127.0.0.1:8001
  python ocr_worker.py --model-type qing --poll-only   # 无 Redis 时降级轮询

依赖安装：
  pip install torch transformers requests redis Pillow python-dotenv
"""

import argparse
import io
import json
import logging
import os
import sys
import time
import numpy as np

import requests
import torch
from PIL import Image

# ── 可选依赖 ──────────────────────────────────────────────────
try:
    import redis as redis_lib
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

MODEL_DEFAULTS = {
    'qing': 'MixTex/tiny-ZhEn-for-onnx',
    'xuan': 'glm-ocr-finetuned',
}
MODEL_CHANNELS = {
    'qing': 'ocr_tasks_qing',
    'xuan': 'ocr_tasks_xuan',
}
MODEL_LABELS = {
    'qing': '青·小模型 (MixTeX)',
    'xuan': '玄·大模型 (GLM-OCR)',
}


def parse_args():
    p = argparse.ArgumentParser(description="MineAI OCR Worker")
    p.add_argument("--model-type",    choices=['qing', 'xuan'], default='xuan',
                   help="模型类型：qing=青·小模型  xuan=玄·大模型（默认 xuan）")
    p.add_argument("--site",          default=os.getenv("MINEAI_SITE_URL", "http://127.0.0.1:8001"),
                   help="Django 服务器地址")
    p.add_argument("--model",         default='',
                   help="模型路径（留空则用各类型默认值）")
    p.add_argument("--prompt",        default=os.getenv("OCR_PROMPT", "Formula Recognition:"),
                   help="推理提示词（仅玄模型使用）")
    p.add_argument("--max-tokens",    type=int, default=int(os.getenv("OCR_MAX_TOKENS", "8192")),
                   help="最大生成 token 数（仅玄模型）")
    p.add_argument("--redis-host",    default=os.getenv("REDIS_HOST", "localhost"))
    p.add_argument("--redis-port",    type=int, default=int(os.getenv("REDIS_PORT", "6379")))
    p.add_argument("--redis-db",      type=int, default=int(os.getenv("REDIS_DB", "0")))
    p.add_argument("--worker-token",  default=os.getenv("OCR_WORKER_TOKEN", ""),
                   help="Worker 共享令牌（对应服务端 OCR_WORKER_TOKEN）")
    p.add_argument("--poll-only",     action="store_true",
                   help="强制 HTTP 轮询模式（不使用 Redis）")
    p.add_argument("--poll-interval", type=int, default=int(os.getenv("OCR_POLL_INTERVAL", "5")),
                   help="HTTP 轮询间隔秒（默认 5）")
    args = p.parse_args()
    # 补全模型路径
    if not args.model:
        args.model = os.getenv("OCR_MODEL_PATH", MODEL_DEFAULTS[args.model_type])
    # 补全频道
    args.channel = os.getenv("REDIS_OCR_CHANNEL", MODEL_CHANNELS[args.model_type])
    return args


# ═══════════════════════════════════════════════════════════════
# 日志
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("ocr_worker")


# ═══════════════════════════════════════════════════════════════
# 模型加载（按类型分发）
# ═══════════════════════════════════════════════════════════════

def load_model_qing(model_path: str):
    """
    青·小模型（MixTeX VisionEncoderDecoder）
    原始 latexocr_host.py 推理架构
    """
    from transformers import AutoTokenizer, VisionEncoderDecoderModel, AutoImageProcessor
    log.info(f"[青] 加载 VisionEncoderDecoder: {model_path}")

    feature_extractor = AutoImageProcessor.from_pretrained(model_path)
    tokenizer = AutoTokenizer.from_pretrained(model_path, max_len=512)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    dtype  = torch.float16 if device == 'cuda' else torch.float32
    model  = VisionEncoderDecoderModel.from_pretrained(model_path).to(device)
    if dtype == torch.float16:
        model = model.half()
    model.eval()

    log.info(f"[青] 加载完成 → device={device} | dtype={dtype}")
    return {'type': 'qing', 'model': model, 'tokenizer': tokenizer,
            'extractor': feature_extractor, 'device': device, 'dtype': dtype}


def load_model_xuan(model_path: str):
    """
    玄·大模型（GLM-OCR AutoModelForImageTextToText）
    """
    from transformers import AutoProcessor, AutoModelForImageTextToText
    log.info(f"[玄] 加载 AutoModelForImageTextToText: {model_path}")

    processor = AutoProcessor.from_pretrained(model_path)
    processor.tokenizer.padding_side = "left"
    if processor.tokenizer.pad_token is None:
        processor.tokenizer.pad_token = processor.tokenizer.eos_token

    model = AutoModelForImageTextToText.from_pretrained(
        model_path, torch_dtype="auto", device_map="auto"
    )
    model.eval()

    device = next(model.parameters()).device
    dtype  = next(model.parameters()).dtype
    log.info(f"[玄] 加载完成 → device={device} | dtype={dtype}")
    return {'type': 'xuan', 'model': model, 'processor': processor,
            'device': device, 'dtype': dtype}


def load_backend(args) -> dict:
    if args.model_type == 'qing':
        return load_model_qing(args.model)
    else:
        return load_model_xuan(args.model)


# ═══════════════════════════════════════════════════════════════
# 推理（青 / 玄 两套逻辑）
# ═══════════════════════════════════════════════════════════════

def infer_qing(backend: dict, image: Image.Image) -> tuple[str, float]:
    """青·小模型推理（毫秒级）"""
    model     = backend['model']
    tokenizer = backend['tokenizer']
    extractor = backend['extractor']
    device    = backend['device']
    dtype     = backend['dtype']

    img_tensor = extractor(image, return_tensors="pt").pixel_values.to(device)
    if dtype == torch.float16:
        img_tensor = img_tensor.half()

    t0 = time.perf_counter()
    with torch.no_grad():
        output_ids = model.generate(img_tensor)
    elapsed = time.perf_counter() - t0

    raw = tokenizer.decode(output_ids[0])
    # 与旧项目 latexocr_host.py 保持完全一致的后处理
    text = (raw
            .replace('\\[', '\\begin{align*}')
            .replace('\\]', '\\end{align*}')
            .replace('%', '\\%')
            .replace('</s>', '')
            .replace('<s>', ''))

    if device == 'cuda':
        torch.cuda.empty_cache()
    return text.strip(), elapsed


def infer_xuan(backend: dict, image: Image.Image,
               prompt: str, max_new_tokens: int) -> tuple[str, float]:
    """玄·大模型推理（秒级）"""
    model     = backend['model']
    processor = backend['processor']

    inputs = processor.apply_chat_template(
        [{"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text",  "text": prompt},
        ]}],
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    )
    inputs = {k: v.to(model.device) if isinstance(v, torch.Tensor) else v
              for k, v in inputs.items()}

    if torch.cuda.is_available():
        torch.cuda.synchronize()
    t0 = time.perf_counter()

    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)

    if torch.cuda.is_available():
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - t0

    input_len = inputs["input_ids"].shape[1]
    text = processor.decode(generated_ids[0][input_len:], skip_special_tokens=False)

    del generated_ids, inputs
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return text.strip(), elapsed


# ═══════════════════════════════════════════════════════════════
# 与 Django 通信
# ═══════════════════════════════════════════════════════════════

class MineAIClient:
    def __init__(self, site_url: str, worker_token: str = ""):
        self.site = site_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "MineAI-OCR-Worker/2.1"
        token = (worker_token or "").strip()
        if token:
            self.session.headers["X-OCR-Worker-Token"] = token

    def download_image(self, image_url: str) -> Image.Image:
        url = image_url if image_url.startswith("http") else self.site + image_url
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")

    def post_callback(self, callback_url: str, text: str = "", error: str = "") -> bool:
        payload = {"error": error} if error else {"text": text}
        try:
            resp = self.session.post(callback_url, json=payload, timeout=15)
            resp.raise_for_status()
            return True
        except Exception as e:
            log.warning(f"Callback 失败 [{callback_url}]: {e}")
            return False

    def post_result_legacy(self, page_id: int, text: str) -> bool:
        url = f"{self.site}/api/ocr/image/{page_id}/"
        try:
            resp = self.session.post(url, json={"text_data": text}, timeout=15)
            resp.raise_for_status()
            return True
        except Exception as e:
            log.warning(f"结果提交失败 [page_id={page_id}]: {e}")
            return False

    def get_pending_pages(self, model_type: str) -> list:
        """HTTP 轮询：按 model_type 拉取待处理任务"""
        url = f"{self.site}/api/ocr/get-empty-text-images/?model_type={model_type}"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json().get("pages", [])
        except Exception as e:
            log.warning(f"轮询失败: {e}")
            return []


# ═══════════════════════════════════════════════════════════════
# 任务处理
# ═══════════════════════════════════════════════════════════════

def process_task(client: MineAIClient, backend: dict,
                 task: dict, args) -> bool:
    task_id      = task.get("task_id") or task.get("id")
    image_url    = task.get("image_url", "")
    callback_url = task.get("callback_url", "")
    page_num     = task.get("page_num", "?")
    tag          = "[青]" if backend['type'] == 'qing' else "[玄]"

    # 任务模型类型不匹配时跳过（Redis 单频道场景兼容）
    task_model = task.get("model_type", backend['type'])
    if task_model != backend['type']:
        log.debug(f"跳过 id={task_id}（任务={task_model}，本 Worker={backend['type']}）")
        return True

    log.info(f"{tag} 任务 id={task_id}  page={page_num}  {image_url}")

    # 1. 下载图片
    try:
        image = client.download_image(image_url)
        log.info(f"   图片尺寸: {image.size}")
    except Exception as e:
        err = f"图片下载失败: {e}"
        log.error(f"   ✗ {err}")
        _report(client, callback_url, task_id, error=err)
        return False

    # 2. 推理
    try:
        if backend['type'] == 'qing':
            text, elapsed = infer_qing(backend, image)
        else:
            text, elapsed = infer_xuan(backend, image, args.prompt, args.max_tokens)
        log.info(f"   ✓ {elapsed:.2f}s | {len(text)} chars")
    except Exception as e:
        err = f"推理失败: {e}"
        log.error(f"   ✗ {err}", exc_info=True)
        _report(client, callback_url, task_id, error=err)
        return False

    # 3. 回传
    ok = _report(client, callback_url, task_id, text=text)
    if ok:
        log.info(f"   ↑ 结果已上传")
    return ok


def _report(client, callback_url, task_id, text="", error=""):
    if callback_url:
        return client.post_callback(callback_url, text=text, error=error)
    elif task_id:
        return client.post_result_legacy(task_id, text if not error else f"[ERROR] {error}")
    return False


# ═══════════════════════════════════════════════════════════════
# Redis Pub/Sub 模式
# ═══════════════════════════════════════════════════════════════

def run_redis_mode(client, backend, args):
    log.info(f"[Redis] {args.redis_host}:{args.redis_port} | 频道={args.channel}")
    r = redis_lib.Redis(
        host=args.redis_host, port=args.redis_port, db=args.redis_db,
        decode_responses=True, socket_connect_timeout=5, socket_keepalive=True,
    )
    r.ping()

    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(args.channel)
    log.info(f"✓ Redis 已连接，监听中... (Ctrl+C 退出)")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            task = json.loads(message["data"])
        except json.JSONDecodeError:
            log.warning(f"无效消息: {message['data'][:120]}")
            continue
        process_task(client, backend, task, args)


# ═══════════════════════════════════════════════════════════════
# HTTP 轮询模式（备用）
# ═══════════════════════════════════════════════════════════════

def run_poll_mode(client, backend, args):
    model_type = backend['type']
    log.info(f"[HTTP 轮询] 服务器={args.site}  间隔={args.poll_interval}s  model_type={model_type}")

    while True:
        pages = client.get_pending_pages(model_type)
        if pages:
            log.info(f"发现 {len(pages)} 个任务")
            for page in pages:
                task = {
                    "task_id":     page.get("id"),
                    "image_url":   page.get("image_url", ""),
                    "callback_url": page.get("callback_url", ""),
                    "model_type":  page.get("model_type", model_type),
                }
                process_task(client, backend, task, args)
        else:
            # 随机扰动，避免多 Worker 同步轮询
            jitter = args.poll_interval + np.random.normal(0, 0.5)
            for i in range(max(1, int(jitter))):
                dots = "." * ((i % 3) + 1)
                sys.stdout.write(f"\r  [{MODEL_LABELS[model_type]}] 等待任务{dots}   ")
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write("\r" + " " * 40 + "\r")


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def main():
    args = parse_args()
    label = MODEL_LABELS[args.model_type]

    print(f"""
{'═' * 60}
  MineAI OCR Worker  —  {label}
{'═' * 60}
  服务器    : {args.site}
  模型路径  : {args.model}
  Redis     : {args.redis_host}:{args.redis_port} / db={args.redis_db}
  频道      : {args.channel}
  轮询间隔  : {args.poll_interval}s
  Max Tokens: {args.max_tokens}（仅玄模型）
  提示词    : {args.prompt}（仅玄模型）
{'═' * 60}
""")

    backend = load_backend(args)
    client  = MineAIClient(args.site, worker_token=args.worker_token)

    if args.poll_only:
        log.info("强制 HTTP 轮询模式")
        run_poll_mode(client, backend, args)
    elif not HAS_REDIS:
        log.warning("redis 库未安装，降级为 HTTP 轮询模式")
        run_poll_mode(client, backend, args)
    else:
        try:
            run_redis_mode(client, backend, args)
        except KeyboardInterrupt:
            log.info("Worker 已停止")
            sys.exit(0)
        except Exception as e:
            log.warning(f"Redis 不可用（{e}），降级为 HTTP 轮询模式")
            run_poll_mode(client, backend, args)


if __name__ == "__main__":
    main()
