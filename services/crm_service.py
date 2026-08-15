"""
TrendoAI CRM va Lead xizmati.
Kontaktlarni aniqlash va adminga avtomatik xabar yuborish.
"""
import re
from datetime import datetime
from extensions import db
from models.interaction import Lead
from telegram_poster import send_admin_alert

CONTACT_PATTERN = re.compile(r'(\+?998[0-9\s\-]{9,13}|\b9[0-9]{8}\b|@[a-zA-Z0-9_]{4,})')


def extract_contact(text):
    """Matndan telefon raqam yoki Telegram username ajratib olish"""
    if not text:
        return None
    match = CONTACT_PATTERN.search(text)
    return match.group(0).strip() if match else None


def capture_lead_from_message(message_text, source="AI Chat Vidjet", default_name="AI Chat Mijoz"):
    """
    Xabardan kontaktni qidirib, topilsa bazaga Lead sifatida saqlash va Adminga alert yuborish.
    """
    contact = extract_contact(message_text)
    if not contact:
        return None

    try:
        new_lead = Lead(
            name=default_name,
            contact=contact,
            source=source
        )
        db.session.add(new_lead)
        db.session.commit()

        time_str = datetime.now().strftime('%d.%m.%Y %H:%M')
        alert_text = (
            f"🎯 <b>YANGI LEAD ({source})!</b>\n\n"
            f"💬 <b>Xabar:</b> {message_text}\n"
            f"📞 <b>Kontakt:</b> {contact}\n"
            f"⏰ <b>Vaqt:</b> {time_str}"
        )
        send_admin_alert(alert_text)
        print(f"[crm] Lead muvaffaqiyatli saqlandi va adminga yuborildi: {contact}")
        return new_lead
    except Exception as exc:
        db.session.rollback()
        print(f"[crm] Lead saqlashda xatolik: {exc}")
        return None
