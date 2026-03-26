from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template, abort
from models import db, Juristic, Room, Customer, RoomResident, Income, Record, ArHeader, RcHeader, JuristicAdminMapping

juristic_bp = Blueprint('juristic', __name__)

@juristic_bp.route('/select-juristic')
def select_juristic():
    if 'user_id' not in session: return redirect(url_for('auth.index'))
    user_id = session.get('user_id')
    user = Customer.query.get(user_id)
    if not user: return redirect(url_for('auth.logout'))
    
    # ดึงโครงการที่ User คนนี้มีสิทธิ์ (จากตารางกลาง JuristicAdminMapping)
    mappings = JuristicAdminMapping.query.filter_by(customer_id=user_id).all()
    juristics = [m.juristic_info for m in mappings]
    
    # ถ้ายังไม่มีในตารางกลาง ให้ลองใช้ juristic_id หลักจากตาราง Customer (เพื่อรองรับข้อมูลเก่า)
    if not juristics and user.juristic_id:
        juristics = [Juristic.query.get(user.juristic_id)]
        
    return render_template('select_juristic.html', juristics=juristics)

@juristic_bp.route('/choose-project/<int:j_id>')
def choose_project(j_id):
    if 'user_id' not in session: return redirect(url_for('auth.index'))
    user_id = session.get('user_id')
    user = Customer.query.get(user_id)
    
    # ตรวจสอบสิทธิ์จากตารางกลาง
    mapping = JuristicAdminMapping.query.filter_by(customer_id=user_id, juristic_id=j_id).first()
    
    # ถ้าไม่มีในตารางกลาง ให้ลองเช็คจากคอลัมน์หลัก (เพื่อความยืดหยุ่น)
    if not mapping and user.juristic_id != j_id:
        abort(403) # Forbidden
        
    juristic = Juristic.query.get(j_id)
    if juristic:
        session['juristic_id'] = j_id
        session['juristic_name'] = juristic.name
        return redirect(url_for('juristic.dashboard'))
    abort(404)

@juristic_bp.route('/dashboard')
def dashboard():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('juristic.select_juristic'))
    
    juristic = Juristic.query.get(j_id)
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    if user_role == 'admin':
        rooms = Room.query.filter_by(juristic_id=j_id).all()
        customers = Customer.query.filter_by(juristic_id=j_id).all()
        incomes = Income.query.filter_by(juristic_id=j_id).all()
        records = Record.query.filter_by(juristic_id=j_id).all()
        ar_headers = ArHeader.query.filter_by(juristic_id=j_id).all()
        rc_headers = RcHeader.query.filter_by(juristic_id=j_id).all()
    else:
        rooms = db.session.query(Room).join(RoomResident).filter(RoomResident.customer_id == user_id, RoomResident.active == True).all()
        customers = [Customer.query.get(user_id)]
        incomes = [] 
        records = [] 
        room_ids = [r.id for r in rooms]
        ar_headers = ArHeader.query.filter(ArHeader.room_id.in_(room_ids)).all()
        rc_headers = RcHeader.query.filter(RcHeader.customer_id == user_id).all()

    return render_template('dashboard.html', 
                           juristic=juristic, 
                           rooms=rooms, 
                           customers=customers,
                           incomes=incomes if user_role == 'admin' else [],
                           records=records if user_role == 'admin' else [],
                           ar_headers=ar_headers,
                           rc_headers=rc_headers)
