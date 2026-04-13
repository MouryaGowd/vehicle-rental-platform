import functools
import sqlite3
from datetime import datetime, timedelta

from flask import (Flask, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'vehicle-rental-secret-key-jain-2024'
DATABASE = 'rental.db'


# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


# ── Auth decorators ───────────────────────────────────────────────────────────

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('vehicles'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('vehicles'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('vehicles'))
    if request.method == 'POST':
        email    = request.form['email'].strip()
        password = request.form['password']
        db   = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        db.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['name']    = user['name']
            session['role']    = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            if user['role'] == 'fleet_manager':
                return redirect(url_for('fleet_dashboard'))
            return redirect(url_for('vehicles'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('vehicles'))
    if request.method == 'POST':
        name        = request.form['name'].strip()
        email       = request.form['email'].strip()
        pw          = request.form['password']
        license_num = request.form['driving_license'].strip()
        db = get_db()
        if db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
            flash('Email already registered.', 'danger')
            db.close()
            return render_template('signup.html')
        db.execute(
            'INSERT INTO users (name, email, password_hash, role, driving_license) VALUES (?, ?, ?, ?, ?)',
            (name, email, generate_password_hash(pw, method='pbkdf2:sha256'), 'customer', license_num)
        )
        db.commit()
        db.close()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


# ── Vehicle listing & detail ──────────────────────────────────────────────────

@app.route('/vehicles')
def vehicles():
    vtype          = request.args.get('type', '')
    fuel           = request.args.get('fuel', '')
    seats          = request.args.get('seats', '')
    max_price      = request.args.get('max_price', '')
    available_only = request.args.get('available_only', '')

    query  = 'SELECT * FROM vehicles WHERE 1=1'
    params = []

    if vtype:
        query += ' AND type = ?';                params.append(vtype)
    if fuel:
        query += ' AND fuel_type = ?';           params.append(fuel)
    if seats:
        query += ' AND seating_capacity >= ?';   params.append(int(seats))
    if max_price:
        query += ' AND price_per_day <= ?';      params.append(float(max_price))
    if available_only:
        query += ' AND availability_status = "available"'

    db = get_db()
    vehicles_list = db.execute(query, params).fetchall()
    db.close()

    filters = dict(type=vtype, fuel=fuel, seats=seats,
                   max_price=max_price, available_only=available_only)
    return render_template('vehicles.html', vehicles=vehicles_list, filters=filters)


@app.route('/vehicles/<int:vid>')
def vehicle_detail(vid):
    db = get_db()
    vehicle = db.execute('SELECT * FROM vehicles WHERE id = ?', (vid,)).fetchone()
    db.close()
    if not vehicle:
        flash('Vehicle not found.', 'danger')
        return redirect(url_for('vehicles'))
    return render_template('vehicle_detail.html', vehicle=vehicle)


# ── Pricing engine ────────────────────────────────────────────────────────────

def _calculate_cost(vehicle, start_dt, end_dt, pricing_rules,
                    rental_type='daily', discount_percent=0.0):
    """
    Returns (total_cost, duration_label, discount_amount).
    rental_type: 'daily' | 'hourly'
    discount_percent: 0-100
    """
    duration_hours = (end_dt - start_dt).total_seconds() / 3600

    if rental_type == 'hourly':
        base_cost      = vehicle['price_per_hour'] * duration_hours
        duration_label = f'{duration_hours:.1f} hour(s)'
    else:
        duration_days  = max(1, duration_hours / 24)
        base_cost      = vehicle['price_per_day'] * duration_days
        duration_label = f'{duration_days:.1f} day(s)'

    total = base_cost
    for rule in pricing_rules:
        if rule['rule_type'] == 'weekend':
            if start_dt.weekday() >= 5 or end_dt.weekday() >= 5:
                total *= rule['multiplier']
        elif rule['rule_type'] == 'seasonal':
            if start_dt.month in (6, 7, 8, 12):
                total *= rule['multiplier']

    discount_amount = 0.0
    if discount_percent > 0:
        discount_amount = round(total * discount_percent / 100, 2)
        total          -= discount_amount

    return round(total, 2), duration_label, round(discount_amount, 2)


# ── Booking ───────────────────────────────────────────────────────────────────

@app.route('/book/<int:vid>', methods=['GET', 'POST'])
@login_required
def book_vehicle(vid):
    if session.get('role') != 'customer':
        flash('Only customers can book vehicles.', 'danger')
        return redirect(url_for('vehicles'))

    db      = get_db()
    vehicle = db.execute('SELECT * FROM vehicles WHERE id = ?', (vid,)).fetchone()

    if not vehicle:
        flash('Vehicle not found.', 'danger')
        db.close()
        return redirect(url_for('vehicles'))

    if vehicle['availability_status'] != 'available':
        flash('This vehicle is currently not available.', 'danger')
        db.close()
        return redirect(url_for('vehicles'))

    if request.method == 'POST':
        start_str    = request.form['start_datetime']
        end_str      = request.form['end_datetime']
        payment_mode = request.form['payment_mode']
        rental_type  = request.form.get('rental_type', 'daily')
        coupon_code  = request.form.get('coupon_code', '').strip().upper()

        try:
            start_dt = datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
            end_dt   = datetime.strptime(end_str,   '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date format.', 'danger')
            db.close()
            return render_template('booking.html', vehicle=vehicle)

        if end_dt <= start_dt:
            flash('Return date/time must be after pickup.', 'danger')
            db.close()
            return render_template('booking.html', vehicle=vehicle)

        # Validate coupon
        discount_percent  = 0.0
        valid_coupon_code = ''
        if coupon_code:
            coupon = db.execute(
                'SELECT * FROM coupons WHERE code = ? AND is_active = 1', (coupon_code,)
            ).fetchone()
            if coupon:
                discount_percent  = coupon['discount_percent']
                valid_coupon_code = coupon_code
                flash(f'Coupon "{coupon_code}" applied — {discount_percent:.0f}% off!', 'info')
            else:
                flash(f'Coupon "{coupon_code}" is invalid or expired.', 'warning')

        pricing_rules = db.execute('SELECT * FROM pricing_rules').fetchall()
        total_cost, duration_label, discount_amount = _calculate_cost(
            vehicle, start_dt, end_dt, pricing_rules, rental_type, discount_percent
        )

        cursor = db.execute(
            '''INSERT INTO rental_bookings
               (customer_id, vehicle_id, rental_type, start_datetime, end_datetime,
                total_cost, coupon_code, discount_amount, payment_mode, payment_status, rental_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (session['user_id'], vid, rental_type, start_str, end_str,
             total_cost, valid_coupon_code, discount_amount,
             payment_mode, 'pending', 'booked')
        )
        booking_id = cursor.lastrowid
        db.execute('UPDATE vehicles SET availability_status = "rented" WHERE id = ?', (vid,))
        db.commit()
        db.close()

        flash(f'Booking confirmed! {duration_label} — Total: Rs.{total_cost:.2f}', 'success')
        return redirect(url_for('payment', booking_id=booking_id))

    db.close()
    return render_template('booking.html', vehicle=vehicle)


@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def payment(booking_id):
    db = get_db()
    booking = db.execute(
        '''SELECT rb.*, v.brand, v.model, v.type, v.price_per_day, v.price_per_hour
           FROM rental_bookings rb
           JOIN vehicles v ON rb.vehicle_id = v.id
           WHERE rb.id = ? AND rb.customer_id = ?''',
        (booking_id, session['user_id'])
    ).fetchone()

    if not booking:
        flash('Booking not found.', 'danger')
        db.close()
        return redirect(url_for('my_rentals'))

    if request.method == 'POST':
        db.execute(
            'UPDATE rental_bookings SET payment_status = "paid" WHERE id = ?', (booking_id,)
        )
        db.commit()
        db.close()
        flash('Payment successful! Your rental is confirmed.', 'success')
        return redirect(url_for('my_rentals'))

    db.close()
    return render_template('payment.html', booking=booking)


@app.route('/my-rentals')
@login_required
def my_rentals():
    db = get_db()
    rentals = db.execute(
        '''SELECT rb.*, v.brand, v.model, v.type, v.fuel_type, v.price_per_day, v.price_per_hour
           FROM rental_bookings rb
           JOIN vehicles v ON rb.vehicle_id = v.id
           WHERE rb.customer_id = ?
           ORDER BY rb.id DESC''',
        (session['user_id'],)
    ).fetchall()
    db.close()
    return render_template('my_rentals.html', rentals=rentals)


@app.route('/rentals/<int:rid>/extend', methods=['POST'])
@login_required
def extend_rental(rid):
    db     = get_db()
    rental = db.execute(
        'SELECT * FROM rental_bookings WHERE id = ? AND customer_id = ?',
        (rid, session['user_id'])
    ).fetchone()

    if not rental or rental['rental_status'] not in ('booked', 'picked_up'):
        flash('Cannot extend this rental.', 'danger')
        db.close()
        return redirect(url_for('my_rentals'))

    vehicle     = db.execute('SELECT * FROM vehicles WHERE id = ?', (rental['vehicle_id'],)).fetchone()
    current_end = datetime.strptime(rental['end_datetime'], '%Y-%m-%dT%H:%M')
    extra_units = max(1, int(request.form.get('extra_units', 1)))

    if rental['rental_type'] == 'hourly':
        new_end    = current_end + timedelta(hours=extra_units)
        extra_cost = vehicle['price_per_hour'] * extra_units
        unit_label = f'{extra_units} hour(s)'
    else:
        new_end    = current_end + timedelta(days=extra_units)
        extra_cost = vehicle['price_per_day'] * extra_units
        unit_label = f'{extra_units} day(s)'

    extra_cost = round(extra_cost, 2)
    db.execute(
        'UPDATE rental_bookings SET end_datetime = ?, total_cost = total_cost + ? WHERE id = ?',
        (new_end.strftime('%Y-%m-%dT%H:%M'), extra_cost, rid)
    )
    db.commit()
    db.close()
    flash(f'Rental extended by {unit_label}. Extra charge: Rs.{extra_cost:.2f}', 'success')
    return redirect(url_for('my_rentals'))


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    db = get_db()
    stats = {
        'total_vehicles': db.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0],
        'available':      db.execute(
            'SELECT COUNT(*) FROM vehicles WHERE availability_status = "available"').fetchone()[0],
        'active_rentals': db.execute(
            'SELECT COUNT(*) FROM rental_bookings WHERE rental_status IN ("booked","picked_up")').fetchone()[0],
        'total_revenue':  db.execute(
            'SELECT COALESCE(SUM(total_cost),0) FROM rental_bookings WHERE payment_status = "paid"').fetchone()[0],
    }
    recent = db.execute(
        '''SELECT rb.*, u.name AS customer_name, v.brand, v.model
           FROM rental_bookings rb
           JOIN users u ON rb.customer_id = u.id
           JOIN vehicles v ON rb.vehicle_id = v.id
           ORDER BY rb.id DESC LIMIT 10'''
    ).fetchall()
    db.close()
    return render_template('admin_dashboard.html', stats=stats, recent_bookings=recent)


@app.route('/admin/vehicles', methods=['GET', 'POST'])
@role_required('admin')
def admin_vehicles():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            db.execute(
                '''INSERT INTO vehicles
                   (type, brand, model, fuel_type, seating_capacity,
                    price_per_hour, price_per_day,
                    availability_status, registration_details,
                    fitness_expiry, insurance_expiry, photo_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, "available", ?, ?, ?, ?)''',
                (request.form['type'], request.form['brand'], request.form['model'],
                 request.form['fuel_type'], int(request.form['seating_capacity']),
                 float(request.form['price_per_hour']), float(request.form['price_per_day']),
                 request.form.get('registration_details', ''),
                 request.form.get('fitness_expiry', ''),
                 request.form.get('insurance_expiry', ''),
                 request.form.get('photo_path', ''))
            )
            db.commit()
            flash('Vehicle added successfully.', 'success')
        elif action == 'delete':
            db.execute('DELETE FROM vehicles WHERE id = ?', (int(request.form['vehicle_id']),))
            db.commit()
            flash('Vehicle removed.', 'success')

    vehicles_list = db.execute('SELECT * FROM vehicles ORDER BY brand, model').fetchall()
    db.close()
    return render_template('admin_vehicles.html', vehicles=vehicles_list)


@app.route('/admin/pricing', methods=['GET', 'POST'])
@role_required('admin')
def admin_pricing():
    db = get_db()
    if request.method == 'POST':
        db.execute(
            'UPDATE pricing_rules SET multiplier = ? WHERE id = ?',
            (float(request.form['multiplier']), int(request.form['rule_id']))
        )
        db.commit()
        flash('Pricing rule updated.', 'success')
    rules = db.execute('SELECT * FROM pricing_rules').fetchall()
    db.close()
    return render_template('admin_pricing.html', rules=rules)


@app.route('/admin/coupons', methods=['GET', 'POST'])
@role_required('admin')
def admin_coupons():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            code = request.form['code'].strip().upper()
            pct  = float(request.form['discount_percent'])
            desc = request.form.get('description', '').strip()
            if db.execute('SELECT id FROM coupons WHERE code = ?', (code,)).fetchone():
                flash(f'Coupon code "{code}" already exists.', 'danger')
            else:
                db.execute(
                    'INSERT INTO coupons (code, discount_percent, description, is_active) VALUES (?, ?, ?, 1)',
                    (code, pct, desc)
                )
                db.commit()
                flash(f'Coupon {code} added.', 'success')
        elif action == 'toggle':
            cid = int(request.form['coupon_id'])
            db.execute('UPDATE coupons SET is_active = 1 - is_active WHERE id = ?', (cid,))
            db.commit()
            flash('Coupon status toggled.', 'success')
        elif action == 'delete':
            cid = int(request.form['coupon_id'])
            db.execute('DELETE FROM coupons WHERE id = ?', (cid,))
            db.commit()
            flash('Coupon deleted.', 'success')

    coupons = db.execute('SELECT * FROM coupons ORDER BY id DESC').fetchall()
    db.close()
    return render_template('admin_coupons.html', coupons=coupons)


# ── Fleet Manager ─────────────────────────────────────────────────────────────

@app.route('/fleet/dashboard')
@role_required('fleet_manager', 'admin')
def fleet_dashboard():
    db = get_db()
    vehicles_list = db.execute('SELECT * FROM vehicles ORDER BY brand, model').fetchall()
    logs = db.execute(
        '''SELECT ml.*, v.brand, v.model
           FROM maintenance_logs ml
           JOIN vehicles v ON ml.vehicle_id = v.id
           ORDER BY ml.id DESC LIMIT 20'''
    ).fetchall()
    active_rentals = db.execute(
        '''SELECT rb.*, u.name AS customer_name, v.brand, v.model
           FROM rental_bookings rb
           JOIN users u ON rb.customer_id = u.id
           JOIN vehicles v ON rb.vehicle_id = v.id
           WHERE rb.rental_status IN ("booked","picked_up")
           ORDER BY rb.id DESC'''
    ).fetchall()
    db.close()
    return render_template('fleet_dashboard.html',
                           vehicles=vehicles_list,
                           maintenance_logs=logs,
                           active_rentals=active_rentals)


@app.route('/fleet/vehicles/<int:vid>/availability', methods=['POST'])
@role_required('fleet_manager', 'admin')
def update_availability(vid):
    status = request.form['status']
    if status not in ('available', 'under_maintenance', 'rented'):
        flash('Invalid status.', 'danger')
        return redirect(url_for('fleet_dashboard'))
    db = get_db()
    db.execute('UPDATE vehicles SET availability_status = ? WHERE id = ?', (status, vid))
    db.commit()
    db.close()
    flash('Availability updated.', 'success')
    return redirect(url_for('fleet_dashboard'))


@app.route('/fleet/vehicles/<int:vid>/photo', methods=['POST'])
@role_required('fleet_manager', 'admin')
def update_vehicle_photo(vid):
    photo_path = request.form.get('photo_path', '').strip()
    db = get_db()
    db.execute('UPDATE vehicles SET photo_path = ? WHERE id = ?', (photo_path, vid))
    db.commit()
    db.close()
    flash('Vehicle photo updated.', 'success')
    return redirect(url_for('fleet_dashboard'))


@app.route('/fleet/maintenance', methods=['POST'])
@role_required('fleet_manager', 'admin')
def log_maintenance():
    db = get_db()
    db.execute(
        '''INSERT INTO maintenance_logs
           (vehicle_id, maintenance_type, description, cost, log_date, next_due_date)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (int(request.form['vehicle_id']), request.form['maintenance_type'],
         request.form.get('description', ''), float(request.form['cost']),
         datetime.now().strftime('%Y-%m-%d'), request.form.get('next_due_date', ''))
    )
    db.commit()
    db.close()
    flash('Maintenance log added.', 'success')
    return redirect(url_for('fleet_dashboard'))


@app.route('/rentals/<int:rid>/pickup', methods=['POST'])
@role_required('fleet_manager', 'admin')
def pickup_rental(rid):
    db = get_db()
    db.execute(
        'UPDATE rental_bookings SET rental_status = "picked_up" WHERE id = ? AND rental_status = "booked"',
        (rid,)
    )
    db.commit()
    db.close()
    flash('Vehicle marked as picked up.', 'success')
    return redirect(url_for('fleet_dashboard'))


@app.route('/rentals/<int:rid>/return', methods=['POST'])
@role_required('fleet_manager', 'admin')
def return_rental(rid):
    db     = get_db()
    rental = db.execute('SELECT * FROM rental_bookings WHERE id = ?', (rid,)).fetchone()
    if rental:
        end_dt     = datetime.strptime(rental['end_datetime'], '%Y-%m-%dT%H:%M')
        now        = datetime.now()
        extra_cost = 0.0

        if now > end_dt:
            vehicle = db.execute('SELECT * FROM vehicles WHERE id = ?', (rental['vehicle_id'],)).fetchone()
            if rental['rental_type'] == 'hourly':
                late_hours = (now - end_dt).total_seconds() / 3600
                extra_cost = round(vehicle['price_per_hour'] * late_hours * 1.5, 2)
            else:
                late_days  = max(1, (now - end_dt).total_seconds() / 86400)
                extra_cost = round(vehicle['price_per_day'] * late_days * 0.5, 2)
            db.execute(
                'UPDATE rental_bookings SET total_cost = total_cost + ? WHERE id = ?', (extra_cost, rid)
            )

        db.execute('UPDATE rental_bookings SET rental_status = "returned" WHERE id = ?', (rid,))
        db.execute('UPDATE vehicles SET availability_status = "available" WHERE id = ?', (rental['vehicle_id'],))
        db.commit()

        if extra_cost > 0:
            flash(f'Vehicle returned. Late fee: Rs.{extra_cost:.2f}', 'warning')
        else:
            flash('Vehicle returned successfully.', 'success')

    db.close()
    return redirect(url_for('fleet_dashboard'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
