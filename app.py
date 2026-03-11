import os
from flask import Flask, render_template, session, abort, request, redirect, url_for, jsonify
from models import db, Room, Juristic
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///juristic.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')

db.init_app(app)

# --- ROUTES ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('select_juristic'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    # ตัวอย่างการเช็ค Login (ในระบบจริงควรเช็คจาก DB และใช้ Password Hash)
    if email == "admin@mail.com" and password == "1234":
        session['user_id'] = 1
        return jsonify({"success": True, "redirect": url_for('select_juristic')})
    
    return jsonify({"success": False, "message": "อีเมลหรือรหัสผ่านไม่ถูกต้อง"})

@app.route('/register', methods=['POST'])
def register():
    try:
        juristic_name = request.form.get('juristic_name')
        if not juristic_name:
            return jsonify({"success": False, "message": "กรุณากรอกชื่อนิติบุคคล"})

        new_juristic = Juristic(name=juristic_name)
        db.session.add(new_juristic)
        db.session.commit()
        
        return jsonify({"success": True, "message": f"เปิดโครงการ {juristic_name} เรียบร้อยแล้ว"})

    except IntegrityError:
        db.session.rollback() # ต้อง Rollback เมื่อเกิด Error เพื่อล้างสถานะ Session
        return jsonify({"success": False, "message": "ชื่อนิติบุคคลนี้มีอยู่ในระบบแล้ว กรุณาใช้ชื่ออื่น"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล"})

@app.route('/select-juristic')
def select_juristic():
    if 'user_id' not in session: return redirect(url_for('index'))
    juristics = Juristic.query.all()
    return render_template('select_juristic.html', juristics=juristics)

@app.route('/choose-project/<int:j_id>')
def choose_project(j_id):
    juristic = Juristic.query.get(j_id)
    if juristic:
        session['juristic_id'] = j_id
        session['juristic_name'] = juristic.name
        return redirect(url_for('dashboard'))
    abort(404)

@app.route('/dashboard')
def dashboard():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('select_juristic'))
    rooms = Room.query.filter_by(juristic_id=j_id).all()
    return render_template('dashboard.html', rooms=rooms)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5005, debug=True)