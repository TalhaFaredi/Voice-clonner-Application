import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND / '.env')


class Settings:
    APP_ENV = os.getenv('APP_ENV', 'development')
    STORAGE = BACKEND / 'storage'
    DATABASE = STORAGE / 'saas.sqlite3'
    MAX_CONTENT_LENGTH = 21 * 1024 * 1024
    PUBLIC_URL = os.getenv('PUBLIC_URL', 'http://localhost:5173').rstrip('/')
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
    SESSION_DAYS = int(os.getenv('SESSION_DAYS', '7'))
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    CLONE_MODEL = os.getenv('CLONE_MODEL', 'Qwen/Qwen3-TTS-12Hz-1.7B-Base')
    PRESET_MODEL = os.getenv('PRESET_MODEL', 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice')
    TTS_DEVICE = os.getenv('TTS_DEVICE', 'cuda:0')
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_FROM = os.getenv('SMTP_FROM', 'accounts@example.com')
