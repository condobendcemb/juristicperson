import os
from dotenv import load_dotenv

# MUST LOAD BEFORE IMPORTING APP
load_dotenv() 

from app import app
from extensions import db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        print("--- Starting Migration V3 (Adding KYC & Billing columns) ---")
        
        # 1. เพิ่มคอลัมน์ในตาราง customer
        try:
            db.session.execute(text("ALTER TABLE customer ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE"))
            db.session.execute(text("ALTER TABLE customer ADD COLUMN IF NOT EXISTS verify_status VARCHAR(20) DEFAULT 'unverified'"))
            db.session.execute(text("ALTER TABLE customer ADD COLUMN IF NOT EXISTS verify_at TIMESTAMP"))
            print("Successfully added KYC columns to 'customer' table.")
        except Exception as e:
            print(f"Error updating 'customer' table: {e}")

        # 2. เพิ่มคอลัมน์ในตาราง juristic (เผื่อไว้อาจจะยังไม่มี)
        try:
            db.session.execute(text("ALTER TABLE juristic ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'"))
            db.session.execute(text("ALTER TABLE juristic ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            db.session.execute(text("ALTER TABLE juristic ADD COLUMN IF NOT EXISTS expiry_date TIMESTAMP"))
            print("Successfully added Status/Billing columns to 'juristic' table.")
        except Exception as e:
            print(f"Error updating 'juristic' table: {e}")

        db.session.commit()
        print("--- Migration V3 complete! ---")

if __name__ == "__main__":
    run_migration()
