import os
from dotenv import load_dotenv

load_dotenv()

from app import app
from extensions import db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        print("--- Migration V5 (Email/TOTP columns) ---")
        try:
            db.session.execute(text("ALTER TABLE customer ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT FALSE"))
            db.session.execute(text("ALTER TABLE customer ADD COLUMN IF NOT EXISTS email_otp VARCHAR(10)"))
            db.session.execute(text("ALTER TABLE customer ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(100)"))
            print("Successfully added Email/TOTP columns to 'customer' table.")
        except Exception as e:
            print(f"Update error: {e}")

        db.session.commit()
if __name__ == "__main__":
    run_migration()
