"""
TrendoAI Instagram Highlights Generator
Generates both SVG and 1080x1080 high-res PNG highlight covers,
plus an interactive HTML showcase.
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "img", "instagram_highlights")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
if not os.path.exists(FONT_BOLD):
    FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"

FONT_REGULAR = "C:/Windows/Fonts/segoeui.ttf"
if not os.path.exists(FONT_REGULAR):
    FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"

HIGHLIGHTS = [
    {
        "id": "xizmatlar",
        "title": "XIZMATLAR",
        "subtitle": "IT & AI YECHIMLAR",
        "icon": "code",
        "primary": "#6366f1",
        "secondary": "#a855f7",
        "accent": "#f472b6",
        "rgb_primary": (99, 102, 241),
        "rgb_secondary": (168, 85, 247),
        "rgb_accent": (244, 114, 182),
    },
    {
        "id": "keyslar",
        "title": "KEYSLAR",
        "subtitle": "PORTFOLIO & NATIJALAR",
        "icon": "rocket",
        "primary": "#6366f1",
        "secondary": "#06b6d4",
        "accent": "#38bdf8",
        "rgb_primary": (99, 102, 241),
        "rgb_secondary": (6, 182, 212),
        "rgb_accent": (56, 189, 248),
    },
    {
        "id": "narxlar",
        "title": "NARXLAR",
        "subtitle": "SHAFFOF TARIFLAR",
        "icon": "diamond",
        "primary": "#ec4899",
        "secondary": "#8b5cf6",
        "accent": "#f472b6",
        "rgb_primary": (236, 72, 153),
        "rgb_secondary": (139, 92, 246),
        "rgb_accent": (244, 114, 182),
    },
    {
        "id": "fikrlar",
        "title": "FIKRLAR",
        "subtitle": "MIJOZLAR SHARHLARI",
        "icon": "chat",
        "primary": "#f43f5e",
        "secondary": "#fb7185",
        "accent": "#facc15",
        "rgb_primary": (244, 63, 94),
        "rgb_secondary": (251, 113, 133),
        "rgb_accent": (250, 204, 21),
    },
    {
        "id": "ai_maslahat",
        "title": "AI MASLAHAT",
        "subtitle": "FOYDALI BIZNES TIPS",
        "icon": "brain",
        "primary": "#06b6d4",
        "secondary": "#6366f1",
        "accent": "#38bdf8",
        "rgb_primary": (6, 182, 212),
        "rgb_secondary": (99, 102, 241),
        "rgb_accent": (56, 189, 248),
    },
]

def generate_svgs():
    """Generate modern, vector SVG files for each highlight."""
    icon_svgs = {
        "code": """
            <!-- Code Brackets & Chip -->
            <path d="M420 440 L340 500 L420 560" stroke="url(#grad)" stroke-width="26" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
            <path d="M660 440 L740 500 L660 560" stroke="url(#grad)" stroke-width="26" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
            <path d="M570 410 L510 590" stroke="{accent}" stroke-width="24" stroke-linecap="round" fill="none"/>
            <circle cx="540" cy="500" r="14" fill="{accent}"/>
        """,
        "rocket": """
            <!-- Rocket Launch -->
            <g transform="translate(540, 485) rotate(-45) translate(-540, -485)">
                <!-- Body -->
                <path d="M540 370 C600 420 600 520 580 570 L500 570 C480 520 480 420 540 370 Z" fill="url(#grad)" />
                <!-- Window -->
                <circle cx="540" cy="460" r="26" fill="#0b0f19" stroke="{accent}" stroke-width="10"/>
                <!-- Fins -->
                <path d="M490 530 L440 570 L485 570 Z" fill="{accent}"/>
                <path d="M590 530 L640 570 L595 570 Z" fill="{accent}"/>
                <!-- Flame -->
                <path d="M515 580 Q540 640 565 580 Z" fill="#fbbf24"/>
                <path d="M525 580 Q540 615 555 580 Z" fill="#f43f5e"/>
            </g>
        """,
        "diamond": """
            <!-- Sparkling Diamond -->
            <polygon points="540,390 670,470 540,610 410,470" fill="none" stroke="url(#grad)" stroke-width="24" stroke-linejoin="round"/>
            <polygon points="540,390 600,470 540,610 480,470" fill="url(#grad)" opacity="0.35"/>
            <line x1="410" y1="470" x2="670" y2="470" stroke="url(#grad)" stroke-width="18"/>
            <line x1="480" y1="470" x2="540" y2="390" stroke="{accent}" stroke-width="16"/>
            <line x1="600" y1="470" x2="540" y2="390" stroke="{accent}" stroke-width="16"/>
            <!-- Sparkles -->
            <circle cx="680" cy="410" r="10" fill="{accent}"/>
            <circle cx="390" cy="550" r="8" fill="{accent}"/>
        """,
        "chat": """
            <!-- Dual Chat Bubbles with Star -->
            <!-- Main Bubble -->
            <path d="M400 400 H640 C680 400 710 430 710 470 V530 C710 570 680 600 640 600 H550 L470 650 V600 H400 C360 600 330 570 330 530 V470 C330 430 360 400 400 400 Z" fill="none" stroke="url(#grad)" stroke-width="22" stroke-linejoin="round"/>
            <!-- Central Star -->
            <polygon points="520,455 532,488 568,488 539,509 550,542 520,522 490,542 501,509 472,488 508,488" fill="{accent}"/>
        """,
        "brain": """
            <!-- AI Neural Brain -->
            <g transform="translate(540, 485) scale(1.15) translate(-540, -485)">
                <!-- Brain Left Hemisphere -->
                <path d="M520 400 C470 400 430 435 430 475 C430 495 440 515 455 525 C440 540 440 565 460 580 C480 595 510 590 520 585" fill="none" stroke="url(#grad)" stroke-width="20" stroke-linecap="round"/>
                <!-- Brain Right Hemisphere -->
                <path d="M560 400 C610 400 650 435 650 475 C650 495 640 515 625 525 C640 540 640 565 620 580 C600 595 570 590 560 585" fill="none" stroke="url(#grad)" stroke-width="20" stroke-linecap="round"/>
                <!-- Center Neural Nodes & Lightning -->
                <circle cx="540" cy="430" r="12" fill="{accent}"/>
                <circle cx="540" cy="555" r="12" fill="{accent}"/>
                <path d="M545 450 L530 490 L555 490 L535 535" stroke="#fbbf24" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
            </g>
        """
    }

    for item in HIGHLIGHTS:
        icon_code = icon_svgs[item["icon"]].format(accent=item["accent"])
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" width="1080" height="1080">
  <defs>
    <!-- Background Radial Glow -->
    <radialGradient id="bgGlow" cx="50%" cy="48%" r="50%">
      <stop offset="0%" stop-color="{item['primary']}" stop-opacity="0.32" />
      <stop offset="45%" stop-color="{item['secondary']}" stop-opacity="0.12" />
      <stop offset="100%" stop-color="#07090e" stop-opacity="1" />
    </radialGradient>

    <!-- Main Ring Linear Gradient -->
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{item['primary']}" />
      <stop offset="60%" stop-color="{item['secondary']}" />
      <stop offset="100%" stop-color="{item['accent']}" />
    </linearGradient>

    <!-- Subtle Outer Ring Gradient -->
    <linearGradient id="ringGrad" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{item['primary']}" stop-opacity="0.9" />
      <stop offset="50%" stop-color="{item['accent']}" stop-opacity="0.4" />
      <stop offset="100%" stop-color="{item['secondary']}" stop-opacity="0.85" />
    </linearGradient>

    <!-- Glow Filter -->
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="30" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Deep Obsidian Canvas -->
  <rect width="1080" height="1080" fill="#07090e" />
  <circle cx="540" cy="500" r="500" fill="url(#bgGlow)" />

  <!-- Outer Ambient Glow Ring -->
  <circle cx="540" cy="485" r="380" fill="none" stroke="{item['primary']}" stroke-width="2" opacity="0.2" />

  <!-- Instagram Story Cutout Safe Guide Circle (Glassmorphic Container) -->
  <circle cx="540" cy="485" r="350" fill="#0c1222" fill-opacity="0.78" stroke="url(#ringGrad)" stroke-width="8" filter="url(#glow)" />
  <circle cx="540" cy="485" r="350" fill="none" stroke="url(#ringGrad)" stroke-width="8" />

  <!-- Inner High-Tech Dotted Ring -->
  <circle cx="540" cy="485" r="310" fill="none" stroke="{item['accent']}" stroke-width="3" stroke-dasharray="14 18" opacity="0.45" />

  <!-- Center Feature Icon -->
  <g>
    {icon_code}
  </g>

  <!-- Top Brand Tag -->
  <text x="540" y="220" text-anchor="middle" fill="#94a3b8" font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif" font-size="24" font-weight="700" letter-spacing="10" opacity="0.75">TRENDO AI</text>

  <!-- Title Label -->
  <text x="540" y="930" text-anchor="middle" fill="#ffffff" font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif" font-size="52" font-weight="900" letter-spacing="8">{item['title']}</text>

  <!-- Subtitle Label -->
  <text x="540" y="980" text-anchor="middle" fill="{item['accent']}" font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif" font-size="24" font-weight="700" letter-spacing="4" opacity="0.9">{item['subtitle']}</text>
</svg>"""
        file_path = os.path.join(OUTPUT_DIR, f"{item['id']}.svg")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

    print("SVG highlights generated successfully!")


def generate_pngs():
    """Generate high-res 1080x1080 PNG images using Pillow."""
    size = (1080, 1080)
    center = (540, 485)
    radius = 350

    try:
        font_brand = ImageFont.truetype(FONT_BOLD, 26)
        font_title = ImageFont.truetype(FONT_BOLD, 54)
        font_sub = ImageFont.truetype(FONT_BOLD, 24)
    except Exception:
        font_brand = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    for item in HIGHLIGHTS:
        # 1. Base dark image
        img = Image.new("RGBA", size, (7, 9, 14, 255))
        draw = ImageDraw.Draw(img)

        # 2. Radial glow behind circle
        glow_layer = Image.new("RGBA", size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        p_col = item["rgb_primary"]
        glow_draw.ellipse([center[0]-380, center[1]-380, center[0]+380, center[1]+380], fill=(p_col[0], p_col[1], p_col[2], 75))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(80))
        img = Image.alpha_composite(img, glow_layer)
        draw = ImageDraw.Draw(img)

        # 3. Outer glass circle
        draw.ellipse([center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius],
                     fill=(12, 18, 34, 215), outline=item["rgb_primary"], width=8)

        # 4. Inner accent ring
        draw.ellipse([center[0]-310, center[1]-310, center[0]+310, center[1]+310],
                     outline=(item["rgb_accent"][0], item["rgb_accent"][1], item["rgb_accent"][2], 120), width=3)

        # 5. Icon drawing based on type
        icon = item["icon"]
        acc = item["rgb_accent"]
        prim = item["rgb_primary"]

        if icon == "code":
            # Left bracket <
            draw.line([(center[0]-120, center[1]-60), (center[0]-190, center[1]), (center[0]-120, center[1]+60)], fill=prim, width=24)
            # Right bracket >
            draw.line([(center[0]+120, center[1]-60), (center[0]+190, center[1]), (center[0]+120, center[1]+60)], fill=prim, width=24)
            # Slash /
            draw.line([(center[0]+35, center[1]-95), (center[0]-35, center[1]+95)], fill=acc, width=22)
            # Center AI core dot
            draw.ellipse([center[0]-15, center[1]-15, center[0]+15, center[1]+15], fill=acc)

        elif icon == "rocket":
            # Rocket body
            draw.polygon([
                (center[0], center[1]-120),
                (center[0]+65, center[1]+40),
                (center[0]-65, center[1]+40)
            ], fill=prim)
            # Fins
            draw.polygon([(center[0]-60, center[1]), (center[0]-110, center[1]+50), (center[0]-60, center[1]+50)], fill=acc)
            draw.polygon([(center[0]+60, center[1]), (center[0]+110, center[1]+50), (center[0]+60, center[1]+50)], fill=acc)
            # Porthole window
            draw.ellipse([center[0]-25, center[1]-30, center[0]+25, center[1]+20], fill=(11, 15, 25), outline=acc, width=8)
            # Exhaust flame
            draw.polygon([(center[0]-25, center[1]+50), (center[0]+25, center[1]+50), (center[0], center[1]+115)], fill=(251, 191, 36))
            draw.polygon([(center[0]-12, center[1]+50), (center[0]+12, center[1]+50), (center[0], center[1]+85)], fill=(244, 63, 94))

        elif icon == "diamond":
            # Faceted diamond
            draw.polygon([
                (center[0], center[1]-110),
                (center[0]+130, center[1]-20),
                (center[0], center[1]+120),
                (center[0]-130, center[1]-20)
            ], outline=prim, width=22)
            draw.line([(center[0]-130, center[1]-20), (center[0]+130, center[1]-20)], fill=prim, width=16)
            draw.line([(center[0]-60, center[1]-20), (center[0], center[1]-110)], fill=acc, width=16)
            draw.line([(center[0]+60, center[1]-20), (center[0], center[1]-110)], fill=acc, width=16)
            draw.line([(center[0]-60, center[1]-20), (center[0], center[1]+120)], fill=acc, width=14)
            draw.line([(center[0]+60, center[1]-20), (center[0], center[1]+120)], fill=acc, width=14)
            # Sparkle dots
            draw.ellipse([center[0]+145, center[1]-75, center[0]+165, center[1]-55], fill=acc)
            draw.ellipse([center[0]-155, center[1]+55, center[0]-135, center[1]+75], fill=acc)

        elif icon == "chat":
            # Speech bubble
            draw.rounded_rectangle([center[0]-170, center[1]-95, center[0]+170, center[1]+70], radius=35, outline=prim, width=22)
            # Bubble tail
            draw.polygon([(center[0]-60, center[1]+70), (center[0]-120, center[1]+130), (center[0]-10, center[1]+70)], fill=prim)
            # Center gold star
            star_pts = []
            for i in range(10):
                angle = i * math.pi / 5 - math.pi / 2
                r = 45 if i % 2 == 0 else 20
                star_pts.append((center[0] + r * math.cos(angle), center[1]-10 + r * math.sin(angle)))
            draw.polygon(star_pts, fill=acc)

        elif icon == "brain":
            # Neural lobes
            draw.arc([center[0]-130, center[1]-110, center[0]+10, center[1]+30], start=130, end=350, fill=prim, width=22)
            draw.arc([center[0]-10, center[1]-110, center[0]+130, center[1]+30], start=190, end=50, fill=prim, width=22)
            draw.arc([center[0]-140, center[1]-30, center[0]+10, center[1]+100], start=110, end=320, fill=prim, width=20)
            draw.arc([center[0]-10, center[1]-30, center[0]+140, center[1]+100], start=220, end=70, fill=prim, width=20)
            # Synaptic center nodes
            draw.ellipse([center[0]-14, center[1]-80, center[0]+14, center[1]-52], fill=acc)
            draw.ellipse([center[0]-14, center[1]+60, center[0]+14, center[1]+88], fill=acc)
            # Lightning spark
            draw.line([(center[0]+8, center[1]-45), (center[0]-18, center[1]), (center[0]+18, center[1]), (center[0]-8, center[1]+45)], fill=(251, 191, 36), width=16)

        # 6. Text Labels
        brand_text = "TRENDO AI"
        draw.text((center[0], 220), brand_text, fill=(148, 163, 184), font=font_brand, anchor="mm")

        title_text = item["title"]
        draw.text((center[0], 930), title_text, fill=(255, 255, 255), font=font_title, anchor="mm")

        sub_text = item["subtitle"]
        draw.text((center[0], 980), sub_text, fill=acc, font=font_sub, anchor="mm")

        # Save PNG
        out_png = os.path.join(OUTPUT_DIR, f"{item['id']}.png")
        img.save(out_png, "PNG", quality=95)

    print("PNG highlights generated successfully!")


def generate_html_showcase():
    """Generate an interactive HTML showcase with live preview and download links."""
    cards_html = ""
    for item in HIGHLIGHTS:
        cards_html += f"""
        <div class="highlight-card">
            <div class="preview-circle">
                <img src="/static/img/instagram_highlights/{item['id']}.png" alt="{item['title']}">
            </div>
            <div class="card-info">
                <h3>{item['title']}</h3>
                <p>{item['subtitle']}</p>
                <div class="btn-group">
                    <a href="/static/img/instagram_highlights/{item['id']}.png" download="{item['id']}.png" class="btn btn-primary">
                        📥 PNG (1080x1080)
                    </a>
                    <a href="/static/img/instagram_highlights/{item['id']}.svg" download="{item['id']}.svg" class="btn btn-secondary">
                        Vector SVG
                    </a>
                </div>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrendoAI — Instagram Highlights To'plami</title>
    <link rel="icon" type="image/png" href="/static/img/logo-icon.png">
    <style>
        :root {{
            --bg: #07090e;
            --card-bg: #0f172a;
            --primary: #6366f1;
            --accent: #f472b6;
            --text: #f8fafc;
            --text-muted: #94a3b8;
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
        }}
        body {{
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .header {{
            text-align: center;
            max-width: 700px;
            margin-bottom: 50px;
        }}
        .header h1 {{
            font-size: 2.4rem;
            margin-bottom: 12px;
            background: linear-gradient(135deg, #fff 0%, #cbd5e1 50%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header p {{
            color: var(--text-muted);
            font-size: 1.1rem;
            line-height: 1.6;
        }}
        .phone-mockup {{
            background: #111827;
            border: 2px solid #1f2937;
            border-radius: 40px;
            padding: 24px 16px;
            box-shadow: 0 25px 60px -15px rgba(99, 102, 241, 0.25);
            max-width: 480px;
            width: 100%;
            margin-bottom: 50px;
        }}
        .phone-header {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
        .phone-avatar {{
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            padding: 2px;
        }}
        .phone-avatar img {{
            width: 100%;
            height: 100%;
            border-radius: 50%;
            object-fit: cover;
            background: #000;
        }}
        .phone-meta h4 {{
            font-size: 1.1rem;
            margin-bottom: 4px;
        }}
        .phone-meta span {{
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
        .stories-bar {{
            display: flex;
            gap: 16px;
            overflow-x: auto;
            padding-bottom: 10px;
            scrollbar-width: thin;
        }}
        .story-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            flex-shrink: 0;
        }}
        .story-circle {{
            width: 72px;
            height: 72px;
            border-radius: 50%;
            padding: 2px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            cursor: pointer;
            transition: transform 0.2s ease;
        }}
        .story-circle:hover {{
            transform: scale(1.08);
        }}
        .story-circle img {{
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: #000;
            object-fit: cover;
        }}
        .story-label {{
            font-size: 0.72rem;
            color: #cbd5e1;
            font-weight: 500;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            max-width: 1100px;
            width: 100%;
        }}
        .highlight-card {{
            background: var(--card-bg);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 24px;
            text-align: center;
            transition: all 0.3s ease;
        }}
        .highlight-card:hover {{
            transform: translateY(-6px);
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 16px 36px rgba(0,0,0,0.4);
        }}
        .preview-circle {{
            width: 170px;
            height: 170px;
            margin: 0 auto 20px;
            border-radius: 50%;
            overflow: hidden;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            border: 3px solid rgba(255,255,255,0.1);
        }}
        .preview-circle img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .card-info h3 {{
            font-size: 1.3rem;
            margin-bottom: 6px;
        }}
        .card-info p {{
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-bottom: 20px;
        }}
        .btn-group {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 16px;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: 600;
            text-decoration: none;
            transition: opacity 0.2s;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, var(--primary), var(--accent));
            color: #fff;
        }}
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.06);
            color: #cbd5e1;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }}
        .btn:hover {{
            opacity: 0.9;
        }}
        .instructions {{
            max-width: 800px;
            background: rgba(99, 102, 241, 0.07);
            border: 1px solid rgba(99, 102, 241, 0.25);
            border-radius: 16px;
            padding: 24px;
            margin-top: 50px;
            width: 100%;
        }}
        .instructions h3 {{
            margin-bottom: 12px;
            color: var(--accent);
        }}
        .instructions ol {{
            padding-left: 20px;
            color: var(--text-muted);
            line-height: 1.8;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>TrendoAI Instagram Highlights</h1>
        <p>Saytingiz uslubi (Indigo & Neon Accent) bilan to'liq uyg'unlashtirilgan 5 ta asosiy bo'lim muqovalari.</p>
    </div>

    <!-- Phone Live Preview -->
    <div class="phone-mockup">
        <div class="phone-header">
            <div class="phone-avatar">
                <img src="/static/img/logo-icon.png" alt="TrendoAI">
            </div>
            <div class="phone-meta">
                <h4>trendoai_uz</h4>
                <span>TrendoAI | Sun'iy Intellekt va IT</span>
            </div>
        </div>
        <div class="stories-bar">
            <div class="story-item">
                <div class="story-circle">
                    <img src="/static/img/instagram_highlights/xizmatlar.png" alt="Xizmatlar">
                </div>
                <span class="story-label">Xizmatlar</span>
            </div>
            <div class="story-item">
                <div class="story-circle">
                    <img src="/static/img/instagram_highlights/keyslar.png" alt="Keyslar">
                </div>
                <span class="story-label">Keyslar</span>
            </div>
            <div class="story-item">
                <div class="story-circle">
                    <img src="/static/img/instagram_highlights/narxlar.png" alt="Narxlar">
                </div>
                <span class="story-label">Narxlar</span>
            </div>
            <div class="story-item">
                <div class="story-circle">
                    <img src="/static/img/instagram_highlights/fikrlar.png" alt="Fikrlar">
                </div>
                <span class="story-label">Fikrlar</span>
            </div>
            <div class="story-item">
                <div class="story-circle">
                    <img src="/static/img/instagram_highlights/ai_maslahat.png" alt="AI Tips">
                </div>
                <span class="story-label">AI Maslahat</span>
            </div>
        </div>
    </div>

    <!-- Grid of download cards -->
    <div class="grid">
        {cards_html}
    </div>

    <!-- Instruction box -->
    <div class="instructions">
        <h3>📲 Instagram profilga o'rnatish yo'riqnomasi:</h3>
        <ol>
            <li>Tepadagi har bir bo'lim uchun <strong>PNG (1080x1080)</strong> tugmasini bosib rasmlarni yuklab oling.</li>
            <li>Instagram ilovasida profilingizga kiring va <strong>Story</strong> bo'limiga tegishli mavzudagi rasmlar yoki ma'lumotlarni qo'ying.</li>
            <li>Story'ni <strong>"Highlight"</strong> (Aktualnie) ga qo'shing.</li>
            <li>Highlight nomini kiriting va <strong>"Edit Cover"</strong> (Muqovani tahrirlash) tugmasini bosing.</li>
            <li>Yuklab olingan mos rasmni tanlang va saqlang!</li>
        </ol>
    </div>
</body>
</html>
"""
    showcase_path = os.path.join(os.path.dirname(OUTPUT_DIR), "..", "instagram_highlights_showcase.html")
    with open(showcase_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML showcase generated successfully!")


if __name__ == "__main__":
    generate_svgs()
    generate_pngs()
    generate_html_showcase()
    print("All Instagram highlight assets have been generated!")
