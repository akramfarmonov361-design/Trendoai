"""
Meta Conversions API (CAPI) integratsiyasi.
Server orqali xavfsiz va tezkor voqealarni (Lead, Purchase, PageView, Contact) Meta'ga uzatish.
"""
import hashlib
import time
import requests
import threading
from flask import request
from config import FACEBOOK_PIXEL_ID, FB_CONVERSIONS_API_TOKEN

def _hash_field(val):
    if not val:
        return None
    return hashlib.sha256(str(val).strip().lower().encode('utf-8')).hexdigest()

def track_meta_event(event_name, user_data=None, custom_data=None, event_source_url=None):
    """
    Meta Conversions API ga fon rejimida (async thread) event yuborish.
    Sayt tezligiga 0ms ta'sir qiladi.
    """
    if not FB_CONVERSIONS_API_TOKEN or not FACEBOOK_PIXEL_ID:
        return

    client_ip = None
    client_ua = None
    try:
        if request:
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if client_ip and ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()
            client_ua = request.headers.get('User-Agent')
    except Exception:
        pass

    def _send():
        try:
            url = f"https://graph.facebook.com/v19.0/{FACEBOOK_PIXEL_ID}/events"
            
            payload_user = {
                "client_ip_address": client_ip,
                "client_user_agent": client_ua,
            }
            
            if user_data:
                if 'phone' in user_data and user_data['phone']:
                    clean_phone = ''.join(c for c in str(user_data['phone']) if c.isdigit())
                    payload_user['ph'] = [_hash_field(clean_phone)]
                if 'email' in user_data and user_data['email']:
                    payload_user['em'] = [_hash_field(user_data['email'])]
                if 'name' in user_data and user_data['name']:
                    payload_user['fn'] = [_hash_field(user_data['name'])]

            event_payload = {
                "event_name": event_name,
                "event_time": int(time.time()),
                "action_source": "website",
                "event_source_url": event_source_url or "https://trendoai.uz",
                "user_data": payload_user,
            }
            
            if custom_data:
                event_payload["custom_data"] = custom_data

            body = {
                "data": [event_payload],
                "access_token": FB_CONVERSIONS_API_TOKEN
            }
            
            requests.post(url, json=body, timeout=5)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()