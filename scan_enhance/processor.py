"""
OpenCV-based document scan enhancement pipeline.
Each function takes a numpy BGR image and returns a processed numpy BGR image.
"""
import math
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from PIL import Image, ImageFilter, ImageEnhance
from io import BytesIO


def _require_cv2():
    if not CV2_AVAILABLE:
        raise RuntimeError("opencv-python is not installed. Run: pip install opencv-python-headless")


def pil_to_cv2(pil_img):
    arr = np.array(pil_img.convert('RGB'))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def cv2_to_pil(bgr):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


# ── Individual operations ────────────────────────────────────────────────────

def op_denoise(img, strength=10):
    """非局部均值去噪 (Non-Local Means Denoising)"""
    _require_cv2()
    h = max(3, min(strength, 30))
    return cv2.fastNlMeansDenoisingColored(img, None, h, h, 7, 21)


def op_deskew(img):
    """文本行倾斜自动校正 (Deskew via Hough line detection)"""
    _require_cv2()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Blur + edge detect
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                             minLineLength=100, maxLineGap=10)
    if lines is None:
        return img

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 != x1:
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if -45 < angle < 45:
                angles.append(angle)

    if not angles:
        return img

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return img

    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    return rotated


def op_perspective_correct(img):
    """自动文档透视校正 (4-point perspective transform)"""
    _require_cv2()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 120)

    # Dilate edges to close gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edged = cv2.dilate(edged, kernel, iterations=2)

    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return img

    # Find largest contour
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    doc_cnt = None
    for c in contours[:5]:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            img_area = img.shape[0] * img.shape[1]
            if area > 0.1 * img_area:
                doc_cnt = approx
                break

    if doc_cnt is None:
        return img

    pts = doc_cnt.reshape(4, 2).astype(np.float32)
    # Order: top-left, top-right, bottom-right, bottom-left
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxW = max(int(widthA), int(widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxH = max(int(heightA), int(heightB))

    if maxW < 50 or maxH < 50:
        return img

    dst = np.array([
        [0, 0],
        [maxW - 1, 0],
        [maxW - 1, maxH - 1],
        [0, maxH - 1]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (maxW, maxH))
    return warped


def _order_points(pts):
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]   # top-left
    rect[2] = pts[np.argmax(s)]   # bottom-right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left
    return rect


def op_binarize(img, method='adaptive', block_size=21, C=10):
    """
    文档二值化
    method: 'otsu' | 'adaptive' | 'sauvola_approx'
    """
    _require_cv2()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if method == 'otsu':
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif method == 'sauvola_approx':
        # Approx Sauvola: adaptive + local std estimate
        mean = cv2.boxFilter(gray.astype(np.float32), -1, (block_size, block_size))
        mean_sq = cv2.boxFilter((gray.astype(np.float32)) ** 2, -1, (block_size, block_size))
        std = np.sqrt(np.maximum(mean_sq - mean ** 2, 0))
        k = 0.3
        R = 128.0
        thresh = mean * (1 + k * (std / R - 1))
        bw = np.where(gray > thresh, 255, 0).astype(np.uint8)
    else:  # adaptive (default)
        bs = block_size if block_size % 2 == 1 else block_size + 1
        bw = cv2.adaptiveThreshold(gray, 255,
                                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, bs, C)

    return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)


def op_enhance_contrast(img, clip_limit=2.5, tile_size=8):
    """CLAHE 局部对比度增强"""
    _require_cv2()
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def op_sharpen(img, amount=1.0):
    """非锐化掩蔽锐化 (Unsharp Masking)"""
    _require_cv2()
    blurred = cv2.GaussianBlur(img, (0, 0), 3)
    sharpened = cv2.addWeighted(img, 1.0 + amount, blurred, -amount, 0)
    return sharpened


def op_remove_shadow(img):
    """形态学去阴影 (Morphological shadow removal)"""
    _require_cv2()
    rgb_planes = cv2.split(img)
    result_planes = []
    for plane in rgb_planes:
        dilated = cv2.dilate(plane, np.ones((7, 7), np.uint8))
        bg = cv2.medianBlur(dilated, 21)
        diff = 255 - cv2.absdiff(plane, bg)
        # Normalize
        norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        result_planes.append(norm)
    return cv2.merge(result_planes)


def op_auto_crop(img, padding=10):
    """自动裁剪到文档内容区域"""
    _require_cv2()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return img
    x, y, w, h = cv2.boundingRect(coords)
    # Add padding
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(img.shape[1] - x, w + 2 * padding)
    h = min(img.shape[0] - y, h + 2 * padding)
    return img[y:y + h, x:x + w]


def op_whiten_background(img, threshold=200):
    """将浅色背景漂白为纯白 (Background whitening)"""
    _require_cv2()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mask = gray > threshold
    result = img.copy()
    result[mask] = [255, 255, 255]
    return result


def op_brightness_contrast(img, brightness=0, contrast=1.0):
    """亮度 / 对比度调整"""
    _require_cv2()
    result = img.astype(np.float32)
    result = result * contrast + brightness
    return np.clip(result, 0, 255).astype(np.uint8)


def op_grayscale(img):
    """灰度化"""
    _require_cv2()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def op_curve_flatten(img, n_strips=40):
    """
    书页曲面平整化 - 通过多项式拟合边缘曲线，将弯曲书页逐条带展平。

    算法流程：
    1. 形态学处理找到文档主轮廓
    2. 沿 x 方向采样顶边/底边坐标，拟合多项式曲线
    3. 将图像切成 n_strips 条垂直细条带，每条带做透视变换展平
    4. 拼接所有条带并缩放回原尺寸
    """
    _require_cv2()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
    h, w = gray.shape

    # ── 1. 形态学处理找轮廓 ───────────────────────────────────────
    elem = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    morphed = cv2.GaussianBlur(gray, (5, 5), 0)
    morphed = cv2.dilate(morphed, elem, iterations=3)
    morphed = cv2.erode(morphed, elem, iterations=5)
    _, binary = cv2.threshold(morphed, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return img

    cnt = max(contours, key=cv2.contourArea)
    if cv2.contourArea(cnt) < 0.05 * h * w:
        return img

    # ── 2. 沿 x 采样顶边/底边 ────────────────────────────────────
    pts = cnt[:, 0, :]  # shape (N, 2)
    x_min = int(pts[:, 0].min())
    x_max = int(pts[:, 0].max())
    if x_max <= x_min:
        return img

    n_samples = n_strips + 1
    xs_sample = np.linspace(x_min, x_max, n_samples, dtype=int)
    bandwidth = max(2, (x_max - x_min) // (n_samples * 2))

    valid_xs, top_ys, bot_ys = [], [], []
    for x in xs_sample:
        near = pts[np.abs(pts[:, 0] - x) <= bandwidth]
        if len(near) == 0:
            near = pts[np.abs(pts[:, 0] - x) <= bandwidth * 3]
        if len(near) == 0:
            continue
        valid_xs.append(x)
        top_ys.append(int(near[:, 1].min()))
        bot_ys.append(int(near[:, 1].max()))

    if len(valid_xs) < 4:
        return img

    # ── 3. 多项式拟合顶/底曲线 ───────────────────────────────────
    deg = min(7, len(valid_xs) - 1)
    top_poly = np.poly1d(np.polyfit(valid_xs, top_ys, deg))
    bot_poly = np.poly1d(np.polyfit(valid_xs, bot_ys, deg))

    xs_strip = np.linspace(x_min, x_max, n_strips + 1)
    top_curve = np.clip(top_poly(xs_strip).astype(int), 0, h - 1)
    bot_curve = np.clip(bot_poly(xs_strip).astype(int), 0, h - 1)

    target_h = int(np.median(bot_curve - top_curve))
    if target_h <= 10:
        return img

    # ── 4. 逐条带透视变换并拼接 ──────────────────────────────────
    strips = []
    for i in range(n_strips):
        x0, x1 = int(xs_strip[i]), int(xs_strip[i + 1])
        if x1 <= x0:
            continue
        strip_w = x1 - x0
        src = np.float32([
            [x0, int(top_curve[i])],
            [x1, int(top_curve[i + 1])],
            [x0, int(bot_curve[i])],
            [x1, int(bot_curve[i + 1])],
        ])
        dst = np.float32([
            [0,       0],
            [strip_w, 0],
            [0,       target_h],
            [strip_w, target_h],
        ])
        M = cv2.getPerspectiveTransform(src, dst)
        warped = cv2.warpPerspective(img, M, (strip_w, target_h))
        strips.append(warped)

    if not strips:
        return img

    result = np.concatenate(strips, axis=1)
    result = cv2.resize(result, (w, h))
    return result


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_image(pil_img, ops: dict) -> Image.Image:
    """
    Apply a sequence of operations to a PIL image.
    ops: dict of {op_name: params_dict | bool}
    Returns processed PIL image.
    """
    _require_cv2()
    img = pil_to_cv2(pil_img)

    # Fixed ordering to avoid conflicts
    pipeline = [
        'remove_shadow',
        'curve_flatten',
        'perspective_correct',
        'deskew',
        'auto_crop',
        'denoise',
        'binarize',
        'enhance_contrast',
        'whiten_background',
        'sharpen',
        'brightness_contrast',
        'grayscale',
    ]

    for op_name in pipeline:
        if op_name not in ops:
            continue
        params = ops[op_name]
        if params is False or params is None:
            continue

        if not isinstance(params, dict):
            params = {}

        if op_name == 'remove_shadow':
            img = op_remove_shadow(img)
        elif op_name == 'curve_flatten':
            img = op_curve_flatten(img, **params)
        elif op_name == 'perspective_correct':
            img = op_perspective_correct(img)
        elif op_name == 'deskew':
            img = op_deskew(img)
        elif op_name == 'auto_crop':
            img = op_auto_crop(img, **params)
        elif op_name == 'denoise':
            img = op_denoise(img, **params)
        elif op_name == 'binarize':
            img = op_binarize(img, **params)
        elif op_name == 'enhance_contrast':
            img = op_enhance_contrast(img, **params)
        elif op_name == 'whiten_background':
            img = op_whiten_background(img, **params)
        elif op_name == 'sharpen':
            img = op_sharpen(img, **params)
        elif op_name == 'brightness_contrast':
            img = op_brightness_contrast(img, **params)
        elif op_name == 'grayscale':
            img = op_grayscale(img)

    return cv2_to_pil(img)
