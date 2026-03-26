from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, limiter
from models import Customer, Juristic, RoomResident, Room, JuristicAdminMapping
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('juristic.select_juristic'))
    return render_template('index.html')

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
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
@limiter.limit("3 per hour")
def register():
    """ลงทะเบียนเฉพาะบัญชีผู้ใช้งาน (User Account)"""
    try:
        name = request.form.get('name', 'ผู้ดูแลระบบ')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return jsonify({"success": False, "message": "กรุณากรอกข้อมูลให้ครบถ้วน"})

        # สร้าง User เปล่าๆ (ยังไม่ผูกกับนิติในขั้นตอนนี้)
        admin_user = Customer(
            name=name,
            email=email,
            username=email,
            password_hash=generate_password_hash(password),
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()
        
        return jsonify({"success": True, "message": "สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบเพื่อเริ่มสร้างนิติบุคคลของคุณ"})

    except IntegrityError:
        db.session.rollback()
        return jsonify({"success": False, "message": "อีเมลนี้มีอยู่ในระบบแล้ว"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"})

@auth_bp.route('/create-juristic', methods=['POST'])
@limiter.limit("5 per hour")
def create_juristic():
    """สร้างโครงการใหม่ (แรกฟรี / ตัวต่อไปจ่ายเงิน)"""
    if 'user_id' not in session: 
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบก่อน"})
    
    current_user_id = session.get('user_id')
    user = Customer.query.get(current_user_id)
    if not user or user.role != 'admin':
        return jsonify({"success": False, "message": "สิทธิ์ไม่เพียงพอ"})

    juristic_name = request.form.get('juristic_name')
    if not juristic_name:
        return jsonify({"success": False, "message": "กรุณาระบุชื่อนิติบุคคล"})

    # ตรวจสอบจำนวนนิติที่มีอยู่
    mapping_count = JuristicAdminMapping.query.filter_by(customer_id=user.id).count()
    
    # เงื่อนไข: ถ้ามีอยู่แล้ว 1 ตัว ต้องมีระบบชำระเงินก่อน (ในที่นี้เราจำลองว่าต้องจ่ายเงิน)
    if mapping_count >= 1:
        # TODO: ระบบชำระเงิน
        # return jsonify({"success": False, "message": "คุณได้ใช้โควตาโครงการฟรีครบแล้ว กรุณาชำระเงินเพื่อเปิดโครงการเพิ่ม"})
        # สำหรับช่วงทดสอบ ให้ผ่านไปก่อนแต่กำหนดสถานะเป็น 'pending_payment'
        status = 'pending_payment'
    else:
        status = 'active'

    try:
        # สร้างนิติบุคคลใหม่ พร้อมอายุการใช้งาน 1 ปี
        new_juristic = Juristic(
            name=juristic_name,
            status=status,
            expiry_date=datetime.utcnow() + timedelta(days=365)
        )
        db.session.add(new_juristic)
        db.session.flush() 

        # ผูก User เข้ากับนิติใหม่
        mapping = JuristicAdminMapping(juristic_id=new_juristic.id, customer_id=user.id)
        db.session.add(mapping)
        
        # ถ้าเป็นนิติแรก ให้ตั้งเป็น Default juristic_id ในตาราง Customer ด้วย
        if not user.juristic_id:
            user.juristic_id = new_juristic.id

        db.session.commit()
        
        msg = f"สร้างโครงการ {juristic_name} เรียบร้อยแล้ว (ใช้งานได้ถึง {new_juristic.expiry_date.strftime('%d/%m/%Y')})"
        return jsonify({"success": True, "message": msg, "redirect": url_for('juristic.select_juristic')})

    except IntegrityError:
        db.session.rollback()
        return jsonify({"success": False, "message": "ชื่อนิติบุคคลนี้มีอยู่ในระบบแล้ว"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"เกิดข้อผิดพลาด: {str(e)}"})

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
