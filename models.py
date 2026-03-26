from extensions import db
from datetime import datetime

class Juristic(db.Model):
    __tablename__ = 'juristic'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # ตั้ง unique กันชื่อซ้ำ
    subdomain = db.Column(db.String(50), unique=True, nullable=True)
    api_key = db.Column(db.String(100), nullable=True)
    
    # Billing / SaaS Fields
    status = db.Column(db.String(20), default='active') # active, expired, pending_payment
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=True) # วันหมดอายุ
    
    # Relationships
    rooms = db.relationship('Room', backref='juristic', lazy=True)
    customers = db.relationship('Customer', backref='juristic', lazy=True)
    incomes = db.relationship('Income', backref='juristic', lazy=True)
    records = db.relationship('Record', backref='juristic', lazy=True)
    ar_headers = db.relationship('ArHeader', backref='juristic', lazy=True)
    rc_headers = db.relationship('RcHeader', backref='juristic', lazy=True)
    room_residents = db.relationship('RoomResident', backref='juristic', lazy=True)


class Room(db.Model):
    __tablename__ = 'room'
    id = db.Column(db.Integer, primary_key=True)
    juristic_id = db.Column(db.Integer, db.ForeignKey('juristic.id'), nullable=False)    
    building = db.Column(db.String(50), nullable=True)
    floor = db.Column(db.String(20), nullable=True)
    room_no = db.Column(db.String(20), nullable=False)
    home_no = db.Column(db.String(50), nullable=True)
    ratio = db.Column(db.Float, nullable=True)
    sq_area = db.Column(db.Float, nullable=True)
    type = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    active = db.Column(db.Boolean, default=True)
    
    create_by = db.Column(db.String(50), nullable=True)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_by = db.Column(db.String(50), nullable=True)
    update_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ar_headers = db.relationship('ArHeader', backref='room', lazy=True)
    residents = db.relationship('RoomResident', backref='room', lazy=True)


class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    juristic_id = db.Column(db.Integer, db.ForeignKey('juristic.id'), nullable=True) # ของเดิมเป็น False
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=True) # สำหรับ Login
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), default='user') # admin, user
    
    status = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address_work = db.Column(db.Text, nullable=True)
    phone_work = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    lineid = db.Column(db.String(100), nullable=True)
    idcard = db.Column(db.String(50), nullable=True)
    national = db.Column(db.String(50), nullable=True)
    active = db.Column(db.Boolean, default=True)
    
    # Identity Verification (KYC)
    is_verified = db.Column(db.Boolean, default=False)
    verify_status = db.Column(db.String(20), default='unverified') # unverified, pending, verified
    verify_at = db.Column(db.DateTime, nullable=True)
    
    create_by = db.Column(db.String(50), nullable=True)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_by = db.Column(db.String(50), nullable=True)
    update_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ar_headers = db.relationship('ArHeader', backref='customer', lazy=True)
    rc_headers = db.relationship('RcHeader', backref='customer', lazy=True)
    room_history = db.relationship('RoomResident', backref='customer', lazy=True)

class JuristicAdminMapping(db.Model):
    """ตารางกลางเชื่อม Admin กับหลายนิติบุคคล (Many-to-Many)"""
    __tablename__ = 'juristic_admin_mapping'
    id = db.Column(db.Integer, primary_key=True)
    juristic_id = db.Column(db.Integer, db.ForeignKey('juristic.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    role = db.Column(db.String(20), default='admin') # สิทธิ์ในนิตินั้นๆ
    
    # Relationships สำหรับดึงข้อมูลสะดวกๆ
    juristic_info = db.relationship('Juristic', backref='admin_links')
    customer_info = db.relationship('Customer', backref='juristic_links')


class RoomResident(db.Model):
    """ตารางเก็บประวัติผู้อยู่อาศัย/เจ้าของห้อง (Room History)"""
    __tablename__ = 'room_resident'
    id = db.Column(db.Integer, primary_key=True)
    juristic_id = db.Column(db.Integer, db.ForeignKey('juristic.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    
    residence_type = db.Column(db.String(50)) # e.g., 'Owner', 'Tenant'
    start_date = db.Column(db.Date, default=datetime.utcnow)
    end_date = db.Column(db.Date, nullable=True)
    active = db.Column(db.Boolean, default=True)
    remark = db.Column(db.Text, nullable=True)

    create_by = db.Column(db.String(50), nullable=True)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_by = db.Column(db.String(50), nullable=True)
    update_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Income(db.Model):
    __tablename__ = 'income'
    id = db.Column(db.Integer, primary_key=True)
    juristic_id = db.Column(db.Integer, db.ForeignKey('juristic.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    rate = db.Column(db.Float, nullable=True)
    condition = db.Column(db.String(255), nullable=True)
    penalty = db.Column(db.Float, nullable=True)
    is_vat = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)

    create_by = db.Column(db.String(50), nullable=True)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_by = db.Column(db.String(50), nullable=True)
    update_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    records = db.relationship('Record', backref='income', lazy=True)


class Record(db.Model):
    __tablename__ = 'record'
    id = db.Column(db.Integer, primary_key=True)
    juristic_id = db.Column(db.Integer, db.ForeignKey('juristic.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    income_id = db.Column(db.Integer, db.ForeignKey('income.id'), nullable=False)
    
    period = db.Column(db.String(20), nullable=False) # e.g., '2024-01'
    seq_no = db.Column(db.Integer, nullable=True)
    prev_unit = db.Column(db.Float, nullable=True)
    curr_unit = db.Column(db.Float, nullable=True)
    used_unit = db.Column(db.Float, nullable=True)
    rate = db.Column(db.Float, nullable=True)
    total_amt = db.Column(db.Float, nullable=True)
    remark = db.Column(db.Text, nullable=True)
    is_billed = db.Column(db.Boolean, default=False)

    create_by = db.Column(db.String(50), nullable=True)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_by = db.Column(db.String(50), nullable=True)
    update_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ArHeader(db.Model):
    __tablename__ = 'ar_header'
    id = db.Column(db.Integer, primary_key=True)
    juristic_id = db.Column(db.Integer, db.ForeignKey('juristic.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    
    date = db.Column(db.Date, nullable=True) # วันที่ออกบิล
    period = db.Column(db.String(20), nullable=True)
    seq_no = db.Column(db.Integer, nullable=True)
    duedate = db.Column(db.Date, nullable=True)
    
    amount = db.Column(db.Float, nullable=True)
    prev_balance = db.Column(db.Float, nullable=True)
    grand_total = db.Column(db.Float, nullable=True)
    paid_amount = db.Column(db.Float, default=0.0)
    
    status = db.Column(db.String(20), default='unpaid')
    is_void = db.Column(db.Boolean, default=False)
    hist_id = db.Column(db.Integer, nullable=True)
    remark = db.Column(db.Text, nullable=True)

    create_by = db.Column(db.String(50), nullable=True)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_by = db.Column(db.String(50), nullable=True)
    update_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    details = db.relationship('ArDetail', backref='header', lazy=True, cascade="all, delete-orphan")


class ArDetail(db.Model):
    __tablename__ = 'ar_detail'
    id = db.Column(db.Integer, primary_key=True)
    header_id = db.Column(db.Integer, db.ForeignKey('ar_header.id'), nullable=False)
    record_id = db.Column(db.Integer, db.ForeignKey('record.id'), nullable=True)
    
    item_name = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    vat_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    remark = db.Column(db.Text, nullable=True)


class RcHeader(db.Model):
    __tablename__ = 'rc_header'
    id = db.Column(db.Integer, primary_key=True)
    juristic_id = db.Column(db.Integer, db.ForeignKey('juristic.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    
    rc_no = db.Column(db.String(50), nullable=True) # เลขที่ใบเสร็จ
    rc_date = db.Column(db.Date, nullable=False)
    total_pay = db.Column(db.Float, nullable=False)
    pay_type = db.Column(db.String(50), nullable=True) # cash, transfer, cheque
    
    # Cheque Info
    cheque_bank = db.Column(db.String(100), nullable=True)
    bank_branch = db.Column(db.String(100), nullable=True)
    cheque_no = db.Column(db.String(100), nullable=True)
    cheque_date = db.Column(db.Date, nullable=True)
    
    # Void Info
    is_void = db.Column(db.Boolean, default=False)
    void_by = db.Column(db.String(50), nullable=True)
    void_date = db.Column(db.DateTime, nullable=True)
    void_reason = db.Column(db.Text, nullable=True)

    create_by = db.Column(db.String(50), nullable=True)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_by = db.Column(db.String(50), nullable=True)
    update_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    details = db.relationship('RcDetail', backref='header', lazy=True, cascade="all, delete-orphan")


class RcDetail(db.Model):
    __tablename__ = 'rc_detail'
    id = db.Column(db.Integer, primary_key=True)
    header_id = db.Column(db.Integer, db.ForeignKey('rc_header.id'), nullable=False)
    ar_header_id = db.Column(db.Integer, db.ForeignKey('ar_header.id'), nullable=False)
    
    amount = db.Column(db.Float, nullable=False) # ยอดเงินที่ตัดจ่ายในบิลนี้
    remark = db.Column(db.Text, nullable=True)

    ar_header = db.relationship('ArHeader', backref='rc_details', lazy=True)
