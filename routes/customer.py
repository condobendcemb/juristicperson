from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template
from werkzeug.security import generate_password_hash
from models import db, Customer, Juristic

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/customer', methods=['GET'])
def index():
    return redirect(url_for('room.list_rooms'))

@customer_bp.route('/customer/add', methods=['POST'])
def add_customer():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    phone = request.form.get('phone')
    role = request.form.get('role', 'user')
    idcard = request.form.get('idcard')
    address = request.form.get('address')
    
    if not name or not email:
        return jsonify({"success": False, "message": "กรุณากรอกชื่อและอีเมล"})
        
    try:
        existing = Customer.query.filter_by(email=email).first()
        if existing:
            return jsonify({"success": False, "message": "อีเมลนี้ถูกใช้งานแล้ว"})
            
        new_customer = Customer(
            juristic_id=j_id, name=name, email=email, username=email,
            password_hash=generate_password_hash(password) if password else None,
            role=role, phone=phone, idcard=idcard, address=address
        )
        db.session.add(new_customer)
        db.session.commit()
        return jsonify({"success": True, "message": "เพิ่มสมาชิกสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@customer_bp.route('/customer/get/<int:c_id>')
def get_customer(c_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    cust = Customer.query.filter_by(id=c_id, juristic_id=j_id).first()
    if not cust: return jsonify({"success": False, "message": "ไม่พบข้อมูลสมาชิก"})
    
    return jsonify({
        "success": True,
        "customer": {
            "id": cust.id, "name": cust.name, "email": cust.email, "phone": cust.phone,
            "role": cust.role, "idcard": cust.idcard, "address": cust.address, "active": cust.active
        }
    })

@customer_bp.route('/customer/update/<int:c_id>', methods=['POST'])
def update_customer(c_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    cust = Customer.query.filter_by(id=c_id, juristic_id=j_id).first()
    if not cust: return jsonify({"success": False, "message": "ไม่พบข้อมูลสมาชิก"})
    
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    phone = request.form.get('phone')
    role = request.form.get('role')
    idcard = request.form.get('idcard')
    address = request.form.get('address')
    active = request.form.get('active') == 'on'
    
    if not name or not email:
        return jsonify({"success": False, "message": "กรุณากรอกชื่อและอีเมล"})
        
    try:
        existing = Customer.query.filter(Customer.email == email, Customer.id != c_id).first()
        if existing:
            return jsonify({"success": False, "message": "อีเมลนี้ถูกใช้งานโดยสมาชิกท่านอื่นแล้ว"})
            
        cust.name = name
        cust.email = email
        cust.username = email
        cust.phone = phone
        cust.role = role
        cust.idcard = idcard
        cust.address = address
        cust.active = active
        
        if password:
            cust.password_hash = generate_password_hash(password)
            
        db.session.commit()
        return jsonify({"success": True, "message": "อัปเดตข้อมูลสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@customer_bp.route('/customer/delete/<int:c_id>', methods=['POST'])
def delete_customer(c_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    cust = Customer.query.filter_by(id=c_id, juristic_id=j_id).first()
    if not cust: return jsonify({"success": False, "message": "ไม่พบข้อมูลสมาชิก"})
    
    if cust.role == 'admin' and cust.email == session.get('user_name'):
         return jsonify({"success": False, "message": "ไม่สามารถลบตัวเองได้"})

    try:
        db.session.delete(cust)
        db.session.commit()
        return jsonify({"success": True, "message": "ลบข้อมูลสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "ลบไม่สำเร็จ (อาจมีข้อมูลอ้างอิงอยู่)"})
