from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template
from models import db, Record, Income, Room, Juristic
from sqlalchemy import or_, and_, func
import datetime

record_bp = Blueprint('record', __name__)

@record_bp.route('/record')
def index():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('juristic.select_juristic'))
    juristic = Juristic.query.get(j_id)
    incomes = Income.query.filter_by(juristic_id=j_id, active=True).all()
    
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

@record_bp.route('/record/summary')
def record_summary():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False})
    
    period = request.args.get('period')
    seq_no = request.args.get('seq_no', 1, type=int)
    if not period: return jsonify({"success": False})
    
    counts = db.session.query(Record.income_id, func.count(Record.id), func.sum(Record.total_amt))\
        .filter(Record.juristic_id == j_id, 
                Record.period == period, 
                Record.seq_no == seq_no,
                Record.total_amt > 0\
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

@record_bp.route('/record/init', methods=['POST'])
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
    
    rooms = Room.query.filter_by(juristic_id=j_id).order_by(Room.room_no).all()
    
    data = []
    for r in rooms:
        rec = Record.query.filter_by(room_id=r.id, income_id=income_id, period=period, seq_no=seq_no).first()
        
        prev_unit = 0.0
        if income.condition == 'คูณหน่วย':
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
                prev_unit = (prev_rec.prev_unit or 0.0) + (prev_rec.used_unit or 0.0)
            
        data.append({
            "room_id": r.id, "room_no": r.room_no, "record_id": rec.id if rec else None,
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
        "success": True, "data": data, "condition": income.condition, "income_rate": income.rate or 0.0
    })

@record_bp.route('/record/save', methods=['POST'])
def record_save():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    period = request.json.get('period')
    seq_no = int(request.json.get('seq_no') or 1)
    income_id = request.json.get('income_id')
    records_data = request.json.get('records', [])
    
    try:
        for item in records_data:
            room_id = item.get('room_id')
            rec = Record.query.filter_by(room_id=room_id, income_id=income_id, period=period, seq_no=seq_no).first()
            if not rec:
                rec = Record(juristic_id=j_id, room_id=room_id, income_id=income_id, period=period, seq_no=seq_no)
                db.session.add(rec)
            
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
