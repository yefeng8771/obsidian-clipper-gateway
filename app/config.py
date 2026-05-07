import os
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    # ---- Server ----
    'host': os.getenv('HOST', '0.0.0.0'),
    'port': int(os.getenv('PORT', 8000)),

    # ---- GitHub Pages（保留：浏览器扩展剪藏的 HTML 快照走这条） ----
    'github_repo':              os.getenv('GITHUB_REPO', ''),
    'github_token':             os.getenv('GITHUB_TOKEN', ''),
    'github_pages_domain':      os.getenv('GITHUB_PAGES_DOMAIN', ''),
    'github_pages_max_retries': int(os.getenv('GITHUB_PAGES_MAX_RETRIES', 60)),

    # ---- Telegram 通知 ----
    'telegram_token':   os.getenv('TELEGRAM_TOKEN', ''),
    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),

    # ---- OpenAI（生成摘要 + 标签） ----
    'openai_api_key':     os.getenv('OPENAI_API_KEY', ''),
    'openai_base_url':    os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
    'openai_model':       os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
    'openai_max_retries': int(os.getenv('OPENAI_MAX_RETRIES', 3)),

    # ---- fast-note-sync (Obsidian vault 后端) ----
    # 优先使用对外域名 FNS_HOST，未设置时回退到内部地址 FNS_URL
    'fns_url':    os.getenv('FNS_HOST') or os.getenv('FNS_URL', 'http://fast-note-sync-service:9000'),
    'fns_token':  os.getenv('FNS_TOKEN', ''),
    'fns_vault':  os.getenv('FNS_VAULT', 'Inbox'),
    'fns_folder': os.getenv('FNS_FOLDER', 'Clippings'),

    # ---- App ----
    'api_key':                  os.getenv('API_KEY', ''),
    'max_file_size':            int(os.getenv('MAX_FILE_SIZE', 30 * 1024 * 1024)),
    'allowed_extensions':       os.getenv('ALLOWED_EXTENSIONS', '.html,.htm').split(','),
}
