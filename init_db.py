from app import app
from models import db, Juristic, Room

with app.app_context():
    # 1. สร้างตาราง
    db.create_all()
    print("--- 1. Tables Created! ---")

    # 2. เพิ่มข้อมูลทดสอบ (ถ้ายังไม่มี)
    if not Juristic.query.first():
        j1 = Juristic(name='บางบอนวิลล่า')
        j2 = Juristic(name='มาสเตอร์คอนโด')
        db.session.add_all([j1, j2])
        db.session.commit()
        
        r1 = Room(room_no='A-101', juristic_id=j1.id)
        r2 = Room(room_no='M-999', juristic_id=j2.id)
        db.session.add_all([r1, r2])
        db.session.commit()
        print("--- 2. Seed Data Added! ---")
    else:
        print("--- Data already exists, skipping seed ---")
        