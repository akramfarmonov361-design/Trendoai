#!/usr/bin/env python3
"""Static rasmlarni xavfsiz optimallashtirish.

Nega kerak: portfolio JPG'lari 1200x896 o'lchamda 700+ KB edi — bitta
sahifa uchun 1.5 MB ortiqcha trafik. Qayta kodlash (JPEG quality 84,
progressive) o'lchamni bir necha barobar kichraytiradi, ko'zga sezilarli
farq qoldirmaydi.

Ishlatish::

    python scripts/optimize_static_images.py            # faqat hisobot
    python scripts/optimize_static_images.py --apply    # yozish

    # WebP'larni ham qayta kodlash (quality 80)
    python scripts/optimize_static_images.py --include-webp --min-kb 60 --apply

Standart holatda faqat JPEG fayllar tegadi. PNG va SVG hech qachon
o'zgartirilmaydi. Natija originaldan kichik bo'lmasa (yoki 5% dan kam
yutqazsa), fayl o'zgartirilmaydi.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = PROJECT_ROOT / "static" / "img"
JPEG_SUFFIXES = {".jpg", ".jpeg"}
WEBP_SUFFIXES = {".webp"}


def _to_rgb(image):
    """Shaffoflikni oq fonga qo'yib, JPEG uchun RGB ga o'tkazadi."""
    if image.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        rgba = image.convert("RGBA")
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def _resize(image, max_width):
    if max_width and image.width > max_width:
        height = round(image.height * max_width / image.width)
        return image.resize((max_width, height), Image.Resampling.LANCZOS)
    return image


def _finish(before, tmp_path):
    after = tmp_path.stat().st_size
    if after >= before * 0.95:
        tmp_path.unlink(missing_ok=True)
        return before, before, None
    return before, after, tmp_path


def optimize_jpeg(path, quality, max_width):
    """JPEG'ni vaqtinchalik faylga qayta kodlaydi.

    Qaytaradi: ``(before_bytes, after_bytes, tmp_path | None)``.
    ``tmp_path`` faqat natija haqiqatan kichik bo'lsa to'ldiriladi.
    """
    before = path.stat().st_size

    with Image.open(path) as source:
        image = _resize(_to_rgb(ImageOps.exif_transpose(source)), max_width)

        tmp_path = path.with_name(path.name + ".optimizing")
        image.save(
            tmp_path,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
        )

    return _finish(before, tmp_path)


def optimize_webp(path, quality, max_width):
    """WebP'ni sifatni saqlab qayta kodlaydi (shaffoflik yo'qolmaydi)."""
    before = path.stat().st_size

    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        has_alpha = image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        )
        image = image.convert("RGBA" if has_alpha else "RGB")
        image = _resize(image, max_width)

        tmp_path = path.with_name(path.name + ".optimizing")
        image.save(tmp_path, format="WEBP", quality=quality, method=6)

    return _finish(before, tmp_path)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="static/img ichidagi katta JPEG fayllarni optimallashtiradi."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Natijani faylga yozadi (standart: faqat hisobot).",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=DEFAULT_DIR,
        help=f"Tekshiriladigan papka (standart: {DEFAULT_DIR}).",
    )
    parser.add_argument(
        "--min-kb",
        type=int,
        default=300,
        help="Faqat shu hajmdan katta fayllar (KB, standart: 300).",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=84,
        help="JPEG sifati 1-95 (standart: 84).",
    )
    parser.add_argument(
        "--include-webp",
        action="store_true",
        help="WebP fayllarni ham qayta kodlaydi.",
    )
    parser.add_argument(
        "--no-jpeg",
        action="store_true",
        help="JPEG'larni chetlab o'tib, faqat WebP bilan ishlaydi.",
    )
    parser.add_argument(
        "--webp-quality",
        type=int,
        default=80,
        help="WebP sifati 1-95 (standart: 80).",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=1600,
        help="Maksimal kenglik; kichik rasmlar kattalashtirilmaydi (standart: 1600).",
    )
    args = parser.parse_args()

    suffixes = set() if args.no_jpeg else set(JPEG_SUFFIXES)
    if args.include_webp:
        suffixes |= WEBP_SUFFIXES

    # Nisbiy `--directory` ham to'g'ri ishlashi uchun absolyut yo'lga keltiramiz.
    directory = args.directory.resolve()
    files = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    )

    rows = []
    total_before = 0
    total_after = 0

    for path in files:
        if path.stat().st_size < args.min_kb * 1024:
            continue

        if path.suffix.lower() in WEBP_SUFFIXES:
            before, after, tmp_path = optimize_webp(
                path, args.webp_quality, args.max_width
            )
        else:
            before, after, tmp_path = optimize_jpeg(
                path, args.quality, args.max_width
            )
        total_before += before
        total_after += after
        rows.append((path, before, after))

        if tmp_path is not None:
            if args.apply:
                tmp_path.replace(path)
            else:
                tmp_path.unlink()

    for path, before, after in rows:
        saved = 100 - (after / before * 100) if before else 0
        print(
            f"{before / 1024:8.0f} -> {after / 1024:8.0f} KB "
            f"({saved:4.0f}% kam)  {path.relative_to(PROJECT_ROOT)}"
        )

    if not rows:
        print("Optimallashtirish kerak bo'lgan JPEG topilmadi.")
        return

    saved_mb = (total_before - total_after) / (1024 * 1024)
    print(
        f"\nJami: {total_before / (1024 * 1024):.1f} MB -> "
        f"{total_after / (1024 * 1024):.1f} MB "
        f"(tejaldi {saved_mb:.1f} MB, {len(rows)} fayl)"
    )
    if not args.apply:
        print("Dry-run: hech narsa yozilmadi. Qo'llash uchun --apply qo'shing.")


if __name__ == "__main__":
    main()
