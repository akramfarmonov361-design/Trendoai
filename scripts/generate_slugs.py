import sys
import os
import re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.logger import setup_logger
logger = setup_logger("generate_slugs")


from app import app, db, Portfolio

def generate_slug(title):
    """Sarlavhadan slug yaratish"""
    if not title:
        return None
    
    # O'zbek harflarini translit qilish
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'ў': 'o', 'қ': 'q', 'ғ': 'g', 'ҳ': 'h',
        "'": '', "'": '', "ʻ": '', "ʼ": ''
    }
    
    slug = title.lower()
    
    # Translit
    for cyr, lat in translit_map.items():
        slug = slug.replace(cyr, lat)
        slug = slug.replace(cyr.upper(), lat.capitalize() if lat else '')
    
    # Faqat harflar, raqamlar va tire
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    
    return slug if slug else None


def migrate_slugs():
    """Barcha portfolio elementlariga slug qo'shish"""
    with app.app_context():
        logger.info("Generating slugs for portfolio items...")
        
        portfolios = Portfolio.query.all()
        updated = 0
        
        for item in portfolios:
            if not item.slug:
                new_slug = generate_slug(item.title)
                if new_slug:
                    # Unique slug yaratish
                    base_slug = new_slug
                    counter = 1
                    while Portfolio.query.filter_by(slug=new_slug).first():
                        new_slug = f"{base_slug}-{counter}"
                        counter += 1
                    
                    item.slug = new_slug
                    updated += 1
                    logger.info(f"  [{item.id}] {item.title} -> {new_slug}")
        
        if updated > 0:
            db.session.commit()
            logger.info(f"\n✅ Successfully updated {updated} portfolio items with slugs.")
        else:
            logger.info("\n✅ All portfolio items already have slugs.")


if __name__ == "__main__":
    migrate_slugs()
