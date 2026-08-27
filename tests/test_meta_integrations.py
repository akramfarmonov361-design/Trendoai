"""
Meta Ads, Facebook Pixel, Conversions API (CAPI) va XML Feed integratsiya testlari.
"""
from app import app
from config import FACEBOOK_PIXEL_ID, FB_CONVERSIONS_API_TOKEN
from services.meta_capi import _hash_field, track_meta_event

def test_meta_config():
    assert FACEBOOK_PIXEL_ID == "1192818429057379"
    assert FB_CONVERSIONS_API_TOKEN.startswith("EAA")

def test_meta_capi_hashing():
    assert _hash_field("+998901234567") is not None
    assert _hash_field("test@trendoai.uz") is not None
    assert _hash_field(None) is None

def test_meta_capi_track_execution():
    with app.test_request_context('/order'):
        track_meta_event("Lead", user_data={"phone": "+998901234567", "email": "test@trendoai.uz"})

def test_facebook_catalog_feed():
    with app.test_client() as client:
        response = client.get('/facebook-catalog.xml')
        assert response.status_code == 200
        assert 'xml' in response.mimetype
        assert b'<rss' in response.data
        assert b'<channel>' in response.data
        assert b'Trendo' in response.data
        assert b'<g:id>' in response.data

def test_facebook_feed_alias():
    with app.test_client() as client:
        response = client.get('/facebook-feed.xml')
        assert response.status_code == 200
        assert 'xml' in response.mimetype