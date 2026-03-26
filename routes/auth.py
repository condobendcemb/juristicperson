from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Customer, Juristic, RoomResident, Room
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('juristic.select_juristic'))
    return render_template('index.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    user = Customer.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password_hash, password):
        if not user.active:
            return jsonify({"success": False, "message": "บัญชีของคุณถูกระงับการใช้งาน กรุณาติดต่อนิติบุคคล"})
            
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_role'] = user.role
        
        if user.role == 'admin':
            return jsonify({"success": True, "redirect": url_for('juristic.select_juristic')})
        else:
            session['juristic_id'] = user.juristic_id
            resident = RoomResident.query.filter_by(customer_id=user.id, active=True).first()
            if resident:
                session['room_id'] = resident.room_id
            return jsonify({"success": True, "redirect": url_for('juristic.dashboard')})
            
    return jsonify({"success": False, "message": "อีเมลหรือรหัสผ่านไม่ถูกต้อง"})

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        juristic_name = request.form.get('juristic_name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not juristic_name or not email or not password:
            return jsonify({"success": False, "message": "กรุณากรอกข้อมูลให้ครบถ้วน"})

        new_juristic = Juristic(name=juristic_name)
        db.session.add(new_juristic)
        db.session.flush() 
        
        admin_user = Customer(
            juristic_id=new_juristic.id,
            name="ผู้ดูแลระบบ",
            email=email,
            username=email,
            password_hash=generate_password_hash(password),
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()
        
        return jsonify({"success": True, "message": f"เปิดโครงการ {juristic_name} และสร้างบัญชีผู้ดูแลเรียบร้อยแล้ว"})

    except IntegrityError:
        db.session.rollback()
        return jsonify({"success": False, "message": "อีเมลหรือชื่อนิติบุคคลนี้มีอยู่ในระบบแล้ว"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"})

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))
