from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template, abort
from models import db, ArHeader, ArDetail, RcHeader, RcDetail, Record, Room, Juristic, RoomResident
from collections import defaultdict
import datetime

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/invoice')
def invoice_manage():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('juristic.select_juristic'))
    juristic = Juristic.query.get(j_id)
    
    periods = db.session.query(ArHeader.period).filter(ArHeader.juristic_id == j_id).distinct().order_by(ArHeader.period.desc()).all()
    periods = [p[0] for p in periods]
    
    period_filter = request.args.get('period')
    seq_filter = request.args.get('seq_no', type=int)
    
    query = ArHeader.query.filter_by(juristic_id=j_id)
    if period_filter:
        query = query.filter_by(period=period_filter)
    if seq_filter:
        query = query.filter_by(seq_no=seq_filter)
        
    invoices = query.order_by(ArHeader.id.desc()).all()
    
    record_periods = db.session.query(Record.period, Record.seq_no).filter(
        Record.juristic_id == j_id,
        Record.is_billed == False
    ).distinct().order_by(Record.period.desc(), Record.seq_no.asc()).all()
    record_periods = [{'period': p, 'seq_no': s} for p, s in record_periods]

    return render_template('invoice.html', juristic=juristic, periods=periods, invoices=invoices, 
                           sel_period=period_filter, sel_seq=seq_filter, record_periods=record_periods)

@billing_bp.route('/invoice/generate', methods=['POST'])
def generate_invoices():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    period_seq = request.form.get('period_seq')
    if not period_seq:
        return jsonify({"success": False, "message": "กรุณาเลือกงวดที่ต้องการออกบิล"})

    if '|' in period_seq:
        period, seq_no = period_seq.split('|', 1)
        try:
            seq_no = int(seq_no)
        except ValueError:
            return jsonify({"success": False, "message": "เลขที่งวดไม่ถูกต้อง"})
    else:
        period = period_seq
        seq_no = request.form.get('seq_no', 1, type=int)

    try:
        records = Record.query.filter_by(juristic_id=j_id, period=period, seq_no=seq_no, is_billed=False).all()
        if not records:
            return jsonify({"success": False, "message": "ไม่มีรายการใหม่ให้ออกบิลในงวดนี้"})
            
        room_records = defaultdict(list)
        for r in records:
            room_records[r.room_id].append(r)
            
        today = datetime.date.today()
        invoice_count = 0
        for room_id, recs in room_records.items():
            active_res = RoomResident.query.filter_by(room_id=room_id, active=True).first()
            customer_id = active_res.customer_id if active_res else None
            
            header = ArHeader(
                juristic_id=j_id, room_id=room_id, customer_id=customer_id, date=today,
                period=period, seq_no=seq_no, duedate=today + datetime.timedelta(days=15),
                status='unpaid', amount=0.0, grand_total=0.0
            )
            db.session.add(header)
            db.session.flush()
            
            total_amt = 0.0
            for r in recs:
                vat_amt = r.total_amt * 0.07 if r.income.is_vat else 0.0
                detail = ArDetail(
                    header_id=header.id, record_id=r.id, item_name=r.income.name,
                    amount=r.total_amt, vat_amount=vat_amt, total_amount=r.total_amt + vat_amt
                )
                db.session.add(detail)
                total_amt += (r.total_amt + vat_amt)
                r.is_billed = True
                
            header.amount = total_amt
            header.grand_total = total_amt
            invoice_count += 1
            
        db.session.commit()
        return jsonify({"success": True, "message": f"ออกใบแจ้งหนี้สำเร็จจำนวน {invoice_count} ใบ"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@billing_bp.route('/receipt')
def receipt_manage():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('auth.index'))
    
    rooms = Room.query.filter_by(juristic_id=j_id, active=True).order_by(Room.room_no).all()
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    return render_template('receipt.html', rooms=rooms, today_str=today_str)

@billing_bp.route('/receipt/unpaid')
def receipt_unpaid():
    j_id = session.get('juristic_id')
    room_id = request.args.get('room_id')
    if not j_id or not room_id: return jsonify({"success": False})
    
    unpaid = ArHeader.query.filter(
        ArHeader.juristic_id == j_id, ArHeader.room_id == room_id,
        ArHeader.status.in_(['unpaid', 'partial']), ArHeader.is_void == False
    ).order_by(ArHeader.period, ArHeader.seq_no).all()
    
    data = []
    for ar in unpaid:
        data.append({
            "id": ar.id, "period": ar.period, "seq_no": ar.seq_no, "grand_total": ar.grand_total,
            "paid_amount": ar.paid_amount, "remain": ar.grand_total - ar.paid_amount,
            "date": ar.date.strftime('%Y-%m-%d') if ar.date else ""
        })
    return jsonify({"success": True, "data": data})

@billing_bp.route('/receipt/save', methods=['POST'])
def receipt_save():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    data = request.json
    room_id = data.get('room_id')
    pay_date = data.get('pay_date')
    pay_type = data.get('pay_type')
    total_pay = float(data.get('total_pay', 0))
    items = data.get('items', [])
    
    if not items or total_pay <= 0:
        return jsonify({"success": False, "message": "กรุณาเลือกบิลและระบุยอดเงิน"})

    try:
        now = datetime.datetime.now()
        prefix = f"RC-{now.strftime('%Y%m')}-"
        last_rc = RcHeader.query.filter(RcHeader.rc_no.like(f"{prefix}%")).order_by(RcHeader.id.desc()).first()
        new_no = f"{prefix}{str(int(last_rc.rc_no.split('-')[-1]) + 1).zfill(4)}" if last_rc else f"{prefix}0001"

        active_res = RoomResident.query.filter_by(room_id=room_id, active=True).first()
        customer_id = active_res.customer_id if active_res else None

        rc = RcHeader(
            juristic_id=j_id, rc_no=new_no, customer_id=customer_id,
            rc_date=datetime.datetime.strptime(pay_date, '%Y-%m-%d').date(),
            total_pay=total_pay, pay_type=pay_type, create_by=session.get('user_name')
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
            
            detail = RcDetail(header_id=rc.id, ar_header_id=ar.id, amount=pay_for_this)
            db.session.add(detail)
            
            ar.paid_amount += pay_for_this
            ar.status = 'paid' if ar.paid_amount >= ar.grand_total else 'partial'
            remaining_pay -= pay_for_this

        db.session.commit()
        return jsonify({"success": True, "message": f"บันทึกรับชำระสำเร็จ เลขที่ {new_no}", "rc_id": rc.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@billing_bp.route('/receipt/list')
def receipt_list():
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False})
    
    receipts = RcHeader.query.filter_by(juristic_id=j_id).order_by(RcHeader.id.desc()).limit(100).all()
    data = []
    for r in receipts:
        first_detail = r.details[0] if r.details else None
        room_no = first_detail.ar_header.room.room_no if first_detail else "Unknown"
        data.append({
            "id": r.id, "rc_no": r.rc_no, "rc_date": r.rc_date.strftime('%Y-%m-%d'),
            "customer_name": r.customer.name if r.customer else "Unknown",
            "room_no": room_no, "total_pay": r.total_pay, "pay_type": r.pay_type, "is_void": r.is_void
        })
    return jsonify({"success": True, "data": data})

@billing_bp.route('/receipt/void', methods=['POST'])
def receipt_void():
    j_id = session.get('juristic_id')
    rc_id = request.json.get('id')
    reason = request.json.get('reason')
    
    if not j_id or not rc_id: return jsonify({"success": False})
    
    try:
        rc = RcHeader.query.get(rc_id)
        if not rc or rc.is_void: return jsonify({"success": False, "message": "ใบเสร็จไม่ถูกต้องหรือถูกยกเลิกไปแล้ว"})
        
        for d in rc.details:
            ar = d.ar_header
            ar.paid_amount -= d.amount
            ar.status = 'unpaid' if ar.paid_amount <= 0 else 'partial'
            if ar.paid_amount < 0: ar.paid_amount = 0
        
        rc.is_void = True
        rc.void_reason = reason
        rc.void_by = session.get('user_name')
        rc.void_date = datetime.datetime.now()
        
        db.session.commit()
        return jsonify({"success": True, "message": "ยกเลิกใบเสร็จสำเร็จ ยอดค้างชำระถูกตีคืนเรียบร้อย"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})

@billing_bp.route('/receipt/print/<int:id>')
def receipt_print(id):
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('auth.index'))
    
    rc = RcHeader.query.get_or_404(id)
    juristic = Juristic.query.get(j_id)
    
    pay_details = []
    for d in rc.details:
        pay_details.append({
            "period": d.ar_header.period, "seq_no": d.ar_header.seq_no,
            "amount": d.amount, "room_no": d.ar_header.room.room_no
        })
        
    paper_size = request.args.get('size', 'a4')
    return render_template('receipt_print.html', rc=rc, juristic=juristic, pay_details=pay_details, paper_size=paper_size)

@billing_bp.route('/invoice/view/<int:inv_id>')
def view_invoice(inv_id):
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('juristic.select_juristic'))
    
    header = ArHeader.query.filter_by(id=inv_id, juristic_id=j_id).first()
    if not header: abort(404)
    
    juristic = Juristic.query.get(j_id)
    paper_size = request.args.get('size', 'a4')
    return render_template('invoice_print.html', header=header, juristic=juristic, paper_size=paper_size)

@billing_bp.route('/invoice/print/bulk')
def print_bulk_invoices():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('juristic.select_juristic'))
    
    ids_str = request.args.get('ids', '')
    if not ids_str: return "No IDs provided", 400
    
    ids = [int(i) for i in ids_str.split(',') if i.strip().isdigit()]
    headers = ArHeader.query.filter(ArHeader.id.in_(ids), ArHeader.juristic_id == j_id).all()
    
    juristic = Juristic.query.get(j_id)
    paper_size = request.args.get('size', 'a4')
    return render_template('invoice_bulk_print.html', headers=headers, juristic=juristic, paper_size=paper_size)

@billing_bp.route('/invoice/delete/<int:inv_id>', methods=['POST'])
def delete_invoice(inv_id):
    j_id = session.get('juristic_id')
    if not j_id: return jsonify({"success": False, "message": "Unauthorized"})
    
    header = ArHeader.query.filter_by(id=inv_id, juristic_id=j_id).first()
    if not header: return jsonify({"success": False, "message": "ไม่พบข้อมูล"})
    
    try:
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