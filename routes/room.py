from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template, abort
from models import db, Room, Juristic, RoomResident, Customer

room_bp = Blueprint('room', __name__)

@room_bp.route('/rooms', methods=['GET'])
def list_rooms():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('juristic.select_juristic'))
    juristic = Juristic.query.get(j_id)
    rooms = Room.query.filter_by(juristic_id=j_id).order_by(Room.building, Room.floor, Room.room_no).all()
    
    types_query = db.session.query(Room.type).filter(Room.juristic_id == j_id, Room.type.isnot(None), Room.type != '').distinct().all()
    types_list = [t[0] for t in types_query if t[0]]
    
    # ดึงข้อมูลผู้อยู่อาศัยทั้งหมดเพื่อใช้ในหน้าเดียวกัน
    customers = Customer.query.filter_by(juristic_id=j_id).all()

    return render_template('rooms.html', rooms=rooms, juristic=juristic, types=types_list, customers=customers)

@room_bp.route('/room/add', methods=['POST'])
def add_room():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    room_no = request.form.get('room_no')
    building = request.form.get('building')
    floor = request.form.get('floor')
    type_ = request.form.get('type')
    status = request.form.get('status')
    sq_area = request.form.get('sq_area')
    ratio = request.form.get('ratio')
    
    if not room_no:
        return jsonify({"success": False, "message": "กรุณากรอกเลขห้อง"})
        
    existing_room = Room.query.filter_by(juristic_id=j_id, room_no=room_no).first()
    if existing_room:
        return jsonify({"success": False, "message": f"ห้องเลขที่ '{room_no}' มีอยู่ในระบบแล้ว"})
        
    try:
        new_room = Room(
            juristic_id=j_id, room_no=room_no, building=building, floor=floor, type=type_, status=status,
            sq_area=float(sq_area) if sq_area else 0.0,
            ratio=float(ratio) if ratio else 0.0
        )
        db.session.add(new_room)
        db.session.commit()
        return jsonify({"success": True, "message": "เพิ่มห้องสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@room_bp.route('/room/get/<int:room_id>')
def get_room(room_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    room = Room.query.filter_by(id=room_id, juristic_id=j_id).first()
    if not room: return jsonify({"success": False, "message": "ไม่พบห้องนี้"})
    return jsonify({
        "success": True,
        "room": {
            "id": room.id, "room_no": room.room_no, "building": room.building, "floor": room.floor,
            "type": room.type, "status": room.status, "sq_area": room.sq_area, "ratio": room.ratio
        }
    })

@room_bp.route('/room/delete/<int:room_id>', methods=['POST'])
def delete_room(room_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    room = Room.query.filter_by(id=room_id, juristic_id=j_id).first()
    if not room: return jsonify({"success": False, "message": "ไม่พบห้องนี้"})
    
    try:
        db.session.delete(room)
        db.session.commit()
        return jsonify({"success": True, "message": "ลบห้องสำเร็จ"})
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "เกิดข้อผิดพลาดในการลบ (อาจมีข้อมูลอ้างอิงอยู่)"})

@room_bp.route('/room/update/<int:room_id>', methods=['POST'])
def update_room(room_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    room = Room.query.filter_by(id=room_id, juristic_id=j_id).first()
    if not room: return jsonify({"success": False, "message": "ไม่พบห้องนี้"})
    
    room_no = request.form.get('room_no')
    building = request.form.get('building')
    floor = request.form.get('floor')
    type_ = request.form.get('type')
    status = request.form.get('status')
    sq_area = request.form.get('sq_area')
    ratio = request.form.get('ratio')
    
    if not room_no:
        return jsonify({"success": False, "message": "กรุณากรอกเลขห้อง"})
        
    existing_room = Room.query.filter_by(juristic_id=j_id, room_no=room_no).first()
    if existing_room and existing_room.id != room_id:
        return jsonify({"success": False, "message": f"ห้องเลขที่ '{room_no}' มีอยู่ในระบบแล้ว"})
        
    try:
        room.room_no = room_no
        room.building = building
        room.floor = floor
        room.type = type_
        room.status = status
        room.sq_area = float(sq_area) if sq_area else 0.0
        room.ratio = float(ratio) if ratio else 0.0
        db.session.commit()
        return jsonify({"success": True, "message": "อัปเดตห้องสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@room_bp.route('/room/get-customers', methods=['GET'])
def get_customers_json():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify([])
    customers = Customer.query.filter_by(juristic_id=j_id, active=True).all()
    # Return id, name, and email for the frontend select dropdown
    return jsonify([{"id": c.id, "name": c.name, "email": c.email} for c in customers])

@room_bp.route('/room/assign', methods=['POST'])
def assign_resident():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    room_id = request.form.get('room_id')
    customer_id = request.form.get('customer_id')
    res_type = request.form.get('residence_type', 'tenant')
    
    if not room_id or not customer_id:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบ"})
        
    try:
        RoomResident.query.filter_by(room_id=room_id, active=True).update({"active": False, "end_date": db.func.current_date()})
        
        new_res = RoomResident(
            juristic_id=j_id, room_id=room_id, customer_id=customer_id, residence_type=res_type,
            start_date=db.func.current_date(), active=True
        )
        db.session.add(new_res)
        
        room = Room.query.get(room_id)
        if room:
            room.status = 'มีผู้อยู่อาศัย'
            
        db.session.commit()
        return jsonify({"success": True, "message": "มอบหมายผู้อยู่อาศัยสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@room_bp.route('/room/history/<int:r_id>', methods=['GET'])
def get_room_history(r_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    history = RoomResident.query.filter_by(room_id=r_id).order_by(RoomResident.id.desc()).all()
    data = []
    for h in history:
        data.append({
            "name": h.customer.name if h.customer else 'N/A',
            "type": h.residence_type,
            "in": str(h.start_date) if h.start_date else '-',
            "out": str(h.end_date) if h.end_date else '-',
            "active": h.active
        })
    return jsonify({"success": True, "history": data})
