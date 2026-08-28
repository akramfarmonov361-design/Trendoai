"""
TrendoAI CRM va Lead xizmati.
Kontaktlarni aniqlash va adminga avtomatik xabar yuborish.
"""
import re
from datetime import datetime, timedelta
from extensions import db
from models.interaction import Lead
from telegram_poster import send_admin_alert

# @username oldida email belgilari turmasligi kerak — aks holda "ali@gmail.com"
# ichidagi "@gmail" kontakt deb topilib, soxta lead yaratilardi.
CONTACT_PATTERN = re.compile(
    r'(\+?998[0-9\s\-]{9,13}|\b9[0-9]{8}\b|(?<![A-Za-z0-9._%+-])@[a-zA-Z0-9_]{4,})'
)

# Bir xil kontakt shu oyna ichida qayta kelsa, yangi Lead ochilmaydi.
DUPLICATE_WINDOW_MINUTES = 60


def extract_contact(text):
    """Matndan telefon raqam yoki Telegram username ajratib olish"""
    if not text:
        return None
    match = CONTACT_PATTERN.search(text)
    return match.group(0).strip() if match else None


def normalize_contact(contact):
    """Taqqoslash uchun kontaktni bir ko'rinishga keltirish."""
    if not contact:
        return ''
    return re.sub(r"[\s()\-]", "", str(contact)).strip().lower()


def is_duplicate_contact(contact, window_minutes=DUPLICATE_WINDOW_MINUTES):
    """Shu kontakt yaqinda allaqachon yozilganmi?

    Har bir chat xabari uchun yangi Lead ochilishi bazani ham, adminning
    Telegram kanalini ham spam bilan to'ldirardi.
    """
    normalized = normalize_contact(contact)
    if not normalized:
        return False

    # created_at bazaning o'z soati bilan (server_default=now(), ya'ni UTC) yoziladi.
    # datetime.now() lokal vaqt bergani uchun taqqoslash noto'g'ri chiqardi —
    # shuning uchun "hozir" ni ham bazadan so'raymiz.
    try:
        db_now = db.session.query(db.func.now()).scalar()
    except Exception:
        db_now = None
    if not isinstance(db_now, datetime):
        db_now = datetime.utcnow()

    cutoff = db_now - timedelta(minutes=window_minutes)
    try:
        recent = Lead.query.filter(Lead.created_at >= cutoff).all()
    except Exception as exc:
        # Tekshiruv imkoni bo'lmasa lead yo'qolmasin — dublikat bo'lsa ham yoziladi.
        print(f"[crm] Dublikat tekshiruvi bajarilmadi: {exc}")
        return False

    return any(normalize_contact(row.contact) == normalized for row in recent)


def capture_lead_from_message(message_text, source="AI Chat Vidjet", default_name="AI Chat Mijoz"):
    """
    Xabardan kontaktni qidirib, topilsa bazaga Lead sifatida saqlash va Adminga alert yuborish.
    """
    contact = extract_contact(message_text)
    if not contact:
        return None

    if is_duplicate_contact(contact):
        print(f"[crm] Dublikat kontakt e'tiborsiz qoldirildi: {contact}")
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
        try:
            from services.meta_capi import track_meta_event
            track_meta_event(
                event_name="Lead",
                user_data={"phone": contact},
                custom_data={"source": source, "currency": "UZS", "value": 300000}
            )
        except Exception:
            pass
        print(f"[crm] Lead muvaffaqiyatli saqlandi va adminga yuborildi: {contact}")
        return new_lead
    except Exception as exc:
        db.session.rollback()
        print(f"[crm] Lead saqlashda xatolik: {exc}")
        return None
