"""
TrendoAI Web / Public sahifalar va SEO marshrutlari.
"""
from flask import Blueprint
from utils.logger import setup_logger
logger = setup_logger("_blueprint")


web_bp = Blueprint('web', __name__)
