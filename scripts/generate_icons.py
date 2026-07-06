"""
TrendoAI brend ikonkalarini bitta 512px masterdan generatsiya qiladi.
Dizayn static/favicon.svg bilan bir xil: indigo->binafsha gradient,
orqa fonda trend chizig'i, oq "T" harfi.

Ishlatish: venv\\Scripts\\python.exe scripts\\generate_icons.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

SIZE = 512
INDIGO = (99, 102, 241)   # #6366f1
PURPLE = (168, 85, 247)   # #a855f7


def _master():
    # Diagonal gradient
    img = Image.new("RGB", (SIZE, SIZE))
    px = img.load()
    denom = 2 * (SIZE - 1)
    for y in range(SIZE):
        for x in range(SIZE):
            t = (x + y) / denom
            px[x, y] = tuple(
                round(a + (b - a) * t) for a, b in zip(INDIGO, PURPLE)
            )

    # Trend chizig'i (yarim shaffof oq)
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    alpha = 56  # ~22%
    d.line([(80, 390), (205, 270), (280, 315), (415, 175)],
           fill=(255, 255, 255, alpha), width=30, joint="curve")
    d.polygon([(432, 158), (442, 222), (372, 205)], fill=(255, 255, 255, alpha))

    # "T" harfi
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

    # Burchaklarni yumaloqlash
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1],
                                           radius=115, fill=255)
    img.putalpha(mask)
    return img


def main():
    master = _master()

    outputs = {
        "favicon-32.png": 32,
        "favicon.png": 192,
        "apple-touch-icon.png": 180,
        "pwa-192.png": 192,
        "pwa-512.png": 512,
        os.path.join("img", "logo-icon.png"): 128,
        os.path.join("img", "logo.png"): 512,
    }
    for name in (72, 96, 128, 144, 152, 192, 384, 512):
        outputs[os.path.join("icons", f"icon-{name}x{name}.png")] = name

    for rel, size in outputs.items():
        path = os.path.join(STATIC, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        im = master if size == SIZE else master.resize((size, size), Image.LANCZOS)
        im.save(path, optimize=True)
        print(f"{rel}: {size}x{size}, {os.path.getsize(path) // 1024}KB")


if __name__ == "__main__":
    main()
