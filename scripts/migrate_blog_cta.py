"""One-off migration: rewrite the closing CTA in existing blog posts.

Old generated posts ended with:
    "Bepul konsultatsiya uchun: t.me/Akramjon1984"
or a markdown variant of the same. New posts (after the AI prompt
change) point to https://trendoai.uz/order. This script updates
already-stored posts so the old Telegram link doesn't keep leaking
out of historical content.

Run locally or as a Render one-off shell:
    python -m scripts.migrate_blog_cta            # dry run
    python -m scripts.migrate_blog_cta --apply    # actually write
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app, db, Post  # noqa: E402

# Match either a bare URL or a markdown-wrapped one, with or without
# the "https://" / "@" prefix variants that have shown up in generated
# content over time.
PATTERNS = [
    re.compile(r"\[?t\.me/Akramjon1984\]?(?:\((?:https?://)?t\.me/Akramjon1984\))?", re.IGNORECASE),
    re.compile(r"\[?@?Akramjon1984\]?(?:\((?:https?://)?t\.me/Akramjon1984\))?", re.IGNORECASE),
]

NEW_LINK = "[trendoai.uz/order](https://trendoai.uz/order)"


def rewrite(content: str) -> tuple[str, bool]:
    new_content = content
    for pattern in PATTERNS:
        new_content = pattern.sub(NEW_LINK, new_content)
    return new_content, new_content != content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    args = parser.parse_args()

    with app.app_context():
        posts = Post.query.all()
        changed = 0
        for post in posts:
            new_content, did_change = rewrite(post.content or "")
            if did_change:
                changed += 1
                print(f"  #{post.id}  {post.title[:60]}")
                if args.apply:
                    post.content = new_content

        if args.apply and changed:
            db.session.commit()
            print(f"\nUpdated {changed} post(s).")
        elif changed:
            print(f"\nWould update {changed} post(s). Re-run with --apply.")
        else:
            print("Nothing to change.")


if __name__ == "__main__":
    main()
