import sqlite3
from datetime import datetime, timedelta

import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.security import check_password_hash, generate_password_hash

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="VehicleRent")
app.add_middleware(SessionMiddleware, secret_key="vehicle-rental-secret-key-jain-2024")
app.mount("/static", StaticFiles(directory="static"), name="static")

# cache_size=0 disables Jinja2's LRU template cache to avoid hash errors with
# unhashable context values (dicts/lists) in newer Jinja2/Starlette versions.
templates = Jinja2Templates(env=jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
    cache_size=0,
))

DATABASE = "rental.db"


# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


# ── Session helpers ───────────────────────────────────────────────────────────

def _flash(request: Request, message: str, category: str = "info"):
    request.session.setdefault("_flashes", [])
    request.session["_flashes"].append({"message": message, "category": category})


def ctx(request: Request, **kwargs) -> dict:
    """Build Jinja2 template context: pops flashes, exposes session & url_for."""
    flashes = request.session.pop("_flashes", [])

    def url_for(name: str, **params):
        # Translate Flask-style 'filename' kwarg to FastAPI-style 'path'
        if name == "static" and "filename" in params:
            params["path"] = params.pop("filename")
        return str(request.url_for(name, **params))

    return {
        "request":  request,
        "session":  dict(request.session),
        "flashes":  flashes,
        "url_for":  url_for,
        **kwargs,
    }


# ── Auth guards ───────────────────────────────────────────────────────────────

def _require_login(request: Request):
    """Returns a redirect if not logged in, else None."""
    if "user_id" not in request.session:
        _flash(request, "Please login first.", "warning")
        return RedirectResponse(url="/login", status_code=302)


def _require_role(request: Request, *roles):
    """Returns a redirect if user doesn't have required role, else None."""
    if "user_id" not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    if request.session.get("role") not in roles:
        _flash(request, "Access denied.", "danger")
        return RedirectResponse(url="/vehicles", status_code=302)


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.api_route("/", methods=["GET"])
async def index(request: Request):
    return RedirectResponse(url="/vehicles", status_code=302)


@app.api_route("/login", methods=["GET", "POST"])
async def login(request: Request):
    if "user_id" in request.session:
        return RedirectResponse(url="/vehicles", status_code=302)

    if request.method == "POST":
        form     = await request.form()
        email    = str(form.get("email", "")).strip()
        password = str(form.get("password", ""))

        db   = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.close()

        if user and check_password_hash(user["password_hash"], password):
            request.session["user_id"] = user["id"]
            request.session["name"]    = user["name"]
            request.session["role"]    = user["role"]
            _flash(request, f'Welcome back, {user["name"]}!', "success")
            if user["role"] == "admin":
                return RedirectResponse(url="/admin/dashboard", status_code=302)
            if user["role"] == "fleet_manager":
                return RedirectResponse(url="/fleet/dashboard", status_code=302)
            return RedirectResponse(url="/vehicles", status_code=302)

        _flash(request, "Invalid email or password.", "danger")

    return templates.TemplateResponse(request, "login.html", ctx(request))


@app.api_route("/signup", methods=["GET", "POST"])
async def signup(request: Request):
    if "user_id" in request.session:
        return RedirectResponse(url="/vehicles", status_code=302)

    if request.method == "POST":
        form        = await request.form()
        name        = str(form.get("name", "")).strip()
        email       = str(form.get("email", "")).strip()
        pw          = str(form.get("password", ""))
        license_num = str(form.get("driving_license", "")).strip()

        db = get_db()
        if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            _flash(request, "Email already registered.", "danger")
            db.close()
            return templates.TemplateResponse(request, "signup.html", ctx(request))

        db.execute(
            "INSERT INTO users (name, email, password_hash, role, driving_license) VALUES (?, ?, ?, ?, ?)",
            (name, email, generate_password_hash(pw, method="pbkdf2:sha256"), "customer", license_num),
        )
        db.commit()
        db.close()
        _flash(request, "Account created! Please login.", "success")
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(request, "signup.html", ctx(request))


@app.api_route("/logout", methods=["GET"])
async def logout(request: Request):
    request.session.clear()
    _flash(request, "Logged out successfully.", "info")
    return RedirectResponse(url="/login", status_code=302)


# ── Vehicle listing & detail ──────────────────────────────────────────────────

@app.api_route("/vehicles", methods=["GET"])
async def vehicles(request: Request):
    qp             = request.query_params
    vtype          = qp.get("type", "")
    fuel           = qp.get("fuel", "")
    seats          = qp.get("seats", "")
    max_price      = qp.get("max_price", "")
    available_only = qp.get("available_only", "")

    query  = "SELECT * FROM vehicles WHERE 1=1"
    params = []

    if vtype:
        query += " AND type = ?";                params.append(vtype)
    if fuel:
        query += " AND fuel_type = ?";           params.append(fuel)
    if seats:
        query += " AND seating_capacity >= ?";   params.append(int(seats))
    if max_price:
        query += " AND price_per_day <= ?";      params.append(float(max_price))
    if available_only:
        query += ' AND availability_status = "available"'

    db = get_db()
    vehicles_list = db.execute(query, params).fetchall()
    db.close()

    filters = dict(type=vtype, fuel=fuel, seats=seats,
                   max_price=max_price, available_only=available_only)
    return templates.TemplateResponse(request, "vehicles.html",
                                      ctx(request, vehicles=vehicles_list, filters=filters))


@app.api_route("/vehicles/{vid}", methods=["GET"])
async def vehicle_detail(request: Request, vid: int):
    db      = get_db()
    vehicle = db.execute("SELECT * FROM vehicles WHERE id = ?", (vid,)).fetchone()
    db.close()
    if not vehicle:
        _flash(request, "Vehicle not found.", "danger")
        return RedirectResponse(url="/vehicles", status_code=302)
    return templates.TemplateResponse(request, "vehicle_detail.html", ctx(request, vehicle=vehicle))


# ── Pricing engine ────────────────────────────────────────────────────────────

def _calculate_cost(vehicle, start_dt, end_dt, pricing_rules,
                    rental_type="daily", discount_percent=0.0):
    duration_hours = (end_dt - start_dt).total_seconds() / 3600

    if rental_type == "hourly":
        base_cost      = vehicle["price_per_hour"] * duration_hours
        duration_label = f"{duration_hours:.1f} hour(s)"
    else:
        duration_days  = max(1, duration_hours / 24)
        base_cost      = vehicle["price_per_day"] * duration_days
        duration_label = f"{duration_days:.1f} day(s)"

    total = base_cost
    for rule in pricing_rules:
        if rule["rule_type"] == "weekend":
            if start_dt.weekday() >= 5 or end_dt.weekday() >= 5:
                total *= rule["multiplier"]
        elif rule["rule_type"] == "seasonal":
            if start_dt.month in (6, 7, 8, 12):
                total *= rule["multiplier"]

    discount_amount = 0.0
    if discount_percent > 0:
        discount_amount = round(total * discount_percent / 100, 2)
        total          -= discount_amount

    return round(total, 2), duration_label, round(discount_amount, 2)


# ── Booking ───────────────────────────────────────────────────────────────────

@app.api_route("/book/{vid}", methods=["GET", "POST"])
async def book_vehicle(request: Request, vid: int):
    if (r := _require_login(request)):
        return r
    if request.session.get("role") != "customer":
        _flash(request, "Only customers can book vehicles.", "danger")
        return RedirectResponse(url="/vehicles", status_code=302)

    db      = get_db()
    vehicle = db.execute("SELECT * FROM vehicles WHERE id = ?", (vid,)).fetchone()

    if not vehicle:
        _flash(request, "Vehicle not found.", "danger")
        db.close()
        return RedirectResponse(url="/vehicles", status_code=302)

    if vehicle["availability_status"] != "available":
        _flash(request, "This vehicle is currently not available.", "danger")
        db.close()
        return RedirectResponse(url="/vehicles", status_code=302)

    if request.method == "POST":
        form         = await request.form()
        start_str    = str(form.get("start_datetime", ""))
        end_str      = str(form.get("end_datetime", ""))
        payment_mode = str(form.get("payment_mode", "cash"))
        rental_type  = str(form.get("rental_type", "daily"))
        coupon_code  = str(form.get("coupon_code", "")).strip().upper()

        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M")
            end_dt   = datetime.strptime(end_str,   "%Y-%m-%dT%H:%M")
        except ValueError:
            _flash(request, "Invalid date format.", "danger")
            db.close()
            return templates.TemplateResponse(request, "booking.html", ctx(request, vehicle=vehicle))

        if end_dt <= start_dt:
            _flash(request, "Return date/time must be after pickup.", "danger")
            db.close()
            return templates.TemplateResponse(request, "booking.html", ctx(request, vehicle=vehicle))

        # Validate coupon
        discount_percent  = 0.0
        valid_coupon_code = ""
        if coupon_code:
            coupon = db.execute(
                "SELECT * FROM coupons WHERE code = ? AND is_active = 1", (coupon_code,)
            ).fetchone()
            if coupon:
                discount_percent  = coupon["discount_percent"]
                valid_coupon_code = coupon_code
                _flash(request, f'Coupon "{coupon_code}" applied — {discount_percent:.0f}% off!', "info")
            else:
                _flash(request, f'Coupon "{coupon_code}" is invalid or expired.', "warning")

        pricing_rules = db.execute("SELECT * FROM pricing_rules").fetchall()
        total_cost, duration_label, discount_amount = _calculate_cost(
            vehicle, start_dt, end_dt, pricing_rules, rental_type, discount_percent
        )

        cursor = db.execute(
            """INSERT INTO rental_bookings
               (customer_id, vehicle_id, rental_type, start_datetime, end_datetime,
                total_cost, coupon_code, discount_amount, payment_mode, payment_status, rental_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (request.session["user_id"], vid, rental_type, start_str, end_str,
             total_cost, valid_coupon_code, discount_amount,
             payment_mode, "pending", "booked"),
        )
        booking_id = cursor.lastrowid
        db.execute('UPDATE vehicles SET availability_status = "rented" WHERE id = ?', (vid,))
        db.commit()
        db.close()

        _flash(request, f"Booking confirmed! {duration_label} — Total: Rs.{total_cost:.2f}", "success")
        return RedirectResponse(url=f"/payment/{booking_id}", status_code=302)

    db.close()
    return templates.TemplateResponse(request, "booking.html", ctx(request, vehicle=vehicle))


@app.api_route("/payment/{booking_id}", methods=["GET", "POST"])
async def payment(request: Request, booking_id: int):
    if (r := _require_login(request)):
        return r

    db = get_db()
    booking = db.execute(
        """SELECT rb.*, v.brand, v.model, v.type, v.price_per_day, v.price_per_hour
           FROM rental_bookings rb
           JOIN vehicles v ON rb.vehicle_id = v.id
           WHERE rb.id = ? AND rb.customer_id = ?""",
        (booking_id, request.session["user_id"]),
    ).fetchone()

    if not booking:
        _flash(request, "Booking not found.", "danger")
        db.close()
        return RedirectResponse(url="/my-rentals", status_code=302)

    if request.method == "POST":
        form = await request.form()
        payment_mode = booking["payment_mode"]
        error = None

        if payment_mode == "card":
            card_number = str(form.get("card_number", "")).replace(" ", "").replace("-", "")
            expiry      = str(form.get("expiry", "")).strip()
            cvv         = str(form.get("cvv", "")).strip()
            if not card_number.isdigit() or len(card_number) != 16:
                error = "Enter a valid 16-digit card number."
            elif not (len(expiry) == 5 and expiry[2] == "/" and expiry[:2].isdigit() and expiry[3:].isdigit()
                      and 1 <= int(expiry[:2]) <= 12):
                error = "Enter expiry in MM/YY format."
            elif not (cvv.isdigit() and len(cvv) == 3):
                error = "Enter a valid 3-digit CVV."
        elif payment_mode == "upi":
            upi_id = str(form.get("upi_id", "")).strip()
            if "@" not in upi_id or len(upi_id) < 3:
                error = "Enter a valid UPI ID (e.g. name@upi)."
        elif payment_mode == "netbanking":
            bank = str(form.get("bank", "")).strip()
            if not bank:
                error = "Please select a bank."

        if error:
            _flash(request, error, "danger")
            db.close()
            return RedirectResponse(url=f"/payment/{booking_id}", status_code=302)

        db.execute(
            'UPDATE rental_bookings SET payment_status = "paid" WHERE id = ?', (booking_id,)
        )
        db.commit()
        db.close()
        _flash(request, "Payment successful! Your rental is confirmed.", "success")
        return RedirectResponse(url="/my-rentals", status_code=302)

    db.close()
    return templates.TemplateResponse(request, "payment.html", ctx(request, booking=booking))


@app.api_route("/my-rentals", methods=["GET"])
async def my_rentals(request: Request):
    if (r := _require_login(request)):
        return r

    db = get_db()
    rentals = db.execute(
        """SELECT rb.*, v.brand, v.model, v.type, v.fuel_type, v.price_per_day, v.price_per_hour
           FROM rental_bookings rb
           JOIN vehicles v ON rb.vehicle_id = v.id
           WHERE rb.customer_id = ?
           ORDER BY rb.id DESC""",
        (request.session["user_id"],),
    ).fetchall()
    db.close()
    return templates.TemplateResponse(request, "my_rentals.html", ctx(request, rentals=rentals))


@app.api_route("/rentals/{rid}/extend", methods=["POST"])
async def extend_rental(request: Request, rid: int):
    if (r := _require_login(request)):
        return r

    db     = get_db()
    rental = db.execute(
        "SELECT * FROM rental_bookings WHERE id = ? AND customer_id = ?",
        (rid, request.session["user_id"]),
    ).fetchone()

    if not rental or rental["rental_status"] not in ("booked", "picked_up"):
        _flash(request, "Cannot extend this rental.", "danger")
        db.close()
        return RedirectResponse(url="/my-rentals", status_code=302)

    form        = await request.form()
    extra_units = max(1, int(form.get("extra_units", 1)))
    vehicle     = db.execute("SELECT * FROM vehicles WHERE id = ?", (rental["vehicle_id"],)).fetchone()
    current_end = datetime.strptime(rental["end_datetime"], "%Y-%m-%dT%H:%M")

    if rental["rental_type"] == "hourly":
        new_end    = current_end + timedelta(hours=extra_units)
        extra_cost = vehicle["price_per_hour"] * extra_units
        unit_label = f"{extra_units} hour(s)"
    else:
        new_end    = current_end + timedelta(days=extra_units)
        extra_cost = vehicle["price_per_day"] * extra_units
        unit_label = f"{extra_units} day(s)"

    extra_cost = round(extra_cost, 2)
    db.execute(
        "UPDATE rental_bookings SET end_datetime = ?, total_cost = total_cost + ? WHERE id = ?",
        (new_end.strftime("%Y-%m-%dT%H:%M"), extra_cost, rid),
    )
    db.commit()
    db.close()
    _flash(request, f"Rental extended by {unit_label}. Extra charge: Rs.{extra_cost:.2f}", "success")
    return RedirectResponse(url="/my-rentals", status_code=302)


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.api_route("/admin/dashboard", methods=["GET"])
async def admin_dashboard(request: Request):
    if (r := _require_role(request, "admin")):
        return r

    db = get_db()
    stats = {
        "total_vehicles": db.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0],
        "available":      db.execute(
            'SELECT COUNT(*) FROM vehicles WHERE availability_status = "available"').fetchone()[0],
        "active_rentals": db.execute(
            'SELECT COUNT(*) FROM rental_bookings WHERE rental_status IN ("booked","picked_up")').fetchone()[0],
        "total_revenue":  db.execute(
            'SELECT COALESCE(SUM(total_cost),0) FROM rental_bookings WHERE payment_status = "paid"').fetchone()[0],
    }
    recent = db.execute(
        """SELECT rb.*, u.name AS customer_name, v.brand, v.model
           FROM rental_bookings rb
           JOIN users u ON rb.customer_id = u.id
           JOIN vehicles v ON rb.vehicle_id = v.id
           ORDER BY rb.id DESC LIMIT 10"""
    ).fetchall()
    db.close()
    return templates.TemplateResponse(request, "admin_dashboard.html",
                                      ctx(request, stats=stats, recent_bookings=recent))


@app.api_route("/admin/vehicles", methods=["GET", "POST"])
async def admin_vehicles(request: Request):
    if (r := _require_role(request, "admin")):
        return r

    db = get_db()
    if request.method == "POST":
        form   = await request.form()
        action = form.get("action")
        if action == "add":
            db.execute(
                """INSERT INTO vehicles
                   (type, brand, model, fuel_type, seating_capacity,
                    price_per_hour, price_per_day, availability_status,
                    registration_details, fitness_expiry, insurance_expiry, photo_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, "available", ?, ?, ?, ?)""",
                (form.get("type"), form.get("brand"), form.get("model"),
                 form.get("fuel_type"), int(form.get("seating_capacity", 1)),
                 float(form.get("price_per_hour", 0)), float(form.get("price_per_day", 0)),
                 form.get("registration_details", ""), form.get("fitness_expiry", ""),
                 form.get("insurance_expiry", ""), form.get("photo_path", "")),
            )
            db.commit()
            _flash(request, "Vehicle added successfully.", "success")
        elif action == "delete":
            db.execute("DELETE FROM vehicles WHERE id = ?", (int(form.get("vehicle_id", 0)),))
            db.commit()
            _flash(request, "Vehicle removed.", "success")

    vehicles_list = db.execute("SELECT * FROM vehicles ORDER BY brand, model").fetchall()
    db.close()
    return templates.TemplateResponse(request, "admin_vehicles.html", ctx(request, vehicles=vehicles_list))


@app.api_route("/admin/pricing", methods=["GET", "POST"])
async def admin_pricing(request: Request):
    if (r := _require_role(request, "admin")):
        return r

    db = get_db()
    if request.method == "POST":
        form = await request.form()
        db.execute(
            "UPDATE pricing_rules SET multiplier = ? WHERE id = ?",
            (float(form.get("multiplier", 1.0)), int(form.get("rule_id", 0))),
        )
        db.commit()
        _flash(request, "Pricing rule updated.", "success")

    rules = db.execute("SELECT * FROM pricing_rules").fetchall()
    db.close()
    return templates.TemplateResponse(request, "admin_pricing.html", ctx(request, rules=rules))


@app.api_route("/admin/coupons", methods=["GET", "POST"])
async def admin_coupons(request: Request):
    if (r := _require_role(request, "admin")):
        return r

    db = get_db()
    if request.method == "POST":
        form   = await request.form()
        action = form.get("action")
        if action == "add":
            code = str(form.get("code", "")).strip().upper()
            pct  = float(form.get("discount_percent", 0))
            desc = str(form.get("description", "")).strip()
            if db.execute("SELECT id FROM coupons WHERE code = ?", (code,)).fetchone():
                _flash(request, f'Coupon code "{code}" already exists.', "danger")
            else:
                db.execute(
                    "INSERT INTO coupons (code, discount_percent, description, is_active) VALUES (?, ?, ?, 1)",
                    (code, pct, desc),
                )
                db.commit()
                _flash(request, f"Coupon {code} added.", "success")
        elif action == "toggle":
            cid = int(form.get("coupon_id", 0))
            db.execute("UPDATE coupons SET is_active = 1 - is_active WHERE id = ?", (cid,))
            db.commit()
            _flash(request, "Coupon status toggled.", "success")
        elif action == "delete":
            cid = int(form.get("coupon_id", 0))
            db.execute("DELETE FROM coupons WHERE id = ?", (cid,))
            db.commit()
            _flash(request, "Coupon deleted.", "success")

    coupons = db.execute("SELECT * FROM coupons ORDER BY id DESC").fetchall()
    db.close()
    return templates.TemplateResponse(request, "admin_coupons.html", ctx(request, coupons=coupons))


# ── Fleet Manager ─────────────────────────────────────────────────────────────

@app.api_route("/fleet/dashboard", methods=["GET"])
async def fleet_dashboard(request: Request):
    if (r := _require_role(request, "fleet_manager", "admin")):
        return r

    db = get_db()
    vehicles_list = db.execute("SELECT * FROM vehicles ORDER BY brand, model").fetchall()
    logs = db.execute(
        """SELECT ml.*, v.brand, v.model
           FROM maintenance_logs ml
           JOIN vehicles v ON ml.vehicle_id = v.id
           ORDER BY ml.id DESC LIMIT 20"""
    ).fetchall()
    active_rentals = db.execute(
        """SELECT rb.*, u.name AS customer_name, v.brand, v.model
           FROM rental_bookings rb
           JOIN users u ON rb.customer_id = u.id
           JOIN vehicles v ON rb.vehicle_id = v.id
           WHERE rb.rental_status IN ("booked","picked_up")
           ORDER BY rb.id DESC"""
    ).fetchall()
    db.close()
    return templates.TemplateResponse(
        request, "fleet_dashboard.html",
        ctx(request, vehicles=vehicles_list, maintenance_logs=logs, active_rentals=active_rentals),
    )


@app.api_route("/fleet/vehicles/{vid}/availability", methods=["POST"])
async def update_availability(request: Request, vid: int):
    if (r := _require_role(request, "fleet_manager", "admin")):
        return r

    form   = await request.form()
    status = str(form.get("status", ""))
    if status not in ("available", "under_maintenance", "rented"):
        _flash(request, "Invalid status.", "danger")
        return RedirectResponse(url="/fleet/dashboard", status_code=302)

    db = get_db()
    db.execute("UPDATE vehicles SET availability_status = ? WHERE id = ?", (status, vid))
    db.commit()
    db.close()
    _flash(request, "Availability updated.", "success")
    return RedirectResponse(url="/fleet/dashboard", status_code=302)


@app.api_route("/fleet/vehicles/{vid}/photo", methods=["POST"])
async def update_vehicle_photo(request: Request, vid: int):
    if (r := _require_role(request, "fleet_manager", "admin")):
        return r

    form       = await request.form()
    photo_path = str(form.get("photo_path", "")).strip()
    db = get_db()
    db.execute("UPDATE vehicles SET photo_path = ? WHERE id = ?", (photo_path, vid))
    db.commit()
    db.close()
    _flash(request, "Vehicle photo updated.", "success")
    return RedirectResponse(url="/fleet/dashboard", status_code=302)


@app.api_route("/fleet/maintenance", methods=["POST"])
async def log_maintenance(request: Request):
    if (r := _require_role(request, "fleet_manager", "admin")):
        return r

    form = await request.form()
    db   = get_db()
    db.execute(
        """INSERT INTO maintenance_logs
           (vehicle_id, maintenance_type, description, cost, log_date, next_due_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (int(form.get("vehicle_id", 0)), str(form.get("maintenance_type", "")),
         str(form.get("description", "")), float(form.get("cost", 0)),
         datetime.now().strftime("%Y-%m-%d"), str(form.get("next_due_date", ""))),
    )
    db.commit()
    db.close()
    _flash(request, "Maintenance log added.", "success")
    return RedirectResponse(url="/fleet/dashboard", status_code=302)


@app.api_route("/rentals/{rid}/pickup", methods=["POST"])
async def pickup_rental(request: Request, rid: int):
    if (r := _require_role(request, "fleet_manager", "admin")):
        return r

    db = get_db()
    db.execute(
        'UPDATE rental_bookings SET rental_status = "picked_up" WHERE id = ? AND rental_status = "booked"',
        (rid,),
    )
    db.commit()
    db.close()
    _flash(request, "Vehicle marked as picked up.", "success")
    return RedirectResponse(url="/fleet/dashboard", status_code=302)


@app.api_route("/rentals/{rid}/return", methods=["POST"])
async def return_rental(request: Request, rid: int):
    if (r := _require_role(request, "fleet_manager", "admin")):
        return r

    db     = get_db()
    rental = db.execute("SELECT * FROM rental_bookings WHERE id = ?", (rid,)).fetchone()
    if rental:
        end_dt     = datetime.strptime(rental["end_datetime"], "%Y-%m-%dT%H:%M")
        now        = datetime.now()
        extra_cost = 0.0

        if now > end_dt:
            vehicle = db.execute("SELECT * FROM vehicles WHERE id = ?", (rental["vehicle_id"],)).fetchone()
            if rental["rental_type"] == "hourly":
                late_hours = (now - end_dt).total_seconds() / 3600
                extra_cost = round(vehicle["price_per_hour"] * late_hours * 1.5, 2)
            else:
                late_days  = max(1, (now - end_dt).total_seconds() / 86400)
                extra_cost = round(vehicle["price_per_day"] * late_days * 0.5, 2)
            db.execute(
                "UPDATE rental_bookings SET total_cost = total_cost + ? WHERE id = ?", (extra_cost, rid)
            )

        db.execute('UPDATE rental_bookings SET rental_status = "returned" WHERE id = ?', (rid,))
        db.execute('UPDATE vehicles SET availability_status = "available" WHERE id = ?', (rental["vehicle_id"],))
        db.commit()

        if extra_cost > 0:
            _flash(request, f"Vehicle returned. Late fee: Rs.{extra_cost:.2f}", "warning")
        else:
            _flash(request, "Vehicle returned successfully.", "success")

    db.close()
    return RedirectResponse(url="/fleet/dashboard", status_code=302)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
