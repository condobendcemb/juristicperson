import os
from dotenv import load_dotenv

load_dotenv()

from app import app
from extensions import db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        print("--- Running final fix migration ---")
        try:
            # 1. ยอมให้ juristic_id เป็น NULL ได้สำหรับ Admin ตอนสมัครแรกเริ่ม
            db.session.execute(text("ALTER TABLE customer ALTER COLUMN juristic_id DROP NOT NULL"))
            print("Successfully made juristic_id NULLABLE in 'customer' table.")
        except Exception as e:
            print(f"Update error: {e}")

        db.session.commit()
if __name__ == "__main__":
    run_migration()
