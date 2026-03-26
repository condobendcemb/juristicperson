from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template, abort
from models import db, Juristic, Room, Customer, RoomResident, Income, Record, ArHeader, RcHeader

juristic_bp = Blueprint('juristic', __name__)

@juristic_bp.route('/select-juristic')
def select_juristic():
    if 'user_id' not in session: return redirect(url_for('auth.index'))
    juristics = Juristic.query.all()
    return render_template('select_juristic.html', juristics=juristics)

@juristic_bp.route('/choose-project/<int:j_id>')
def choose_project(j_id):
    juristic = Juristic.query.get(j_id)
    if juristic:
        session['juristic_id'] = j_id
        session['juristic_name'] = juristic.name
        return redirect(url_for('juristic.dashboard'))
    abort(404)

@juristic_bp.route('/dashboard')
def dashboard():
    j_id = session.get('juristic_id')
    if not j_id: return redirect(url_for('juristic.select_juristic'))
    
    juristic = Juristic.query.get(j_id)
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    if user_role == 'admin':
        rooms = Room.query.filter_by(juristic_id=j_id).all()
        customers = Customer.query.filter_by(juristic_id=j_id).all()
        incomes = Income.query.filter_by(juristic_id=j_id).all()
        records = Record.query.filter_by(juristic_id=j_id).all()
        ar_headers = ArHeader.query.filter_by(juristic_id=j_id).all()
        rc_headers = RcHeader.query.filter_by(juristic_id=j_id).all()
    else:
        rooms = db.session.query(Room).join(RoomResident).filter(RoomResident.customer_id == user_id, RoomResident.active == True).all()
        customers = [Customer.query.get(user_id)]
        incomes = [] 
        records = [] 
        room_ids = [r.id for r in rooms]
        ar_headers = ArHeader.query.filter(ArHeader.room_id.in_(room_ids)).all()
        rc_headers = RcHeader.query.filter(RcHeader.customer_id == user_id).all()

    return render_template('dashboard.html', 
                           juristic=juristic, 
                           rooms=rooms, 
                           customers=customers,
                           incomes=incomes if user_role == 'admin' else [],
                           records=records if user_role == 'admin' else [],
                           ar_headers=ar_headers,
                           rc_headers=rc_headers)
