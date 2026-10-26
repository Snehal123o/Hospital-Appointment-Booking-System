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

## Screenshorts
<img width="1917" height="972" alt="Screenshot 2026-10-27 040438" src="https://github.com/user-attachments/assets/94e2cc9d-52a1-44af-9edf-ba18c2df6bcb" />

<img width="1916" height="977" alt="Screenshot 2026-10-27 040545" src="https://github.com/user-attachments/assets/a12f8e8b-d874-427b-b81e-82a288ff365c" />

<img width="1897" height="967" alt="Screenshot 2026-10-27 040646" src="https://github.com/user-attachments/assets/a4d2fe3e-9bbf-408a-b520-b7f4a12e7f08" />

<img width="1916" height="966" alt="Screenshot 2026-10-27 040808" src="https://github.com/user-attachments/assets/3fe22461-8a93-4186-bba7-5862ee3ca63f" />

<img width="1900" height="956" alt="Screenshot 2026-10-27 041057" src="https://github.com/user-attachments/assets/f17b0469-954f-4371-bf5a-86bcf07ca901" />

<img width="1892" height="961" alt="Screenshot 2026-10-27 041128" src="https://github.com/user-attachments/assets/899a0d94-f40f-4405-bfe1-d09a016ac7a8" />

<img width="1907" height="968" alt="Screenshot 2026-10-27 041213" src="https://github.com/user-attachments/assets/0da6a393-fe5b-4f89-b1ee-babdd9a8f2c3" />

<img width="1856" height="966" alt="Screenshot 2026-10-27 041331" src="https://github.com/user-attachments/assets/c1541040-4e2d-4d2d-9fae-5d85f2fd9b8d" />

<img width="1901" height="962" alt="Screenshot 2026-10-27 041358" src="https://github.com/user-attachments/assets/9fc0a879-97e3-49ea-8ead-3ff815cbd5c8" />













