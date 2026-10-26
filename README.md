# Hospital Appointment Booking and Management System

A web-based application to manage patient registration, doctor search and hospital
appointment scheduling, with double-booking prevention and appointment history.

**Tech Stack:** Python, Streamlit, MySQL, Pandas, mysql-connector-python

## Features
- Patient registration (unique phone number, input validation)
- Doctor search by specialization or name
- Doctor availability checking (working days + free time slots)
- Appointment booking with **double-booking prevention** (application check + database UNIQUE key)
- Patient appointment history and cancellation (cancelled slots become free again)
- Admin dashboard with counts and appointments-per-doctor chart (Pandas)

## Project structure
```
hospital_appointment_system/
├── app.py            # Streamlit UI
├── db.py             # MySQL queries (mysql-connector-python + Pandas)
├── schema.sql        # Tables + sample doctors
└── requirements.txt
```

## Setup
1. Install MySQL and make sure it is running.
2. Create the database and tables:
   ```
   mysql -u root -p < schema.sql
   ```
   For an existing installation, import `doctor_accounts.sql` into `hospital_appointment_db` instead; do not re-import `schema.sql` because it also inserts sample doctors.
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set your MySQL credentials (defaults: host=localhost, user=root, empty password, db=hospital_db):
   - Windows (PowerShell): `$env:DB_PASSWORD="your_password"`
   - Linux / macOS: `export DB_PASSWORD="your_password"`
   Set an administrator password before running the app:
   - Windows (PowerShell): `$env:ADMIN_PASSWORD="choose_a_strong_password"`
   - Linux / macOS: `export ADMIN_PASSWORD="choose_a_strong_password"`
   If using `hospital_appointment_db`, set `DB_NAME` to that database as well.
5. Run:
   ```
   streamlit run app.py
   ```

## How double-booking is prevented
1. Before inserting, `book_appointment()` checks whether the doctor already has an active
   appointment in that date + slot, and whether the patient has another one at the same time.
2. `schema.sql` also defines a UNIQUE key on (doctor, date, slot) for non-cancelled
   appointments, so even two users booking at the same instant cannot both succeed.

## Demo flow
Register Patient -> Find Doctor -> Book Appointment (use the same phone number) ->
My Appointments -> Admin Dashboard.
