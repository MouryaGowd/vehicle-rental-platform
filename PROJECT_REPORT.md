# VehicleRent — Project Report
### Vehicle Rental Management Platform
**Jain University — Database Management Systems Project**

---

## 1. Project Overview

VehicleRent is a full-stack web-based Vehicle Rental Management Platform that enables customers to browse and book vehicles, fleet managers to maintain and track the fleet, and administrators to manage the entire operation from a single dashboard. The system is designed to run locally on Windows with a one-click setup, requiring no external database server or cloud services.

---

## 2. Technologies Used

### 2.1 Backend

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.8+ | Core programming language |
| **FastAPI** | ≥ 0.100.0 | Web framework — async HTTP routing, request/response handling |
| **Uvicorn** | ≥ 0.22.0 | ASGI server — runs the FastAPI application |
| **Starlette** | (bundled with FastAPI) | Middleware layer — session management, static files, routing |
| **Jinja2** | ≥ 3.1.0 | Server-side HTML templating engine |
| **Werkzeug** | ≥ 3.0.0 | Password hashing (`pbkdf2:sha256`) and security utilities |
| **itsdangerous** | ≥ 2.1.0 | Cryptographically signed session cookies |
| **python-multipart** | ≥ 0.0.7 | Parsing HTML form submissions (`multipart/form-data`) |
| **SQLite3** | Built-in (Python stdlib) | Relational database — zero-config, file-based |

### 2.2 Frontend

| Technology | Version | Purpose |
|---|---|---|
| **HTML5** | — | Semantic page structure |
| **Bootstrap** | 5.3.0 (CDN) | Responsive UI components — navbar, cards, tables, modals, badges |
| **Vanilla JavaScript** | ES6 | Live cost preview on booking page, interactive UI helpers |
| **CSS3** | Custom (`style.css`) | Theme overrides, vehicle cards, status badges |

### 2.3 Infrastructure & Tooling

| Tool | Purpose |
|---|---|
| **Windows Batch Scripts** (`.bat`) | One-click setup (`setup.bat`) and server start (`run.bat`) |
| **Python `venv`** | Isolated virtual environment — no system-level package conflicts |
| **Git + GitHub** | Version control and public distribution |

---

## 3. System Architecture

```
Browser (HTTP)
     │
     ▼
Uvicorn (ASGI Server — port 5000)
     │
     ▼
FastAPI Application (app.py)
     ├── SessionMiddleware  ──► Signed cookie sessions (itsdangerous)
     ├── StaticFiles mount  ──► /static → CSS, JS, images
     └── Routes (api_route) ──► async handler functions
              │
              ├── SQLite (rental.db)  ◄── sqlite3 stdlib
              └── Jinja2Templates     ◄── templates/*.html
```

**Request flow:**
1. Browser sends HTTP request to `localhost:5000`
2. Uvicorn receives it and passes to FastAPI middleware stack
3. SessionMiddleware decodes the signed session cookie
4. Route handler runs business logic, queries SQLite via `sqlite3.Row`
5. `ctx()` helper builds template context (session, flashes, url_for)
6. Jinja2 renders the HTML template with the context
7. HTML response is sent back to the browser

---

## 4. Project Structure

```
Jain/
│
├── app.py                  ← FastAPI application — all routes & business logic
│                             ~670 lines covering all 3 roles
│
├── init_db.py              ← Database schema creation + seed data
│                             Creates 6 tables, inserts demo users/vehicles/coupons
│
├── requirements.txt        ← Python dependencies (pip-installable)
│
├── setup.bat               ← Windows: creates venv, installs deps, inits DB
├── run.bat                 ← Windows: starts the FastAPI/Uvicorn server
│
├── rental.db               ← SQLite database (auto-created by setup.bat)
│
├── static/
│   ├── css/
│   │   └── style.css       ← Custom styles (cards, badges, layout tweaks)
│   ├── js/
│   │   └── main.js         ← Live cost preview, UI helpers
│   └── images/             ← Vehicle photos (place .jpg/.png files here)
│
└── templates/              ← Jinja2 HTML templates (extend base.html)
    ├── base.html           ← Shared layout: navbar, flash messages, footer
    ├── login.html          ← Login form
    ├── signup.html         ← Customer registration form
    ├── vehicles.html       ← Vehicle browse & filter page
    ├── vehicle_detail.html ← Single vehicle details page
    ├── booking.html        ← Booking form (daily/hourly, coupon, payment mode)
    ├── payment.html        ← Payment simulation page
    ├── my_rentals.html     ← Customer rental history + extend rental
    ├── admin_dashboard.html    ← Admin stats overview + recent bookings
    ├── admin_vehicles.html     ← Add / delete vehicles
    ├── admin_pricing.html      ← Edit pricing rule multipliers
    ├── admin_coupons.html      ← Add / toggle / delete coupon codes
    └── fleet_dashboard.html    ← Fleet status, maintenance logs, pickup/return
```

---

## 5. Database Schema

### 5.1 Entity-Relationship Summary

```
users ──────────< rental_bookings >──────── vehicles
                                                 │
                                      maintenance_logs
pricing_rules  (standalone)
coupons        (standalone)
```

### 5.2 Table Definitions

**`users`**
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| name | TEXT | Full name |
| email | TEXT UNIQUE | Login identifier |
| password_hash | TEXT | pbkdf2:sha256 hash (Werkzeug) |
| role | TEXT | `customer` / `admin` / `fleet_manager` |
| driving_license | TEXT | Customer driving licence number |

**`vehicles`**
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| type | TEXT | `car` / `suv` / `bike` / `van` |
| brand | TEXT | Manufacturer (e.g. Toyota) |
| model | TEXT | Model name (e.g. Innova Crysta) |
| fuel_type | TEXT | `petrol` / `diesel` / `electric` |
| seating_capacity | INTEGER | Number of seats |
| price_per_hour | REAL | Hourly rental rate (Rs.) |
| price_per_day | REAL | Daily rental rate (Rs.) |
| availability_status | TEXT | `available` / `rented` / `under_maintenance` |
| registration_details | TEXT | Vehicle registration number |
| fitness_expiry | TEXT | Fitness certificate expiry date |
| insurance_expiry | TEXT | Insurance expiry date |
| photo_path | TEXT | Filename in `static/images/` |

**`rental_bookings`**
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| customer_id | INTEGER FK | References `users.id` |
| vehicle_id | INTEGER FK | References `vehicles.id` |
| rental_type | TEXT | `daily` / `hourly` |
| start_datetime | TEXT | Pickup date-time (`YYYY-MM-DDTHH:MM`) |
| end_datetime | TEXT | Return date-time |
| total_cost | REAL | Final cost after surcharges and discounts |
| coupon_code | TEXT | Applied coupon code (empty if none) |
| discount_amount | REAL | Rupee value of coupon discount |
| payment_mode | TEXT | `cash` / `card` / `upi` / `net_banking` |
| payment_status | TEXT | `pending` / `paid` |
| rental_status | TEXT | `booked` → `picked_up` → `returned` |

**`maintenance_logs`**
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| vehicle_id | INTEGER FK | References `vehicles.id` |
| maintenance_type | TEXT | `oil_change` / `tire_rotation` / `engine_repair` etc. |
| description | TEXT | Detailed notes |
| cost | REAL | Service cost (Rs.) |
| log_date | TEXT | Date of service |
| next_due_date | TEXT | Scheduled next service date |

**`pricing_rules`**
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| rule_type | TEXT | `weekend` / `seasonal` / `late_return` |
| multiplier | REAL | Rate multiplier (e.g. 1.2 = 20% surcharge) |
| description | TEXT | Human-readable explanation |

**`coupons`**
| Column | Type | Description |
|---|---|---|
| id | INTEGER PK | Auto-increment primary key |
| code | TEXT UNIQUE | Coupon code (e.g. `WELCOME10`) |
| discount_percent | REAL | Percentage discount (e.g. 10.0) |
| description | TEXT | Description shown to customer |
| is_active | INTEGER | 1 = active, 0 = disabled |

---

## 6. User Roles & Features

### 6.1 Customer
| Feature | How It Works |
|---|---|
| **Signup / Login** | Registration stores name, email, driving licence; password hashed with pbkdf2:sha256 |
| **Browse Vehicles** | `/vehicles` lists all vehicles with filter controls (type, fuel, seats, max price, available only) |
| **Vehicle Detail** | `/vehicles/{id}` shows full specs, pricing, and availability |
| **Book a Vehicle** | `/book/{id}` — choose daily or hourly rental, pick dates, enter coupon code, select payment mode |
| **Coupon Discount** | Validated against `coupons` table; discount applied after surcharges |
| **Payment Simulation** | `/payment/{id}` — confirms payment (Cash / Card / UPI / Net Banking) |
| **My Rentals** | `/my-rentals` — full booking history with status badges |
| **Extend Rental** | POST to `/rentals/{id}/extend` — adds hours or days to an active booking |

### 6.2 Administrator
| Feature | How It Works |
|---|---|
| **Dashboard** | `/admin/dashboard` — total vehicles, available count, active rentals, total revenue |
| **Manage Vehicles** | `/admin/vehicles` — add new vehicles with all specs, or delete existing ones |
| **Pricing Rules** | `/admin/pricing` — adjust weekend / seasonal / late-return multipliers |
| **Coupon Management** | `/admin/coupons` — add new coupons, toggle active/inactive, delete coupons |
| **Fleet View** | Admin can also access Fleet Dashboard for full operational visibility |

### 6.3 Fleet Manager
| Feature | How It Works |
|---|---|
| **Fleet Dashboard** | `/fleet/dashboard` — all vehicles, active rentals, maintenance log |
| **Update Availability** | Change vehicle status to `available` / `under_maintenance` / `rented` |
| **Mark Pickup** | POST to `/rentals/{id}/pickup` — moves rental to `picked_up` state |
| **Mark Return** | POST to `/rentals/{id}/return` — auto-calculates late fees if overdue, marks vehicle `available` |
| **Log Maintenance** | Record maintenance type, description, cost, and next service date |
| **Update Vehicle Photo** | Set `photo_path` to a filename in `static/images/` |

---

## 7. Pricing Logic

```
Base Cost:
  Hourly rental:  price_per_hour × number_of_hours
  Daily rental:   price_per_day  × number_of_days  (minimum 1 day)

Surcharges (applied as multipliers to base cost):
  Weekend:   ×1.2  if pickup OR return falls on Saturday or Sunday
  Seasonal:  ×1.3  if booking month is June, July, August, or December

Coupon Discount:
  discount_amount = subtotal_after_surcharges × (discount_percent / 100)
  final_cost      = subtotal_after_surcharges − discount_amount

Late Return Fee (on vehicle return):
  Hourly rental: price_per_hour × late_hours × 1.5
  Daily rental:  price_per_day  × late_days  × 0.5  (minimum 1 day)
```

---

## 8. Security

| Concern | Implementation |
|---|---|
| **Password storage** | `werkzeug.security.generate_password_hash` with `pbkdf2:sha256` — never stored in plaintext |
| **Session security** | Starlette `SessionMiddleware` with `itsdangerous` — session cookie is HMAC-signed; tampering is detected |
| **Role-based access** | `_require_login()` and `_require_role()` guard every protected route; returns 302 redirect if not authorised |
| **SQL injection** | All database queries use parameterised statements (`?` placeholders) — no string concatenation with user input |
| **Form validation** | Date parsing wrapped in `try/except`; numeric inputs cast with `int()`/`float()` |

---

## 9. API Reference

### 9.1 How FastAPI Routing Works in This Project

All routes are declared with `@app.api_route(path, methods=[...])` which handles both GET and POST on the same URL — matching the traditional HTML form pattern where a page renders on GET and processes the form on POST.

```python
# Example: single function handles GET (show page) and POST (process form)
@app.api_route("/login", methods=["GET", "POST"])
async def login(request: Request):
    if request.method == "POST":
        form = await request.form()   # parses multipart/form-data
        # ... validate and redirect
    return templates.TemplateResponse(request, "login.html", ctx(request))
```

Every handler receives a `Request` object from Starlette. Path parameters (e.g. `vid: int`) are declared in the function signature and FastAPI parses + validates them automatically.

---

### 9.2 Complete API Endpoint Table

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/` | Public | Redirects to `/vehicles` |
| GET | `/login` | Public | Renders login form |
| POST | `/login` | Public | Validates credentials, sets session, redirects by role |
| GET | `/signup` | Public | Renders registration form |
| POST | `/signup` | Public | Creates new customer account, redirects to login |
| GET | `/logout` | Any logged-in | Clears session, redirects to login |
| GET | `/vehicles` | Public | Browse + filter vehicle listing |
| GET | `/vehicles/{vid}` | Public | Vehicle detail page |
| GET | `/book/{vid}` | Customer | Renders booking form for a vehicle |
| POST | `/book/{vid}` | Customer | Creates booking, applies coupon, redirects to payment |
| GET | `/payment/{booking_id}` | Customer | Renders payment confirmation page |
| POST | `/payment/{booking_id}` | Customer | Marks payment as paid, redirects to My Rentals |
| GET | `/my-rentals` | Customer | Lists all rentals for the logged-in customer |
| POST | `/rentals/{rid}/extend` | Customer | Extends an active rental by extra hours/days |
| GET | `/admin/dashboard` | Admin | Stats overview — revenue, active rentals, vehicle count |
| GET | `/admin/vehicles` | Admin | Lists all vehicles |
| POST | `/admin/vehicles` | Admin | Add a new vehicle or delete an existing one (`action` field) |
| GET | `/admin/pricing` | Admin | Lists pricing rules |
| POST | `/admin/pricing` | Admin | Updates a pricing rule multiplier |
| GET | `/admin/coupons` | Admin | Lists all coupons |
| POST | `/admin/coupons` | Admin | Add / toggle / delete a coupon (`action` field) |
| GET | `/fleet/dashboard` | Fleet / Admin | Fleet status, active rentals, maintenance log |
| POST | `/fleet/vehicles/{vid}/availability` | Fleet / Admin | Updates a vehicle's availability status |
| POST | `/fleet/vehicles/{vid}/photo` | Fleet / Admin | Updates the photo filename for a vehicle |
| POST | `/fleet/maintenance` | Fleet / Admin | Logs a maintenance entry for a vehicle |
| POST | `/rentals/{rid}/pickup` | Fleet / Admin | Marks a booking as `picked_up` |
| POST | `/rentals/{rid}/return` | Fleet / Admin | Marks a booking as `returned`, calculates late fees |

---

### 9.3 Request Handling Details

#### Reading Query Parameters (GET filters)
```python
# GET /vehicles?type=car&fuel=petrol&seats=5&max_price=3000&available_only=1
qp             = request.query_params
vtype          = qp.get("type", "")         # "" if not provided
seats          = qp.get("seats", "")
max_price      = qp.get("max_price", "")
available_only = qp.get("available_only", "")
```

#### Reading Form Data (POST actions)
```python
# POST /book/{vid}  with  Content-Type: multipart/form-data
form         = await request.form()          # must be awaited (async)
start_str    = str(form.get("start_datetime", ""))
rental_type  = str(form.get("rental_type", "daily"))
coupon_code  = str(form.get("coupon_code", "")).strip().upper()
payment_mode = str(form.get("payment_mode", "cash"))
```
`python-multipart` must be installed for `await request.form()` to work — it is included in `requirements.txt`.

#### Path Parameters (URL variables)
```python
# GET /vehicles/3  →  vid = 3 (FastAPI validates it's an integer)
@app.api_route("/vehicles/{vid}", methods=["GET"])
async def vehicle_detail(request: Request, vid: int):
    vehicle = db.execute("SELECT * FROM vehicles WHERE id = ?", (vid,)).fetchone()
```

#### Dispatching Multiple Actions on One POST Endpoint
Admin and Fleet routes use a hidden `action` field in the form to dispatch different operations from one endpoint:
```python
# POST /admin/vehicles  with  action=add  or  action=delete
form   = await request.form()
action = form.get("action")   # "add" or "delete"
if action == "add":
    db.execute("INSERT INTO vehicles ...")
elif action == "delete":
    db.execute("DELETE FROM vehicles WHERE id = ?", ...)
```

---

### 9.4 Response Types

#### HTML Page Response (TemplateResponse)
Used for all pages that render HTML:
```python
return templates.TemplateResponse(request, "vehicles.html",
    ctx(request, vehicles=vehicles_list, filters=filters))
```
The `ctx()` helper builds the template context — it pops flash messages from the session, provides a custom `url_for` function, and exposes the session dict so templates can check `session.role`, `session.name`, etc.

#### Redirect Response (Post/Redirect/Get pattern)
After every POST that modifies data, the handler redirects to prevent double-submission on browser refresh:
```python
_flash(request, "Booking confirmed!", "success")
return RedirectResponse(url=f"/payment/{booking_id}", status_code=302)
```
HTTP 302 is used for all redirects (temporary redirect — correct for POST → GET).

---

### 9.5 Session API

Sessions are managed by Starlette's `SessionMiddleware` using signed cookies (`itsdangerous`). The session behaves like a dict:

```python
# Set session values on login
request.session["user_id"] = user["id"]
request.session["name"]    = user["name"]
request.session["role"]    = user["role"]

# Read session values in any route
if request.session.get("role") == "admin":
    ...

# Clear session on logout
request.session.clear()
```

Flash messages are stored as a list inside the session and consumed once by `ctx()`:
```python
def _flash(request, message, category="info"):
    request.session.setdefault("_flashes", [])
    request.session["_flashes"].append({"message": message, "category": category})

# In ctx():
flashes = request.session.pop("_flashes", [])  # consumed — won't show twice
```

---

### 9.6 Database API (sqlite3)

SQLite is accessed via Python's built-in `sqlite3` module. `sqlite3.Row` is set as the row factory so rows behave like dicts:

```python
def get_db():
    db = sqlite3.connect("rental.db")
    db.row_factory = sqlite3.Row   # enables row["column_name"] access
    return db

# Query example — parameterised to prevent SQL injection
vehicle = db.execute(
    "SELECT * FROM vehicles WHERE id = ?", (vid,)
).fetchone()

# Access columns by name
print(vehicle["brand"], vehicle["price_per_day"])

# Insert with commit
db.execute("INSERT INTO rental_bookings (...) VALUES (?, ?, ...)", (...))
db.commit()
db.close()
```

---

### 9.7 Template API (Jinja2)

Templates extend `base.html` and use block inheritance:

```html
<!-- In any child template -->
{% extends "base.html" %}
{% block title %}Browse Vehicles{% endblock %}
{% block content %}
  <!-- page-specific HTML here -->
{% endblock %}
```

**Variables available in every template** (injected by `ctx()`):

| Variable | Type | Usage |
|---|---|---|
| `session` | dict | `session.role`, `session.name`, `session.user_id` |
| `flashes` | list | Iterated to show alert banners |
| `url_for` | function | `url_for('vehicles')`, `url_for('static', filename='css/style.css')` |
| `request` | Request | Available but rarely used directly in templates |

**Conditional rendering by role:**
```html
{% if session.role == 'admin' %}
  <a href="{{ url_for('admin_dashboard') }}">Admin Dashboard</a>
{% endif %}

{% if session.role == 'customer' %}
  <a href="{{ url_for('my_rentals') }}">My Rentals</a>
{% endif %}
```

**Looping over query results:**
```html
{% for vehicle in vehicles %}
  <div class="card">
    <h5>{{ vehicle.brand }} {{ vehicle.model }}</h5>
    <p>Rs.{{ vehicle.price_per_day }}/day</p>
    {% if vehicle.availability_status == 'available' %}
      <a href="{{ url_for('book_vehicle', vid=vehicle.id) }}">Book Now</a>
    {% endif %}
  </div>
{% endfor %}
```

---

### 9.8 Auth Guard API

Two inline guard functions protect routes. They return a `RedirectResponse` if the check fails, or `None` if it passes. The walrus operator (`:=`) makes the pattern concise:

```python
def _require_login(request: Request):
    if "user_id" not in request.session:
        _flash(request, "Please login first.", "warning")
        return RedirectResponse(url="/login", status_code=302)

def _require_role(request: Request, *roles):
    if "user_id" not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    if request.session.get("role") not in roles:
        _flash(request, "Access denied.", "danger")
        return RedirectResponse(url="/vehicles", status_code=302)

# Usage in every protected route:
@app.api_route("/my-rentals", methods=["GET"])
async def my_rentals(request: Request):
    if (r := _require_login(request)): return r
    ...

@app.api_route("/admin/dashboard", methods=["GET"])
async def admin_dashboard(request: Request):
    if (r := _require_role(request, "admin")): return r
    ...

@app.api_route("/fleet/dashboard", methods=["GET"])
async def fleet_dashboard(request: Request):
    if (r := _require_role(request, "fleet_manager", "admin")): return r
    ...
```

---

## 10. How Requirements Are Satisfied

### Requirement: Three User Roles
- **Admin** — full control over vehicles, pricing, coupons, revenue monitoring
- **Fleet Manager** — operational control: availability, maintenance, pickup/return
- **Customer** — browsing, booking, payment, rental history
- Role is stored in the session after login; every protected route checks `session["role"]`

### Requirement: Vehicle Management
- Admin can add vehicles with all required fields: type, brand, model, fuel type, seating capacity, pricing (hourly + daily), registration details, fitness expiry, insurance expiry, and photo
- Admin can delete vehicles
- Fleet Manager can update availability status and upload photo paths

### Requirement: Booking System
- Customers can book with either **hourly** or **daily** pricing
- Booking stores: customer, vehicle, rental type, start/end datetime, total cost, coupon, discount, payment mode, payment status, and rental status
- Rental state machine enforced: `booked → picked_up → returned`

### Requirement: Pricing & Discounts
- Weekend surcharge (20%), seasonal surcharge (30%), and late return fee (50–150%) are stored as configurable multipliers in the database
- Admin can change multipliers at any time from the Pricing Rules page
- Coupon codes validated in real-time at booking; discount shown to customer

### Requirement: Payment Simulation
- Payment page offers Cash, Card, UPI, and Net Banking
- Clicking "Confirm Payment" updates `payment_status` to `paid`
- No real payment gateway — simulated for academic demonstration

### Requirement: Maintenance Tracking
- Fleet Manager logs each maintenance event with type, description, cost, date, and next due date
- All logs visible on Fleet Dashboard with vehicle name
- Vehicles under maintenance are marked `under_maintenance` so customers cannot book them

### Requirement: Reporting / Dashboard
- Admin Dashboard shows: total vehicles, available vehicles, active rentals count, and cumulative revenue from paid bookings
- Recent 10 bookings listed with customer name, vehicle, status, and cost
- Fleet Dashboard shows all active rentals with customer and vehicle details

### Requirement: Easy Setup on Windows
- **`setup.bat`**: single double-click creates the virtual environment, installs all dependencies from `requirements.txt`, and initialises the database with seed data
- **`run.bat`**: single double-click starts the server; user visits `http://localhost:5000`
- No external services required — SQLite is built into Python; no database server to install

---

## 10. Demo Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@rental.com | admin123 |
| Fleet Manager | fleet@rental.com | fleet123 |
| Customer | john@example.com | customer123 |
| Customer | jane@example.com | customer123 |

## Demo Coupon Codes

| Code | Discount |
|---|---|
| WELCOME10 | 10% off |
| SUMMER20 | 20% off |
| VIP15 | 15% off |

---

## 11. End-to-End Demo Flow

```
── Customer Flow ──────────────────────────────────────────────────────────────
1. Open http://localhost:5000
2. Sign Up or Login as Customer (john@example.com / customer123)
3. Browse Vehicles → filter by type, fuel, seats
4. Click a vehicle → View Details
5. Click "Book Now" → choose Daily or Hourly
6. Set pickup and return date/time
7. Enter coupon code (e.g. WELCOME10) → see discount applied
8. Select payment mode → click "Confirm Booking"
9. Payment page → click "Confirm Payment"
10. My Rentals → view booking with status "Booked"

── Fleet Manager Flow ─────────────────────────────────────────────────────────
1. Login as Fleet Manager (fleet@rental.com / fleet123)
2. Fleet Dashboard → see all vehicles and active rentals
3. Under Active Rentals → click "Mark Picked Up"
4. Later → click "Mark Returned" (late fee auto-calculated if overdue)
5. Log Maintenance → fill form, save to maintenance log
6. Update Availability → change status of a vehicle

── Admin Flow ─────────────────────────────────────────────────────────────────
1. Login as Admin (admin@rental.com / admin123)
2. Admin Dashboard → view stats (revenue, active rentals, vehicle count)
3. Manage Vehicles → add a new vehicle or delete an existing one
4. Pricing Rules → adjust weekend/seasonal multiplier values
5. Coupons → add a new coupon, toggle active/inactive, delete
6. Fleet View → full operational dashboard (same as Fleet Manager)
```

---

*Generated for Jain University DBMS Project — VehicleRent Platform — April 2026*
