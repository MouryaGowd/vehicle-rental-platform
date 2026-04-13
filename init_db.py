import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

DATABASE = 'rental.db'


def init_db():
    db = sqlite3.connect(DATABASE)

    db.executescript('''
        DROP TABLE IF EXISTS maintenance_logs;
        DROP TABLE IF EXISTS rental_bookings;
        DROP TABLE IF EXISTS coupons;
        DROP TABLE IF EXISTS pricing_rules;
        DROP TABLE IF EXISTS vehicles;
        DROP TABLE IF EXISTS users;

        CREATE TABLE users (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL,
            email            TEXT    UNIQUE NOT NULL,
            password_hash    TEXT    NOT NULL,
            role             TEXT    NOT NULL DEFAULT 'customer',
            driving_license  TEXT
        );

        CREATE TABLE vehicles (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            type                 TEXT    NOT NULL,
            brand                TEXT    NOT NULL,
            model                TEXT    NOT NULL,
            fuel_type            TEXT    NOT NULL,
            seating_capacity     INTEGER NOT NULL,
            price_per_hour       REAL    NOT NULL,
            price_per_day        REAL    NOT NULL,
            availability_status  TEXT    NOT NULL DEFAULT 'available',
            registration_details TEXT,
            fitness_expiry       TEXT,
            insurance_expiry     TEXT,
            photo_path           TEXT
        );

        CREATE TABLE rental_bookings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id     INTEGER NOT NULL,
            vehicle_id      INTEGER NOT NULL,
            rental_type     TEXT    NOT NULL DEFAULT 'daily',
            start_datetime  TEXT    NOT NULL,
            end_datetime    TEXT    NOT NULL,
            total_cost      REAL    NOT NULL,
            coupon_code     TEXT    DEFAULT '',
            discount_amount REAL    NOT NULL DEFAULT 0,
            payment_mode    TEXT    NOT NULL,
            payment_status  TEXT    NOT NULL DEFAULT 'pending',
            rental_status   TEXT    NOT NULL DEFAULT 'booked',
            FOREIGN KEY (customer_id) REFERENCES users(id),
            FOREIGN KEY (vehicle_id)  REFERENCES vehicles(id)
        );

        CREATE TABLE maintenance_logs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id       INTEGER NOT NULL,
            maintenance_type TEXT    NOT NULL,
            description      TEXT,
            cost             REAL    NOT NULL,
            log_date         TEXT    NOT NULL,
            next_due_date    TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        );

        CREATE TABLE pricing_rules (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_type   TEXT NOT NULL,
            multiplier  REAL NOT NULL DEFAULT 1.0,
            description TEXT
        );

        CREATE TABLE coupons (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            code             TEXT UNIQUE NOT NULL,
            discount_percent REAL NOT NULL,
            description      TEXT,
            is_active        INTEGER NOT NULL DEFAULT 1
        );
    ''')

    # ── Users ────────────────────────────────────────────────────────────────
    users = [
        ('Admin User',    'admin@rental.com', generate_password_hash('admin123',    method='pbkdf2:sha256'), 'admin',         None),
        ('Fleet Manager', 'fleet@rental.com', generate_password_hash('fleet123',    method='pbkdf2:sha256'), 'fleet_manager', None),
        ('John Customer', 'john@example.com', generate_password_hash('customer123', method='pbkdf2:sha256'), 'customer',      'DL-12345678'),
        ('Jane Doe',      'jane@example.com', generate_password_hash('customer123', method='pbkdf2:sha256'), 'customer',      'DL-87654321'),
    ]
    db.executemany(
        'INSERT INTO users (name, email, password_hash, role, driving_license) VALUES (?, ?, ?, ?, ?)',
        users
    )

    # ── Vehicles ─────────────────────────────────────────────────────────────
    # columns: type, brand, model, fuel, seats, price/hr, price/day, status, reg, fit_exp, ins_exp, photo
    vehicles = [
        ('car',  'Toyota',        'Innova Crysta', 'petrol',   7,  200.0, 3500.0, 'available',         'MH-01-AB-1234', '2025-12-31', '2025-06-30', ''),
        ('car',  'Maruti',        'Swift Dzire',   'petrol',   5,  100.0, 1500.0, 'available',         'MH-02-CD-5678', '2025-11-30', '2025-08-31', ''),
        ('suv',  'Mahindra',      'Scorpio N',     'diesel',   7,  250.0, 4500.0, 'available',         'MH-03-EF-9012', '2026-01-31', '2025-07-31', ''),
        ('bike', 'Royal Enfield', 'Classic 350',   'petrol',   2,   60.0,  800.0, 'available',         'MH-04-GH-3456', '2025-10-31', '2025-09-30', ''),
        ('van',  'Force',         'Traveller',     'diesel',  12,  300.0, 5000.0, 'available',         'MH-05-IJ-7890', '2025-09-30', '2025-05-31', ''),
        ('car',  'Hyundai',       'Creta',         'petrol',   5,  160.0, 2800.0, 'available',         'MH-06-KL-1234', '2026-03-31', '2025-11-30', ''),
        ('suv',  'Tata',          'Nexon EV',      'electric', 5,  180.0, 3200.0, 'available',         'MH-07-MN-5678', '2026-06-30', '2026-01-31', ''),
        ('car',  'Honda',         'City',          'petrol',   5,  120.0, 2000.0, 'under_maintenance', 'MH-08-OP-9012', '2025-08-31', '2025-04-30', ''),
    ]
    db.executemany(
        '''INSERT INTO vehicles
           (type, brand, model, fuel_type, seating_capacity, price_per_hour, price_per_day,
            availability_status, registration_details, fitness_expiry, insurance_expiry, photo_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        vehicles
    )

    # ── Pricing Rules ─────────────────────────────────────────────────────────
    pricing_rules = [
        ('weekend',     1.2, 'Weekend surcharge — 20% extra when pickup/return falls on weekend'),
        ('seasonal',    1.3, 'Peak season surcharge — 30% extra in Jun-Aug and Dec'),
        ('late_return', 1.5, 'Late return fee — 150% of period rate per overdue period'),
    ]
    db.executemany(
        'INSERT INTO pricing_rules (rule_type, multiplier, description) VALUES (?, ?, ?)',
        pricing_rules
    )

    # ── Coupons ───────────────────────────────────────────────────────────────
    coupons = [
        ('WELCOME10', 10.0, 'New customer welcome — 10% off any booking', 1),
        ('SUMMER20',  20.0, 'Summer special — 20% off',                   1),
        ('VIP15',     15.0, 'VIP customer discount — 15% off',            1),
    ]
    db.executemany(
        'INSERT INTO coupons (code, discount_percent, description, is_active) VALUES (?, ?, ?, ?)',
        coupons
    )

    # ── Maintenance Logs ──────────────────────────────────────────────────────
    today = datetime.now()
    logs = [
        (1, 'oil_change',    'Regular oil change and filter replacement', 2500.0,
         (today - timedelta(days=30)).strftime('%Y-%m-%d'),
         (today + timedelta(days=60)).strftime('%Y-%m-%d')),
        (3, 'tire_rotation', 'All four tires rotated and balanced',       1200.0,
         (today - timedelta(days=15)).strftime('%Y-%m-%d'),
         (today + timedelta(days=90)).strftime('%Y-%m-%d')),
        (8, 'engine_repair', 'Engine overhaul due to overheating',        15000.0,
         today.strftime('%Y-%m-%d'),
         (today + timedelta(days=7)).strftime('%Y-%m-%d')),
    ]
    db.executemany(
        '''INSERT INTO maintenance_logs
           (vehicle_id, maintenance_type, description, cost, log_date, next_due_date)
           VALUES (?, ?, ?, ?, ?, ?)''',
        logs
    )

    db.commit()
    db.close()

    print("Database initialized successfully!")
    print()
    print("  Credentials:")
    print("    Admin:         admin@rental.com  / admin123")
    print("    Fleet Manager: fleet@rental.com  / fleet123")
    print("    Customer:      john@example.com  / customer123")
    print()
    print("  Coupon codes: WELCOME10 (10%)  SUMMER20 (20%)  VIP15 (15%)")


if __name__ == '__main__':
    init_db()
