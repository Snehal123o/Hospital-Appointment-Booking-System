"""Database layer for the Hospital Appointment Booking and Management System.

Uses mysql-connector-python for MySQL access and Pandas for tabular results.
Set connection details through environment variables (see README.md).
"""
import hashlib
import hmac
import os
import secrets
from datetime import date

import mysql.connector
import pandas as pd
from mysql.connector import Error, errorcode

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "hospital_db"),
}
_PASSWORD_ITERATIONS = 310_000

# Hourly slots; 13:00-14:00 is the lunch break.
TIME_SLOTS = [
    "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00",
    "14:00-15:00", "15:00-16:00", "16:00-17:00",
]


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def _query_df(sql, params=None) -> pd.DataFrame:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        cols = [c[0] for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()


# ----------------------------- patients ---------------------------------
def register_patient(name, age, gender, phone, email, address):
    """Insert a new patient. Returns (ok, message, patient_id)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO patients (full_name, age, gender, phone, email, address) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (name, age, gender, phone, email or None, address or None),
        )
        conn.commit()
        return True, "Patient registered successfully.", cur.lastrowid
    except Error as e:
        conn.rollback()
        if e.errno == errorcode.ER_DUP_ENTRY:
            return False, "A patient with this phone number already exists.", None
        return False, f"Database error: {e}", None
    finally:
        conn.close()


def find_patient_by_phone(phone) -> pd.DataFrame:
    return _query_df("SELECT * FROM patients WHERE phone = %s", (phone,))


# ----------------------------- doctors ----------------------------------
def list_specializations():
    df = _query_df("SELECT DISTINCT specialization FROM doctors ORDER BY specialization")
    return df["specialization"].tolist()


def search_doctors(specialization=None, name=None) -> pd.DataFrame:
    sql = ("SELECT doctor_id, full_name, specialization, experience_yrs, "
           "consult_fee, available_days FROM doctors WHERE 1=1")
    params = []
    if specialization and specialization != "All":
        sql += " AND specialization = %s"
        params.append(specialization)
    if name:
        sql += " AND full_name LIKE %s"
        params.append(f"%{name}%")
    sql += " ORDER BY full_name"
    return _query_df(sql, params)


def get_doctor(doctor_id) -> pd.Series:
    df = _query_df("SELECT * FROM doctors WHERE doctor_id = %s", (doctor_id,))
    return df.iloc[0] if not df.empty else None


def _password_credentials(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _PASSWORD_ITERATIONS
    ).hex()
    return salt, digest


def doctors_without_accounts() -> pd.DataFrame:
    return _query_df(
        "SELECT d.doctor_id, d.full_name, d.specialization FROM doctors d "
        "LEFT JOIN doctor_accounts a ON a.doctor_id = d.doctor_id "
        "WHERE a.doctor_id IS NULL ORDER BY d.full_name"
    )


def create_doctor_account(doctor_id, email, password):
    salt, digest = _password_credentials(password)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO doctor_accounts (doctor_id, email, password_salt, password_hash) "
            "VALUES (%s, %s, %s, %s)",
            (doctor_id, email.strip().lower(), salt, digest),
        )
        conn.commit()
        return True, "Doctor login created successfully."
    except Error as e:
        conn.rollback()
        if e.errno == errorcode.ER_DUP_ENTRY:
            return False, "This doctor or email already has an account."
        if e.errno == errorcode.ER_NO_REFERENCED_ROW_2:
            return False, "Doctor not found. Refresh the page and try again."
        return False, f"Database error: {e}"
    finally:
        conn.close()


def add_doctor(name, specialization, experience_yrs, consult_fee, available_days,
               email, password):
    salt, digest = _password_credentials(password)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO doctors (full_name, specialization, experience_yrs, consult_fee, available_days) "
            "VALUES (%s, %s, %s, %s, %s)",
            (name, specialization, experience_yrs, consult_fee, available_days),
        )
        doctor_id = cur.lastrowid
        cur.execute(
            "INSERT INTO doctor_accounts (doctor_id, email, password_salt, password_hash) "
            "VALUES (%s, %s, %s, %s)",
            (doctor_id, email.strip().lower(), salt, digest),
        )
        conn.commit()
        return True, "Doctor added and login created successfully.", doctor_id
    except Error as e:
        conn.rollback()
        if e.errno == errorcode.ER_DUP_ENTRY:
            return False, "This email is already used by a doctor account.", None
        return False, f"Database error: {e}", None
    finally:
        conn.close()


def authenticate_doctor(email, password):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT a.doctor_id, a.password_salt, a.password_hash, "
            "d.full_name, d.specialization FROM doctor_accounts a "
            "JOIN doctors d ON d.doctor_id = a.doctor_id WHERE a.email = %s",
            (email.strip().lower(),),
        )
        account = cur.fetchone()
    finally:
        conn.close()

    if account is None:
        return None
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(account[1]), _PASSWORD_ITERATIONS
    ).hex()
    if not hmac.compare_digest(digest, account[2]):
        return None
    return {
        "doctor_id": int(account[0]),
        "full_name": account[3],
        "specialization": account[4],
    }


def doctor_appointments(doctor_id) -> pd.DataFrame:
    return _query_df(
        """
        SELECT a.appointment_id, p.full_name AS patient, p.phone,
               a.appointment_date, a.time_slot, a.reason, a.status
        FROM appointments a
        JOIN patients p ON p.patient_id = a.patient_id
        WHERE a.doctor_id = %s
        ORDER BY a.appointment_date, a.time_slot
        """,
        (doctor_id,),
    )


# --------------------------- availability -------------------------------
def doctor_works_on(doctor_id, appt_date: date) -> bool:
    doc = get_doctor(doctor_id)
    if doc is None:
        return False
    return appt_date.strftime("%a") in doc["available_days"].split(",")


def get_available_slots(doctor_id, appt_date: date):
    """Return the slots still free for the doctor on that date."""
    if not doctor_works_on(doctor_id, appt_date):
        return []
    booked = _query_df(
        "SELECT time_slot FROM appointments "
        "WHERE doctor_id = %s AND appointment_date = %s AND status <> 'Cancelled'",
        (doctor_id, appt_date),
    )["time_slot"].tolist()
    return [s for s in TIME_SLOTS if s not in booked]


# --------------------------- appointments -------------------------------
def book_appointment(patient_id, doctor_id, appt_date: date, slot, reason):
    """Book an appointment with double-booking prevention.

    Checks the doctor's slot and the patient's own clash in application code,
    and the UNIQUE key in the schema acts as the final safety net.
    """
    if appt_date < date.today():
        return False, "Cannot book an appointment in the past."
    if not doctor_works_on(doctor_id, appt_date):
        return False, "The doctor is not available on this day."

    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT 1 FROM appointments WHERE doctor_id=%s AND appointment_date=%s "
            "AND time_slot=%s AND status <> 'Cancelled'",
            (doctor_id, appt_date, slot),
        )
        if cur.fetchone():
            return False, "This slot is already booked. Please choose another slot."

        cur.execute(
            "SELECT 1 FROM appointments WHERE patient_id=%s AND appointment_date=%s "
            "AND time_slot=%s AND status <> 'Cancelled'",
            (patient_id, appt_date, slot),
        )
        if cur.fetchone():
            return False, "You already have another appointment at this time."

        cur.execute(
            "INSERT INTO appointments (patient_id, doctor_id, appointment_date, time_slot, reason) "
            "VALUES (%s, %s, %s, %s, %s)",
            (patient_id, doctor_id, appt_date, slot, reason or None),
        )
        conn.commit()
        return True, f"Appointment booked successfully (ID: {cur.lastrowid})."
    except Error as e:
        conn.rollback()
        if e.errno == errorcode.ER_DUP_ENTRY:  # two users raced for the same slot
            return False, "Sorry, this slot was just taken. Please pick another."
        return False, f"Database error: {e}"
    finally:
        conn.close()


def patient_history(patient_id) -> pd.DataFrame:
    return _query_df(
        """
        SELECT a.appointment_id, a.appointment_date, a.time_slot,
               d.full_name AS doctor, d.specialization, a.reason, a.status
        FROM appointments a
        JOIN doctors d ON d.doctor_id = a.doctor_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date DESC, a.time_slot
        """,
        (patient_id,),
    )


def cancel_appointment(appointment_id, patient_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE appointments SET status='Cancelled' "
            "WHERE appointment_id=%s AND patient_id=%s AND status='Booked'",
            (appointment_id, patient_id),
        )
        conn.commit()
        if cur.rowcount:
            return True, "Appointment cancelled."
        return False, "No active appointment found with that ID for this patient."
    except Error as e:
        conn.rollback()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def all_appointments() -> pd.DataFrame:
    """For the admin dashboard."""
    return _query_df(
        """
        SELECT a.appointment_id, p.full_name AS patient, p.phone,
               d.full_name AS doctor, d.specialization,
               a.appointment_date, a.time_slot, a.status
        FROM appointments a
        JOIN patients p ON p.patient_id = a.patient_id
        JOIN doctors  d ON d.doctor_id  = a.doctor_id
        ORDER BY a.appointment_date DESC, a.time_slot
        """
    )
