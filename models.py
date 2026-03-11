# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    juristic_id = db.Column(db.Integer, db.ForeignKey('juristic.id'), nullable=False) # ตัวแยกข้อมูล
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))
    amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='unpaid')
    


class Juristic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # ตั้ง unique กันชื่อซ้ำ
    subdomain = db.Column(db.String(50), unique=True, nullable=True)
    api_key = db.Column(db.String(100), nullable=True)
    rooms = db.relationship('Room', backref='juristic', lazy=True)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), nullable=False)
    juristic_id = db.Column(db.Integer, db.ForeignKey('juristic.id'), nullable=False)    
    
    