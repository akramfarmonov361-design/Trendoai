"""
TrendoAI brend PNG ikonkalarini 3D master logodan (`static/img/logo-3d.png`)
generatsiya qiladi:
- Sayt logotiplari (`logo-icon.png`, `logo.png`) va faviconlar (`favicon-32.png`,
  `favicon.png`, `favicon.ico`) uchun tashqi qora kvadrat fonni olib tashlab,
  3D dumaloq medalyonni silliq (anti-aliased) shaffof PNG ko'rinishiga keltiradi.
- iOS/PWA (`apple-touch-icon.png`, `pwa-*.png`, `icons/icon-*.png`) uchun
  maskable/to'liq fonli PNG yaratadi.

Ishlatish: venv\\Scripts\\python.exe scripts\\generate_icons.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from utils.logger import setup_logger

logger = setup_logger("generate_icons")

from PIL import Image, ImageDraw, ImageFilter, ImageFont

STATIC = os.path.join(ROOT, "static")
MASTER_LOGO_3D = os.path.join(STATIC, "img", "logo-3d.png")

SIZE = 512
INDIGO = (99, 102, 241)   # #6366f1
PURPLE = (168, 85, 247)   # #a855f7


def _fallback_master():
    img = Image.new("RGB", (SIZE, SIZE))
    px = img.load()
    denom = 2 * (SIZE - 1)
    for y in range(SIZE):
        for x in range(SIZE):
            t = (x + y) / denom
            px[x, y] = tuple(
                round(a + (b - a) * t) for a, b in zip(INDIGO, PURPLE)
            )

    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    alpha = 56
    d.line([(80, 390), (205, 270), (280, 315), (415, 175)],
           fill=(255, 255, 255, alpha), width=30, joint="curve")
    d.polygon([(432, 158), (442, 222), (372, 205)], fill=(255, 255, 255, alpha))

    font = None
    for name in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(name, 330)
            break
        except OSError:
            continue
    if font is None:
        raise SystemExit("Bold shrift topilmadi (arialbd.ttf)")
    d.text((SIZE / 2, SIZE / 2 + 10), "T", font=font, anchor="mm",
           fill=(255, 255, 255, 255))

    img = Image.alpha_composite(img.convert("RGBA"), overlay)

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1],
                                           radius=115, fill=255)
    img.putalpha(mask)
    return img, img


def _load_masters():
    """Returns (transparent_circular_master, full_bleed_pwa_master)."""
    if not os.path.exists(MASTER_LOGO_3D):
        return _fallback_master()

    with Image.open(MASTER_LOGO_3D) as src:
        raw = src.convert("RGBA")

    w, h = raw.size
    cx, cy = w // 2, h // 2
    # 1024x1024 masterda 3D medalyonning tashqi neon-kumush halqasi r=394 da tugaydi.
    medal_radius = int(min(w, h) * 0.386)  # ~395px (1024 da)

    # 4x supersampled anti-aliased doira maskasi
    scale = 4
    hi_mask = Image.new("L", (w * scale, h * scale), 0)
    d = ImageDraw.Draw(hi_mask)
    x0 = (cx - medal_radius) * scale
    y0 = (cy - medal_radius) * scale
    x1 = (cx + medal_radius) * scale
    y1 = (cy + medal_radius) * scale
    d.ellipse([x0, y0, x1, y1], fill=255)
    mask = hi_mask.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=0.8))

    transparent = raw.copy()
    transparent.putalpha(mask)

    # Tashqi bo'sh joyni qirqib, medalyonni kadrga sig'diramiz (ozgina 2% margin bilan)
    pad = int(medal_radius * 1.03)
    crop_box = (max(0, cx - pad), max(0, cy - pad), min(w, cx + pad), min(h, cy + pad))
    transparent_cropped = transparent.crop(crop_box).resize((SIZE, SIZE), Image.LANCZOS)

    # PWA / Apple touch icon uchun burchaklari yumaloqlangan yoki to'liq kadr
    pwa_crop_pad = int(medal_radius * 1.12)
    pwa_box = (
        max(0, cx - pwa_crop_pad),
        max(0, cy - pwa_crop_pad),
        min(w, cx + pwa_crop_pad),
        min(h, cy + pwa_crop_pad),
    )
    pwa_master = raw.crop(pwa_box).resize((SIZE, SIZE), Image.LANCZOS)

    return transparent_cropped, pwa_master


def main():
    transparent_master, pwa_master = _load_masters()

    # Shaffof dumaloq 3D PNG (sayt header/footer, admin, TMA, browser tab favicon)
    transparent_outputs = {
        "favicon-32.png": 32,
        "favicon.png": 192,
        os.path.join("img", "logo-icon.png"): 256,
        os.path.join("img", "logo.png"): 512,
    }
    for rel, size in transparent_outputs.items():
        path = os.path.join(STATIC, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        im = (
            transparent_master
            if transparent_master.size == (size, size)
            else transparent_master.resize((size, size), Image.LANCZOS)
        )
        im.save(path, format="PNG", optimize=True)
        logger.info(f"[transparent] {rel}: {size}x{size}, {os.path.getsize(path) // 1024}KB")

    # PWA va iOS home screen ikonkalari (maskable full-bleed)
    pwa_outputs = {
        "apple-touch-icon.png": 180,
        "pwa-192.png": 192,
        "pwa-512.png": 512,
    }
    for name in (72, 96, 128, 144, 152, 192, 384, 512):
        pwa_outputs[os.path.join("icons", f"icon-{name}x{name}.png")] = name

    for rel, size in pwa_outputs.items():
        path = os.path.join(STATIC, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        im = (
            pwa_master
            if pwa_master.size == (size, size)
            else pwa_master.resize((size, size), Image.LANCZOS)
        )
        im.save(path, format="PNG", optimize=True)
        logger.info(f"[pwa] {rel}: {size}x{size}, {os.path.getsize(path) // 1024}KB")

    ico_path = os.path.join(STATIC, "favicon.ico")
    ico_base = transparent_master.resize((256, 256), Image.LANCZOS)
    ico_base.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    logger.info(f"[transparent] favicon.ico: {os.path.getsize(ico_path) // 1024}KB")


if __name__ == "__main__":
    main()
