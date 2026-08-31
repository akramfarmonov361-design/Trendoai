# Yengil vaznli Python 3.11.9 ishlatamiz
FROM python:3.11.9-slim

# Muhit o'zgaruvchilari
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Serverdagi ishchi papka
WORKDIR /app

# Kutubxonalarni yig'ish (kesh uchun alohida)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Qolgan barcha kodlarni nusxalash
COPY . /app/

# Portfolio rasmlari va loglar kabi ma'lumotlar saqlanishi kerak bo'lgan papkalarni yaratish
RUN mkdir -p /app/static/uploads && mkdir -p /app/logs

# Ochiq bo'ladigan port
EXPOSE 5000

# Gunicorn orqali ilovani ishga tushirish (2 ta ishchi jarayon (worker) yetarli)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:create_app()"]
