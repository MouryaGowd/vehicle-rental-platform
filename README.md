# VehicleRent — Vehicle Rental Management Platform

A full-stack vehicle rental platform built with **Python (Flask)** + **SQLite** + **HTML/CSS/JS (Bootstrap 5)**.

---

## Tech Stack

| Layer    | Technology                    |
|----------|-------------------------------|
| Backend  | Python 3.8+ · Flask 3.x       |
| Database | SQLite (built into Python)    |
| Frontend | HTML5 · Bootstrap 5 · Vanilla JS |
| Scripts  | Windows Batch (.bat)          |

---

## Features

### Three User Roles
| Role          | Capabilities                                                             |
|---------------|--------------------------------------------------------------------------|
| **Customer**  | Signup/Login · Browse & filter vehicles · Book (hourly or daily) · Apply coupon · Simulate payment · View & extend rentals |
| **Admin**     | Add/remove vehicles · Configure pricing rules · Manage coupons · Monitor revenue & active rentals |
| **Fleet Mgr** | Update vehicle availability · Log maintenance · Upload vehicle photos · Mark pickup/return |

### Core Features
- Vehicle filtering: type, fuel, seats, price, availability
- Hourly **and** daily rental pricing
- Pricing rules: weekend surcharge, seasonal surcharge, late return fees
- Discount coupons with admin management
- Rental state machine: **Booked → Picked Up → Returned**
- Late return fee auto-calculation on return
- Payment simulation (Cash / Card / UPI / Net Banking)
- Maintenance logging with next-due dates

---

## Running on Windows

### Prerequisites
- **Python 3.8 or higher** — download from https://python.org  
  During installation, **tick "Add Python to PATH"**

### Step 1 — First-time setup (run once)
Double-click **`setup.bat`**

This will:
1. Verify Python is installed
2. Create an isolated virtual environment (`venv/`)
3. Install Flask and dependencies inside the venv
4. Create and seed the SQLite database (`rental.db`)

### Step 2 — Start the server
Double-click **`run.bat`**

Then open your browser and go to:
```
http://localhost:5000
```

Press **Ctrl+C** in the terminal window to stop the server.

---

## Demo Credentials

| Role          | Email                | Password     |
|---------------|----------------------|--------------|
| Admin         | admin@rental.com     | admin123     |
| Fleet Manager | fleet@rental.com     | fleet123     |
| Customer      | john@example.com     | customer123  |

## Demo Coupon Codes

| Code       | Discount |
|------------|----------|
| WELCOME10  | 10% off  |
| SUMMER20   | 20% off  |
| VIP15      | 15% off  |

---

## Project Structure

```
Jain/
├── app.py              # Flask application — all routes & business logic
├── init_db.py          # Database schema creation + seed data
├── requirements.txt    # Python dependencies (Flask, Werkzeug)
├── setup.bat           # Windows: create venv, install deps, init DB
├── run.bat             # Windows: start the Flask server
├── rental.db           # SQLite database (auto-created by setup.bat)
├── static/
│   ├── css/style.css   # Custom styling
│   ├── js/main.js      # Client-side helpers
│   └── images/         # Place vehicle photos here
└── templates/          # Jinja2 HTML templates
    ├── base.html
    ├── login.html · signup.html
    ├── vehicles.html · vehicle_detail.html · booking.html
    ├── payment.html · my_rentals.html
    ├── admin_dashboard.html · admin_vehicles.html
    ├── admin_pricing.html · admin_coupons.html
    └── fleet_dashboard.html
```

---

## Database Schema

| Table              | Key Fields                                                         |
|--------------------|---------------------------------------------------------------------|
| `users`            | id, name, email, password_hash, role, driving_license              |
| `vehicles`         | id, type, brand, model, fuel_type, seats, price_per_hour, price_per_day, status, registration, fitness_expiry, insurance_expiry, photo_path |
| `rental_bookings`  | id, customer_id, vehicle_id, rental_type, start/end_datetime, total_cost, coupon_code, discount_amount, payment_mode/status, rental_status |
| `maintenance_logs` | id, vehicle_id, maintenance_type, description, cost, log_date, next_due_date |
| `pricing_rules`    | id, rule_type (weekend/seasonal/late_return), multiplier, description |
| `coupons`          | id, code, discount_percent, description, is_active                 |

---

## Pricing Logic

```
Base Cost = price_per_hour × hours   (hourly rental)
          = price_per_day  × days    (daily rental, min 1 day)

Apply weekend multiplier  if pickup or return is on Sat/Sun
Apply seasonal multiplier if month is Jun, Jul, Aug, or Dec
Apply coupon discount     if a valid coupon code is entered
Apply late return fee     at 150% hourly / 50% daily rate per overdue period
```

---

## Adding Vehicle Photos

Place any `.jpg` or `.png` image in `static/images/` and enter the filename
(e.g. `innova.jpg`) when adding a vehicle as Admin or updating via Fleet Dashboard.

---

## End-to-End Demo Flow

```
Login (Customer) → Browse Vehicles → Filter → View Details
→ Book (choose Daily/Hourly, enter coupon) → Payment Simulation
→ My Rentals (view status, extend)

Login (Fleet) → Fleet Dashboard → Mark Pickup → Mark Return
→ Log Maintenance → Update Availability

Login (Admin) → Dashboard (stats) → Manage Vehicles (add/delete)
→ Pricing Rules (adjust multipliers) → Coupons (add/toggle/delete)
```
