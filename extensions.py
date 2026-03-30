import os
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()

# บน Render (multi-worker) ให้ตั้ง RATELIMIT_STORAGE_URL=memory:// ใน env
# หรือใช้ Redis: redis://...  เพื่อให้ทุก worker ใช้ counter ร่วมกัน
_storage = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")

limiter = Limiter(
    get_remote_address,
    default_limits=["500 per day", "100 per hour"],
    storage_uri=_storage,
    strategy="fixed-window",        # ประหยัด memory กว่า moving-window
    swallow_errors=True,            # ถ้า storage พัง อย่าให้ app พัง
)
