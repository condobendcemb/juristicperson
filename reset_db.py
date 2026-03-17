from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    try:
        print("Dropping and recreating public schema...")
        db.session.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO postgres; GRANT ALL ON SCHEMA public TO public;"))
        db.session.commit()
        
        print("Creating new tables from models.py...")
        db.create_all()
        print("Database schema reset successfully! Ready for new data.")
    except Exception as e:
        print(f"Error: {e}")
