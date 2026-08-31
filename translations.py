import os
import json
from utils.logger import setup_logger

logger = setup_logger("translations")

TRANSLATIONS = {}

def load_translations():
    global TRANSLATIONS
    base_dir = os.path.dirname(os.path.abspath(__file__))
    locales_dir = os.path.join(base_dir, 'translations_data')
    
    temp_dict = {}
    if os.path.exists(locales_dir):
        for filename in os.listdir(locales_dir):
            if filename.endswith('.json'):
                lang = filename.replace('.json', '')
                filepath = os.path.join(locales_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lang_data = json.load(f)
                        for key, text in lang_data.items():
                            if key not in temp_dict:
                                temp_dict[key] = {}
                            temp_dict[key][lang] = text
                except Exception as e:
                    logger.error(f"'{filename}' faylini o'qishda xatolik: {e}")
                    
    TRANSLATIONS.update(temp_dict)
    if TRANSLATIONS:
        logger.info(f"Tarjimalar yuklandi: {len(TRANSLATIONS)} ta qator.")

def get_translation(key, lang='uz', default=None):
    """Berilgan kalit va til uchun tarjimani qaytaradi."""
    if key in TRANSLATIONS and lang in TRANSLATIONS[key]:
        return TRANSLATIONS[key][lang]
    # Agar topilmasa, default qiymat qaytaramiz
    if default is not None:
        return default
    # Yo'qsa 'uz' tarjimasini yoki kalitni qaytaramiz
    return TRANSLATIONS.get(key, {}).get('uz', key)

# Dastur ishga tushganda avtomatik yuklash
load_translations()
