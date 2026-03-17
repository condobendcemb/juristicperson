import os
import datetime
from flask import Flask, render_template, session, abort, request, redirect, url_for, jsonify
from models import db, Room, Juristic, Customer, RoomResident, Income, Record, ArHeader, RcHeader, ArDetail, RcDetail
from sqlalchemy import or_, and_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///juristic.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-123')

db.init_app(app)

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
    # จัดการล้าน (Millions)
    if len(baht_part) > 6:
        # ใช้ integer indexing แทน slicing เพื่อลดโอกาส lint error (หรือสกัดส่วนออกมาให้ชัดเจน)
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
    
    # ค้นหา Customer จาก email (ซึ่งใช้เป็น username ในที่นี้)
    user = Customer.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password_hash, password):
        if not user.active:
            return jsonify({"success": False, "message": "บัญชีของคุณถูกระงับการใช้งาน กรุณาติดต่อนิติบุคคล"})
            
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_role'] = user.role
        
        # ถ้าเป็น admin อาจจะข้ามไปหน้าเลือกนิติ แต่ถ้าเป็น user ควรจะลัดไปหา juristic_id ของตัวเองเลย
        if user.role == 'admin':
            return jsonify({"success": True, "redirect": url_for('select_juristic')})
        else:
            session['juristic_id'] = user.juristic_id
            # หาห้องที่เขาสังกัดอยู่ (RoomResident)
            resident = RoomResident.query.filter_by(customer_id=user.id, active=True).first()
            if resident:
                session['room_id'] = resident.room_id
            return jsonify({"success": True, "redirect": url_for('dashboard')})
            
    return jsonify({"success": False, "message": "อีเมลหรือรหัสผ่านไม่ถูกต้อง"})

@app.route('/register', methods=['POST'])
def register():
    try:
        juristic_name = request.form.get('juristic_name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not juristic_name or not email or not password:
            return jsonify({"success": False, "message": "กรุณากรอกข้อมูลให้ครบถ้วน"})

        # 1. สร้างนิติบุคคลใหม่
        new_juristic = Juristic(name=juristic_name)
        db.session.add(new_juristic)
        db.session.flush() # เพื่อให้ได้ ID ของ Juristic มาก่อน commit
        
        # 2. สร้าง User Admin สำหรับนิตินี้ (อ้างอิงจาก Customer table)
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
    
    juristic = Juristic.query.get(j_id)
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    # ดึงข้อมูลสรุป
    if user_role == 'admin':
        rooms = Room.query.filter_by(juristic_id=j_id).all()
        customers = Customer.query.filter_by(juristic_id=j_id).all()
        # สำหรับโมเดลที่ยังไม่ได้สร้างหน้าจัดการ แต่มีใน Model แล้ว
        from models import Income, Record, ArHeader, RcHeader
        incomes = Income.query.filter_by(juristic_id=j_id).all()
        records = Record.query.filter_by(juristic_id=j_id).all()
        ar_headers = ArHeader.query.filter_by(juristic_id=j_id).all()
        rc_headers = RcHeader.query.filter_by(juristic_id=j_id).all()
    else:
        # ถ้าเป็น User ทั่วไป เห็นเฉพาะข้อมูลตัวเอง
        rooms = db.session.query(Room).join(RoomResident).filter(RoomResident.customer_id == user_id, RoomResident.active == True).all()
        customers = [Customer.query.get(user_id)]
        incomes = [] # ตามความเหมาะสม
        records = [] # กรองตาม room_id ของเขา
        room_ids = [r.id for r in rooms]
        from models import ArHeader, RcHeader
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

@app.route('/rooms', methods=['GET'])
def list_rooms():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('select_juristic'))
    juristic = Juristic.query.get(j_id)
    rooms = Room.query.filter_by(juristic_id=j_id).order_by(Room.building, Room.floor, Room.room_no).all()
    
    # ดึงรายชื่อประเภทห้องทั้งหมดที่ไม่ซ้ำกันของนิตินี้
    types_query = db.session.query(Room.type).filter(Room.juristic_id == j_id, Room.type.isnot(None), Room.type != '').distinct().all()
    types_list = [t[0] for t in types_query if t[0]]

    return render_template('rooms.html', rooms=rooms, juristic=juristic, types=types_list)

@app.route('/room/add', methods=['POST'])
def add_room():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    room_no = request.form.get('room_no')
    building = request.form.get('building')
    floor = request.form.get('floor')
    type = request.form.get('type')
    status = request.form.get('status')
    sq_area = request.form.get('sq_area')
    ratio = request.form.get('ratio')
    
    if not room_no:
        return jsonify({"success": False, "message": "กรุณากรอกเลขห้อง"})
        
    # เช็คว่ามีเลขห้องนี้ในนิติบุคคลนี้หรือยัง
    existing_room = Room.query.filter_by(juristic_id=j_id, room_no=room_no).first()
    if existing_room:
        return jsonify({"success": False, "message": f"ห้องเลขที่ '{room_no}' มีอยู่ในระบบแล้ว"})
        
    try:
        new_room = Room(
            juristic_id=j_id, 
            room_no=room_no, 
            building=building, 
            floor=floor, 
            type=type, 
            status=status,
            sq_area=float(sq_area) if sq_area else 0.0,
            ratio=float(ratio) if ratio else 0.0
        )
        db.session.add(new_room)
        db.session.commit()
        return jsonify({"success": True, "message": "เพิ่มห้องสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@app.route('/room/get/<int:room_id>')
def get_room(room_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    room = Room.query.filter_by(id=room_id, juristic_id=j_id).first()
    if not room: return jsonify({"success": False, "message": "ไม่พบห้องนี้"})
    return jsonify({
        "success": True,
        "room": {
            "id": room.id,
            "room_no": room.room_no,
            "building": room.building,
            "floor": room.floor,
            "type": room.type,
            "status": room.status,
            "sq_area": room.sq_area,
            "ratio": room.ratio
        }
    })

@app.route('/room/delete/<int:room_id>', methods=['POST'])
def delete_room(room_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    room = Room.query.filter_by(id=room_id, juristic_id=j_id).first()
    if not room: return jsonify({"success": False, "message": "ไม่พบห้องนี้"})
    
    try:
        db.session.delete(room)
        db.session.commit()
        return jsonify({"success": True, "message": "ลบห้องสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "เกิดข้อผิดพลาดในการลบ (อาจมีข้อมูลอ้างอิงอยู่)"})

@app.route('/room/update/<int:room_id>', methods=['POST'])
def update_room(room_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    room = Room.query.filter_by(id=room_id, juristic_id=j_id).first()
    if not room: return jsonify({"success": False, "message": "ไม่พบห้องนี้"})
    
    room_no = request.form.get('room_no')
    building = request.form.get('building')
    floor = request.form.get('floor')
    type = request.form.get('type')
    status = request.form.get('status')
    sq_area = request.form.get('sq_area')
    ratio = request.form.get('ratio')
    
    if not room_no:
        return jsonify({"success": False, "message": "กรุณากรอกเลขห้อง"})
        
    # เช็คว่ามีเลขห้องนี้ในนิติบุคคลนี้หรือยัง
    existing_room = Room.query.filter_by(juristic_id=j_id, room_no=room_no).first()
    if existing_room and existing_room.id != room_id:
        return jsonify({"success": False, "message": f"ห้องเลขที่ '{room_no}' มีอยู่ในระบบแล้ว"})
        
    try:
        room.room_no = room_no
        room.building = building
        room.floor = floor
        room.type = type
        room.status = status
        room.sq_area = float(sq_area) if sq_area else 0.0
        room.ratio = float(ratio) if ratio else 0.0
        db.session.commit()
        return jsonify({"success": True, "message": "อัปเดตห้องสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})


@app.route('/income')
def income():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('select_juristic'))
    juristic = Juristic.query.get(j_id)
    incomes = Income.query.filter_by(juristic_id=j_id).all()
    return render_template('income.html', incomes=incomes, juristic=juristic)

@app.route('/income/add', methods=['POST'])
def add_income():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    name = request.form.get('name')
    rate = request.form.get('rate')
    condition = request.form.get('condition')
    penalty = request.form.get('penalty')
    is_vat = request.form.get('is_vat') == 'on'
    
    if not name:
        return jsonify({"success": False, "message": "กรุณากรอกชื่อรายการรายได้"})
        
    try:
        new_inc = Income(
            juristic_id=j_id,
            name=name,
            rate=float(rate) if rate else 0.0,
            condition=condition,
            penalty=float(penalty) if penalty else 0.0,
            is_vat=is_vat
        )
        db.session.add(new_inc)
        db.session.commit()
        return jsonify({"success": True, "message": "เพิ่มรายการรายได้สำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@app.route('/income/get/<int:i_id>')
def get_income(i_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    inc = Income.query.filter_by(id=i_id, juristic_id=j_id).first()
    if not inc: return jsonify({"success": False, "message": "ไม่พบข้อมูล"})
    return jsonify({
        "success": True,
        "income": {
            "id": inc.id,
            "name": inc.name,
            "rate": inc.rate,
            "condition": inc.condition,
            "penalty": inc.penalty,
            "is_vat": inc.is_vat,
            "active": inc.active
        }
    })

@app.route('/income/update/<int:i_id>', methods=['POST'])
def update_income(i_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    inc = Income.query.filter_by(id=i_id, juristic_id=j_id).first()
    if not inc: return jsonify({"success": False, "message": "ไม่พบข้อมูล"})
    
    try:
        inc.name = request.form.get('name')
        inc.rate = float(request.form.get('rate') or 0.0)
        inc.condition = request.form.get('condition')
        inc.penalty = float(request.form.get('penalty') or 0.0)
        inc.is_vat = request.form.get('is_vat') == 'on'
        inc.active = request.form.get('active') == 'on'
        db.session.commit()
        return jsonify({"success": True, "message": "อัปเดตข้อมูลสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@app.route('/income/delete/<int:i_id>', methods=['POST'])
def delete_income(i_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    inc = Income.query.filter_by(id=i_id, juristic_id=j_id).first()
    if not inc: return jsonify({"success": False, "message": "ไม่พบข้อมูล"})
    try:
        db.session.delete(inc)
        db.session.commit()
        return jsonify({"success": True, "message": "ลบสำเร็จ"})
    except:
        db.session.rollback()
        return jsonify({"success": False, "message": "ลบไม่สำเร็จ (อาจมีข้อมูลอ้างอิงอยู่)"})

# --- Record Management (Periodic) ---

@app.route('/record')
def record():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('select_juristic'))
    juristic = Juristic.query.get(j_id)
    incomes = Income.query.filter_by(juristic_id=j_id, active=True).all()
    # ดึงรายงวดที่มีอยู่ (ยกตัวอย่าง ปีปัจจุบัน)
    import datetime
    now = datetime.datetime.now()
    periods = []
    for i in range(12):
        month = now.month - i
        year = now.year
        if month <= 0:
            month += 12
            year -= 1
        periods.append(f"{year}-{month:02d}")
    
    return render_template('record.html', juristic=juristic, incomes=incomes, periods=periods)

@app.route('/record/summary')
def record_summary():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False})
    
    period = request.args.get('period')
    seq_no = request.args.get('seq_no', 1, type=int)
    if not period: return jsonify({"success": False})
    
    from sqlalchemy import func
    counts = db.session.query(Record.income_id, func.count(Record.id), func.sum(Record.total_amt))\
        .filter(Record.juristic_id == j_id, Record.period == period, Record.seq_no == seq_no)\
        .group_by(Record.income_id).all()
    
    summary = []
    for inc_id, count, total_amt in counts:
        inc = Income.query.get(inc_id)
        if inc:
            summary.append({
                "name": inc.name,
                "count": count,
                "total": float(total_amt or 0)
            })
            
    return jsonify({"success": True, "summary": summary})

@app.route('/record/init', methods=['POST'])
def record_init():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    period = request.form.get('period')
    seq_no = request.form.get('seq_no', 1, type=int)
    income_id = request.form.get('income_id')
    
    if not period or not income_id:
        return jsonify({"success": False, "message": "กรุณาเลือกงวดและประเภทรายได้"})
    
    income = Income.query.get(income_id)
    if not income: return jsonify({"success": False, "message": "ไม่พบประเภทรายได้"})
    
    # ดึงห้องทั้งหมด
    rooms = Room.query.filter_by(juristic_id=j_id).order_by(Room.room_no).all()
    
    data = []
    for r in rooms:
        # เช็คว่ามี Record เดิมในงวดนี้หรือยัง
        rec = Record.query.filter_by(room_id=r.id, income_id=income_id, period=period, seq_no=seq_no).first()
        
        prev_unit = 0.0
        # ถ้าเป็นแบบคูณหน่วย (เช่น ค่าน้ำ) ให้ดึงหน่วยก่อนหน้า
        if income.condition == 'คูณหน่วย':
            # หาหางวดล่าสุดเท่าที่มี ก่อนงวดปัจจุบัน (เปรียบเทียบ period และ seq_no)
            prev_rec = Record.query.filter(
                Record.room_id == r.id, 
                Record.income_id == income_id, 
                or_(
                    Record.period < period,
                    and_(Record.period == period, Record.seq_no < seq_no)
                ),
                Record.curr_unit > 0
            ).order_by(Record.period.desc(), Record.seq_no.desc()).first()
            
            if prev_rec:
                # กลับไปใช้ตรรกะเดิม: [มิเตอร์เริ่มต้นงวดก่อน] + [จำนวนที่ใช้ไปงวดก่อน] = [มิเตอร์เริ่มต้นงวดใหม่]
                prev_unit = (prev_rec.prev_unit or 0.0) + (prev_rec.used_unit or 0.0)
            
        data.append({
            "room_id": r.id,
            "room_no": r.room_no,
            "record_id": rec.id if rec else None,
            "prev_unit": rec.prev_unit if rec else prev_unit,
            "curr_unit": rec.curr_unit if rec else 0.0,
            "used_unit": rec.used_unit if rec else 0.0,
            "rate": rec.rate if rec else (income.rate or 0.0),
            "total_amt": rec.total_amt if rec else 0.0,
            "remark": rec.remark if rec else "",
            "is_billed": rec.is_billed if rec else False,
            "sq_area": r.sq_area or 0.0,
            "ratio": r.ratio or 0.0
        })
        
    return jsonify({
        "success": True, 
        "data": data, 
        "condition": income.condition,
        "income_rate": income.rate or 0.0
    })

@app.route('/record/save', methods=['POST'])
def record_save():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    period = request.json.get('period')
    seq_no = int(request.json.get('seq_no') or 1)
    income_id = request.json.get('income_id')
    records_data = request.json.get('records', []) # รับเป็น JSON
    
    try:
        for item in records_data:
            room_id = item.get('room_id')
            # หา Record เดิม
            rec = Record.query.filter_by(room_id=room_id, income_id=income_id, period=period, seq_no=seq_no).first()
            
            if not rec:
                rec = Record(
                    juristic_id=j_id,
                    room_id=room_id,
                    income_id=income_id,
                    period=period,
                    seq_no=seq_no
                )
                db.session.add(rec)
            
            # ไม่อัปเดตถ้าออกบิลไปแล้ว
            if rec.is_billed: continue
            
            rec.prev_unit = float(item.get('prev_unit') or 0.0)
            rec.curr_unit = float(item.get('curr_unit') or 0.0)
            rec.used_unit = float(item.get('used_unit') or 0.0)
            rec.rate = float(item.get('rate') or 0.0)
            rec.total_amt = float(item.get('total_amt') or 0.0)
            rec.remark = item.get('remark', '')
            
        db.session.commit()
        return jsonify({"success": True, "message": "บันทึกข้อมูลสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@app.route('/invoice')
def invoice_manage():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('select_juristic'))
    juristic = Juristic.query.get(j_id)
    
    # ดึงงวดที่มีการออกบิลไปแล้ว
    periods = db.session.query(ArHeader.period).filter(ArHeader.juristic_id == j_id).distinct().order_by(ArHeader.period.desc()).all()
    periods = [p[0] for p in periods]
    
    # ดึง Invoice พร้อมฟิลเตอร์
    period_filter = request.args.get('period')
    seq_filter = request.args.get('seq_no', type=int)
    
    query = ArHeader.query.filter_by(juristic_id=j_id)
    if period_filter:
        query = query.filter_by(period=period_filter)
    if seq_filter:
        query = query.filter_by(seq_no=seq_filter)
        
    invoices = query.order_by(ArHeader.id.desc()).all()
    
    # ดึงงวดที่บันทึกไว้ (เพื่อนำไปออกบิล)
    record_periods = db.session.query(Record.period).filter(Record.juristic_id == j_id).distinct().all()
    record_periods = [p[0] for p in record_periods]

    return render_template('invoice.html', juristic=juristic, periods=periods, invoices=invoices, 
                           sel_period=period_filter, sel_seq=seq_filter, record_periods=record_periods)

@app.route('/invoice/generate', methods=['POST'])
def generate_invoices():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    period = request.form.get('period')
    seq_no = request.form.get('seq_no', 1, type=int)
    if not period: return jsonify({"success": False, "message": "กรุณาเลือกว่างวดไหน"})
    
    try:
        # 1. ดึง Record ที่ยังไม่ได้ออกบิลในงวดนี้ และ Sequence นี้
        records = Record.query.filter_by(juristic_id=j_id, period=period, seq_no=seq_no, is_billed=False).all()
        if not records:
            return jsonify({"success": False, "message": "ไม่มีรายการใหม่ให้ออกบิลในงวดนี้"})
            
        # 2. จัดกลุ่มตามห้อง
        from collections import defaultdict
        room_records = defaultdict(list)
        for r in records:
            room_records[r.room_id].append(r)
            
        import datetime
        today = datetime.date.today()
        
        invoice_count = 0
        for room_id, recs in room_records.items():
            # ดึงผู้อยู่อาศัยปัจจุบัน
            active_res = RoomResident.query.filter_by(room_id=room_id, active=True).first()
            customer_id = active_res.customer_id if active_res else None
            
            # สร้าง ArHeader
            header = ArHeader(
                juristic_id=j_id,
                room_id=room_id,
                customer_id=customer_id,
                date=today,
                period=period,
                seq_no=seq_no,
                duedate=today + datetime.timedelta(days=15), # กำหนดจ่ายใน 15 วัน
                status='unpaid',
                amount=0.0,
                grand_total=0.0
            )
            db.session.add(header)
            db.session.flush() # เพื่อให้ได้ header.id
            
            total_amt = 0.0
            for r in recs:
                # คำนวณภาษี
                vat_amt = 0.0
                if r.income.is_vat:
                    vat_amt = r.total_amt * 0.07
                
                detail = ArDetail(
                    header_id=header.id,
                    record_id=r.id,
                    item_name=r.income.name,
                    amount=r.total_amt,
                    vat_amount=vat_amt,
                    total_amount=r.total_amt + vat_amt
                )
                db.session.add(detail)
                total_amt += (r.total_amt + vat_amt)
                
                # ทำเครื่องหมายว่าออกบิลแล้ว
                r.is_billed = True
                
            header.amount = total_amt # ในทีนี้คือยอดรวมสุทธิ (หรือจะแยก amount กับ grand_total ก็ได้)
            header.grand_total = total_amt
            invoice_count = invoice_count + 1
            
        db.session.commit()
        return jsonify({"success": True, "message": f"ออกใบแจ้งหนี้สำเร็จจำนวน {invoice_count} ใบ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

# --- Receipt (RC) Routes ---

@app.route('/receipt')
def receipt_manage():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('login'))
    
    rooms = Room.query.filter_by(juristic_id=j_id, active=True).order_by(Room.room_no).all()
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    return render_template('receipt.html', rooms=rooms, today_str=today_str)

@app.route('/receipt/unpaid')
def receipt_unpaid():
    j_id = session.get('juristic_id')
    room_id = request.args.get('room_id')
    if not j_id or not room_id: return jsonify({"success": False})
    
    # ดึงบิลที่ค้างชำระ (unpaid หรือ partial)
    unpaid = ArHeader.query.filter(
        ArHeader.juristic_id == j_id,
        ArHeader.room_id == room_id,
        ArHeader.status.in_(['unpaid', 'partial']),
        ArHeader.is_void == False
    ).order_by(ArHeader.period, ArHeader.seq_no).all()
    
    data = []
    for ar in unpaid:
        data.append({
            "id": ar.id,
            "period": ar.period,
            "seq_no": ar.seq_no,
            "grand_total": ar.grand_total,
            "paid_amount": ar.paid_amount,
            "remain": ar.grand_total - ar.paid_amount,
            "date": ar.date.strftime('%Y-%m-%d') if ar.date else ""
        })
    return jsonify({"success": True, "data": data})

@app.route('/receipt/save', methods=['POST'])
def receipt_save():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    data = request.json
    room_id = data.get('room_id')
    pay_date = data.get('pay_date')
    pay_type = data.get('pay_type')
    total_pay = float(data.get('total_pay', 0))
    items = data.get('items', []) # รายการบิลที่เลือกจ่าย
    
    if not items or total_pay <= 0:
        return jsonify({"success": False, "message": "กรุณาเลือกบิลและระบุยอดเงิน"})

    try:
        # 1. สร้างเลขที่ใบเสร็จ (RC-YYYYMM-XXXX)
        now = datetime.datetime.now()
        prefix = f"RC-{now.strftime('%Y%m')}-"
        last_rc = RcHeader.query.filter(RcHeader.rc_no.like(f"{prefix}%")).order_by(RcHeader.id.desc()).first()
        if last_rc:
            last_num = int(last_rc.rc_no.split('-')[-1])
            new_no = f"{prefix}{str(last_num + 1).zfill(4)}"
        else:
            new_no = f"{prefix}0001"

        # ดึงลูกค้าปัจจุบันของห้อง
        active_res = RoomResident.query.filter_by(room_id=room_id, active=True).first()
        customer_id = active_res.customer_id if active_res else None

        # 2. สร้าง RcHeader
        rc = RcHeader(
            juristic_id=j_id,
            rc_no=new_no,
            customer_id=customer_id,
            rc_date=datetime.datetime.strptime(pay_date, '%Y-%m-%d').date(),
            total_pay=total_pay,
            pay_type=pay_type,
            create_by=session.get('user_name')
        )
        db.session.add(rc)
        db.session.flush()

        remaining_pay = total_pay
        for item in items:
            if remaining_pay <= 0: break
            
            ar = ArHeader.query.get(item['ar_id'])
            if not ar: continue
            
            ar_remain = ar.grand_total - ar.paid_amount
            pay_for_this = min(remaining_pay, ar_remain)
            
            # สร้าง RcDetail
            detail = RcDetail(
                header_id=rc.id,
                ar_header_id=ar.id,
                amount=pay_for_this
            )
            db.session.add(detail)
            
            # อัปเดต ArHeader
            ar.paid_amount += pay_for_this
            if ar.paid_amount >= ar.grand_total:
                ar.status = 'paid'
            else:
                ar.status = 'partial'
                
            remaining_pay -= pay_for_this

        db.session.commit()
        return jsonify({"success": True, "message": f"บันทึกรับชำระสำเร็จ เลขที่ {new_no}", "rc_id": rc.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@app.route('/receipt/list')
def receipt_list():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False})
    
    # ดึงใบเสร็จ 100 ใบหลังสุด
    receipts = RcHeader.query.filter_by(juristic_id=j_id).order_by(RcHeader.id.desc()).limit(100).all()
    data = []
    for r in receipts:
        # หาชื่อลูกค้าและห้อง (จาก ar_header ใน detail แรก)
        first_detail = r.details[0] if r.details else None
        room_no = first_detail.ar_header.room.room_no if first_detail else "Unknown"
        
        data.append({
            "id": r.id,
            "rc_no": r.rc_no,
            "rc_date": r.rc_date.strftime('%Y-%m-%d'),
            "customer_name": r.customer.name if r.customer else "Unknown",
            "room_no": room_no,
            "total_pay": r.total_pay,
            "pay_type": r.pay_type,
            "is_void": r.is_void
        })
    return jsonify({"success": True, "data": data})

@app.route('/receipt/void', methods=['POST'])
def receipt_void():
    j_id = session.get('juristic_id')
    rc_id = request.json.get('id')
    reason = request.json.get('reason')
    
    if not j_id or not rc_id: return jsonify({"success": False})
    
    try:
        rc = RcHeader.query.get(rc_id)
        if not rc or rc.is_void:
            return jsonify({"success": False, "message": "ใบเสร็จไม่ถูกต้องหรือถูกยกเลิกไปแล้ว"})
        
        # คืนยอดใน ArHeader
        for d in rc.details:
            ar = d.ar_header
            ar.paid_amount -= d.amount
            if ar.paid_amount <= 0:
                ar.paid_amount = 0
                ar.status = 'unpaid'
            else:
                ar.status = 'partial'
        
        rc.is_void = True
        rc.void_reason = reason
        rc.void_by = session.get('user_name')
        rc.void_date = datetime.datetime.now()
        
        db.session.commit()
        return jsonify({"success": True, "message": "ยกเลิกใบเสร็จสำเร็จ ยอดค้างชำระถูกตีคืนเรียบร้อย"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@app.route('/receipt/print/<int:id>')
def receipt_print(id):
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('login'))
    
    rc = RcHeader.query.get_or_404(id)
    juristic = Juristic.query.get(j_id)
    
    # รวมรายละเอียดว่าจ่ายบิลไหนบ้าง
    pay_details = []
    for d in rc.details:
        pay_details.append({
            "period": d.ar_header.period,
            "seq_no": d.ar_header.seq_no,
            "amount": d.amount,
            "room_no": d.ar_header.room.room_no
        })
        
    paper_size = request.args.get('size', 'a4')
    return render_template('receipt_print.html', rc=rc, juristic=juristic, pay_details=pay_details, paper_size=paper_size)


@app.route('/invoice/view/<int:inv_id>')
def view_invoice(inv_id):
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('select_juristic'))
    
    header = ArHeader.query.filter_by(id=inv_id, juristic_id=j_id).first()
    if not header: abort(404)
    
    juristic = Juristic.query.get(j_id)
    paper_size = request.args.get('size', 'a4')
    return render_template('invoice_print.html', header=header, juristic=juristic, paper_size=paper_size)

@app.route('/invoice/print/bulk')
def print_bulk_invoices():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('select_juristic'))
    
    ids_str = request.args.get('ids', '')
    if not ids_str: return "No IDs provided", 400
    
    ids = [int(i) for i in ids_str.split(',') if i.strip().isdigit()]
    headers = ArHeader.query.filter(ArHeader.id.in_(ids), ArHeader.juristic_id == j_id).all()
    
    juristic = Juristic.query.get(j_id)
    paper_size = request.args.get('size', 'a4')
    return render_template('invoice_bulk_print.html', headers=headers, juristic=juristic, paper_size=paper_size)

@app.route('/invoice/delete/<int:inv_id>', methods=['POST'])
def delete_invoice(inv_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    header = ArHeader.query.filter_by(id=inv_id, juristic_id=j_id).first()
    if not header: return jsonify({"success": False, "message": "ไม่พบข้อมูล"})
    
    try:
        # คืนสถานะ Record ให้กลับเป็นยังไม่ไดออกบิล
        for d in header.details:
            if d.record_id:
                rec = Record.query.get(d.record_id)
                if rec: rec.is_billed = False
        
        db.session.delete(header)
        db.session.commit()
        return jsonify({"success": True, "message": "ลบใบแจ้งหนี้สำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})
def get_customers_json():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify([])
    # เลือกเฉพาะสมาชิกที่ยัง Active อยู่เพื่อนำไปมอบหมายห้อง
    customers = Customer.query.filter_by(juristic_id=j_id, active=True).all()
    return jsonify([{"id": c.id, "name": c.name} for c in customers])

@app.route('/room/assign_resident', methods=['POST'])
def assign_resident():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    room_id = request.form.get('room_id')
    customer_id = request.form.get('customer_id')
    res_type = request.form.get('residence_type', 'tenant') # owner or tenant
    
    if not room_id or not customer_id:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบ"})
        
    try:
        # 1. ปิด Active Resident เดิมในห้องนี้
        RoomResident.query.filter_by(room_id=room_id, active=True).update({"active": False, "end_date": db.func.current_date()})
        
        # 2. เพิ่มรายการใหม่
        new_res = RoomResident(
            juristic_id=j_id, # เพิ่ม juristic_id ที่ขาดไป
            room_id=room_id,
            customer_id=customer_id,
            residence_type=res_type,
            start_date=db.func.current_date(),
            active=True
        )
        db.session.add(new_res)
        
        # 3. อัปเดตสถานะห้อง
        room = Room.query.get(room_id)
        if room:
            room.status = 'มีผู้อยู่อาศัย'
            
        db.session.commit()
        return jsonify({"success": True, "message": "มอบหมายผู้อยู่อาศัยสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@app.route('/room/history/<int:r_id>', methods=['GET'])
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

@app.route('/customer', methods=['GET'])
def customer() -> str:
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('select_juristic'))
    juristic = Juristic.query.get(j_id)
    customers = Customer.query.filter_by(juristic_id=j_id).all()
    return render_template('customer.html', customers=customers, juristic=juristic)

@app.route('/customer/add', methods=['POST'])
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
        # เช็ค email ซ้ำ
        existing = Customer.query.filter_by(email=email).first()
        if existing:
            return jsonify({"success": False, "message": "อีเมลนี้ถูกใช้งานแล้ว"})
            
        new_customer = Customer(
            juristic_id=j_id,
            name=name,
            email=email,
            username=email,
            password_hash=generate_password_hash(password) if password else None,
            role=role,
            phone=phone,
            idcard=idcard,
            address=address
        )
        db.session.add(new_customer)
        db.session.commit()
        return jsonify({"success": True, "message": "เพิ่มสมาชิกสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@app.route('/customer/get/<int:c_id>')
def get_customer(c_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    cust = Customer.query.filter_by(id=c_id, juristic_id=j_id).first()
    if not cust: return jsonify({"success": False, "message": "ไม่พบข้อมูลสมาชิก"})
    
    return jsonify({
        "success": True,
        "customer": {
            "id": cust.id,
            "name": cust.name,
            "email": cust.email,
            "phone": cust.phone,
            "role": cust.role,
            "idcard": cust.idcard,
            "address": cust.address,
            "active": cust.active
        }
    })

@app.route('/customer/update/<int:c_id>', methods=['POST'])
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
    active = request.form.get('active') == 'on' # Checkbox handling
    
    if not name or not email:
        return jsonify({"success": False, "message": "กรุณากรอกชื่อและอีเมล"})
        
    try:
        # เช็ค email ซ้ำ (ยกเว้นของตัวเอง)
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
        
        if password: # อัปเดตรหัสผ่านเฉพาะเมื่อมีการกรอกมาใหม่
            cust.password_hash = generate_password_hash(password)
            
        db.session.commit()
        return jsonify({"success": True, "message": "อัปเดตข้อมูลสำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@app.route('/customer/delete/<int:c_id>', methods=['POST'])
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5005, debug=True)