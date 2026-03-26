from app import app
from models import db, Customer, JuristicAdminMapping

def run_migration():
    with app.app_context():
        # 1. สร้างตารางใหม่ (ถ้ายังไม่เคยมี)
        db.create_all()
        print("--- 1. Tables created/checked ---")

        # 2. ย้ายข้อมูลจาก Customer.juristic_id เดิมลงตารางกลาง
        admins = Customer.query.filter_by(role='admin').all()
        migrated_count = 0
        for admin in admins:
            if admin.juristic_id:
                # เช็คว่ามีอยู่แล้วหรือยัง
                existing = JuristicAdminMapping.query.filter_by(
                    juristic_id=admin.juristic_id, 
                    customer_id=admin.id
                ).first()
                if not existing:
                    mapping = JuristicAdminMapping(
                        juristic_id=admin.juristic_id, 
                        customer_id=admin.id
                    )
                    db.session.add(mapping)
                    migrated_count += 1
        
        db.session.commit()
        print(f"--- 2. Migration complete! Linked {migrated_count} existing admin(s) to their projects ---")

if __name__ == "__main__":
    run_migration()
