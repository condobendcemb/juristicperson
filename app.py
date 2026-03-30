import os
from flask import Flask, session
from flask_talisman import Talisman
from extensions import db, csrf, limiter
from models import db as _db # Keep it for db.init_app, but we'll use extensions.db

# Import Blueprints
from routes.auth import auth_bp
from routes.juristic import juristic_bp
from routes.room import room_bp
from routes.income import income_bp
from routes.record import record_bp
from routes.billing import billing_bp
from routes.customer import customer_bp

app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///juristic.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')

# --- Security Setup ---
# 1. CSRF Protection
csrf.init_app(app)

# 2. Rate Limiting (Brute Force Protection)
limiter.init_app(app)

# 3. Security Headers & CSP
csp = {
    'default-src': '\'self\'',
    'base-uri': '\'self\'',
    'object-src': '\'none\'',
    'frame-ancestors': '\'none\'',
    'form-action': '\'self\'',
    'script-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'https://*.googleapis.com',
        'https://*.gstatic.com',
        'https://cdn.jsdelivr.net'  # สำหรับ SweetAlert2 และ Bootstrap
    ],
    'style-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'https://fonts.googleapis.com',
        'https://cdn.jsdelivr.net',
        'https://cdnjs.cloudflare.com'
    ],
    'img-src': ['\'self\'', 'data:', 'https:'],
    'font-src': ['\'self\'', 'https://fonts.gstatic.com', 'https://cdnjs.cloudflare.com'],
    'connect-src': '\'self\''
}

talisman = Talisman(
    app,
    content_security_policy=csp,
    force_https=False, # เปลี่ยนเป็น True เมื่อรันบน Production (Render จัดการ HTTPS ให้แล้ว)
    strict_transport_security=True,
    strict_transport_security_max_age=31536000,
    frame_options='DENY',
    session_cookie_secure=False, # เปลี่ยนเป็น True เมื่อใช้ HTTPS
    session_cookie_http_only=True
)

db.init_app(app)

# --- Error Handlers ---
@app.errorhandler(429)
def ratelimit_handler(e):
    """คืน JSON เสมอเมื่อโดน Rate Limit เพื่อไม่ให้ Frontend แตก"""
    from flask import jsonify
    return jsonify({
        "success": False,
        "message": f"คำขอมากเกินไป กรุณารอสักครู่แล้วลองใหม่ ({e.description})"
    }), 429

@app.errorhandler(400)
def bad_request_handler(e):
    from flask import jsonify, request as req
    if req.accept_mimetypes.accept_json and not req.accept_mimetypes.accept_html:
        return jsonify({"success": False, "message": str(e)}), 400
    return e

# --- Jinja Filters ---
def format_thai_baht(number):
    if number is None: return ""
    def _read_segment(num_str):
        units = ['', 'สิบ', 'ร้อย', 'พัน', 'หมื่น', 'แสน', 'ล้าน']
        digits = ['ศูนย์', 'หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า']
        res = ''
        length = len(num_str)
        for i in range(length):
            digit = int(num_str[i])
            if digit != 0:
                if i == length - 1 and digit == 1 and length > 1:
                    res += 'เอ็ด'
                elif i == length - 2 and digit == 2:
                    res += 'ยี่สิบ'
                elif i == length - 2 and digit == 1:
                    res += 'สิบ'
                else:
                    res += digits[digit] + units[length - i - 1]
            elif i == length - 1 and digit == 0 and length == 1:
                 res += digits[digit]
        return res

    s_num = f"{number:.2f}"
    baht_part, satang_part = s_num.split('.')
    
    res = ''
    if len(baht_part) > 6:
        m_part = baht_part[0 : len(baht_part)-6]
        l_part = baht_part[len(baht_part)-6 : ]
        res += _read_segment(m_part) + 'ล้าน'
        res += _read_segment(l_part)
    else:
        res += _read_segment(baht_part)
    
    if res: res += 'บาท'
    if satang_part == '00':
        res += 'ถ้วน'
    else:
        res += _read_segment(satang_part) + 'สตางค์'
    return res

app.jinja_env.filters['format_thai_baht'] = format_thai_baht

# Jinja Filter: Format period to Thai
def format_period(period_str):
    """Convert '2024-01' to 'ปี 2024 เดือน มกราคม'"""
    if not period_str:
        return ''
    try:
        parts = str(period_str).split('-')
        if len(parts) == 2:
            year, month = int(parts[0]), int(parts[1])
            months_th = ['', 'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
                        'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
            month_name = months_th[month] if 1 <= month <= 12 else str(month)
            return f'ปี {year} เดือน {month_name}'
    except:
        pass
    return period_str

app.jinja_env.filters['format_period'] = format_period

# Jinja Filter: Check if current endpoint is active
def is_active_menu(endpoint_name):
    """ตรวจสอบว่า endpoint ปัจจุบันตรงกับชื่อ endpoint ที่ระบุ"""
    from flask import request
    current_endpoint = request.endpoint
    if not current_endpoint:
        return False
    # เทียบ endpoint ด้านหน้าจุด (เช่น 'juristic.dashboard' -> 'juristic')
    return current_endpoint.startswith(endpoint_name)

app.jinja_env.filters['is_active_menu'] = is_active_menu

# --- Register Blueprints ---
app.register_blueprint(auth_bp)
app.register_blueprint(juristic_bp)
app.register_blueprint(room_bp)
app.register_blueprint(income_bp)
app.register_blueprint(record_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(customer_bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    # Run on 5000 inside container, mapped to 5010 on host
    app.run(host='0.0.0.0', port=5000, debug=True)