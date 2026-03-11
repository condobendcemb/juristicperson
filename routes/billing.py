# routes/billing.py (บางส่วน)
@billing_bp.route('/update-water', methods=['POST'])
def update_water():
    room_id = request.form.get('room_id')
    reading = float(request.form.get('reading'))
    
    # Logic: บันทึกลง DB
    new_record = WaterMeter(room_id=room_id, current_reading=reading)
    db.session.add(new_record)
    db.session.commit()
    
    # แทนที่จะ redirect เราส่งกลับแค่ "ข้อความสำเร็จ" หรือ "แถวใหม่"
    return f'<span class="text-emerald-400 animate-pulse">บันทึกแล้ว: {reading}</span>'