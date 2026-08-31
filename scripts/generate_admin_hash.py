"""Admin paroli uchun xavfsiz hash yaratadi.

Foydalanish:
    python scripts/generate_admin_hash.py

Chiqqan qiymatni Render'da ADMIN_PASSWORD_HASH sifatida qo'ying va
ochiq ADMIN_PASSWORD o'zgaruvchisini o'chiring.
"""
import getpass
import sys
from utils.logger import setup_logger
logger = setup_logger("generate_admin_hash")


from werkzeug.security import generate_password_hash


def main():
    password = getpass.getpass("Yangi admin paroli: ")
    if len(password) < 12:
        logger.info("Xato: parol kamida 12 ta belgidan iborat bo'lsin.", file=sys.stderr)
        return 1

    if password != getpass.getpass("Parolni takrorlang: "):
        logger.info("Xato: parollar mos kelmadi.", file=sys.stderr)
        return 1

    logger.info("\nADMIN_PASSWORD_HASH=" + generate_password_hash(password))
    logger.info("\nShu qatorni Render environment'iga qo'shing va ADMIN_PASSWORD ni o'chiring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
