import os
from dotenv import load_dotenv

load_dotenv()

from app import app
from extensions import db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        print("--- Migration V6 (Add total_rooms to juristic) ---")
        try:
            db.session.execute(text("ALTER TABLE juristic ADD COLUMN IF NOT EXISTS total_rooms INTEGER"))
            print("Successfully added 'total_rooms' column to 'juristic' table.")
        except Exception as e:
            print(f"Update error: {e}")

        db.session.commit()

if __name__ == "__main__":
    run_migration()