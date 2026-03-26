from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template
from models import db, Income, Juristic

income_bp = Blueprint('income', __name__)

@income_bp.route('/income')
def index():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('juristic.select_juristic'))
    juristic = Juristic.query.get(j_id)
    incomes = Income.query.filter_by(juristic_id=j_id).all()
    return render_template('income.html', incomes=incomes, juristic=juristic)

@income_bp.route('/income/add', methods=['POST'])
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
            juristic_id=j_id, name=name, rate=float(rate) if rate else 0.0,
            condition=condition, penalty=float(penalty) if penalty else 0.0,
            is_vat=is_vat
        )
        db.session.add(new_inc)
        db.session.commit()
        return jsonify({"success": True, "message": "เพิ่มรายการรายได้สำเร็จ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@income_bp.route('/income/get/<int:i_id>')
def get_income(i_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    inc = Income.query.filter_by(id=i_id, juristic_id=j_id).first()
    if not inc: return jsonify({"success": False, "message": "ไม่พบข้อมูล"})
    return jsonify({
        "success": True,
        "income": {
            "id": inc.id, "name": inc.name, "rate": inc.rate, "condition": inc.condition,
            "penalty": inc.penalty, "is_vat": inc.is_vat, "active": inc.active
        }
    })

@income_bp.route('/income/update/<int:i_id>', methods=['POST'])
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

@income_bp.route('/income/delete/<int:i_id>', methods=['POST'])
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
