"""Hospital Appointment Booking and Management System (Streamlit front end).

Run with:  streamlit run app.py
"""
from datetime import date, timedelta
import hmac
import os

import streamlit as st

import db

st.set_page_config(page_title="Hospital Appointment System", page_icon="🏥", layout="wide")

st.sidebar.title("🏥 City Care Hospital")
page = st.sidebar.radio(
    "Menu",
    ["Home", "Register Patient", "Find Doctor", "Book Appointment",
    "My Appointments", "Doctor Portal", "Admin Dashboard"],
)


def db_guard(fn, *args, **kwargs):
    """Run a DB call and show a friendly error if MySQL is unreachable."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not reach the database: {e}")
        st.info("Check that MySQL is running, schema.sql has been executed, "
                "and DB_* environment variables are set.")
        st.stop()


# ------------------------------------------------------------------ Home
if page == "Home":
    st.title("Hospital Appointment Booking & Management System")
    st.write("Register as a patient, search doctors by specialization, "
             "book a free time slot and track your appointment history.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Specializations", len(db_guard(db.list_specializations)))
    c2.metric("Doctors", len(db_guard(db.search_doctors)))
    c3.metric("Slots per day", len(db.TIME_SLOTS))
    st.caption("Use the menu on the left to get started.")

# ------------------------------------------------------- Register Patient
elif page == "Register Patient":
    st.title("Patient Registration")
    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("Full name *")
        col1, col2 = st.columns(2)
        age = col1.number_input("Age *", min_value=0, max_value=120, value=25)
        gender = col2.selectbox("Gender *", ["Male", "Female", "Other"])
        phone = st.text_input("Phone number * (10 digits)")
        email = st.text_input("Email")
        address = st.text_area("Address")
        submitted = st.form_submit_button("Register")

    if submitted:
        if not name.strip():
            st.error("Name is required.")
        elif not (phone.isdigit() and len(phone) == 10):
            st.error("Enter a valid 10-digit phone number.")
        else:
            ok, msg, pid = db_guard(
                db.register_patient, name.strip(), int(age), gender, phone, email.strip(), address.strip()
            )
            if ok:
                st.success(f"{msg} Your Patient ID is **{pid}**.")
            else:
                st.error(msg)

# ------------------------------------------------------------ Find Doctor
elif page == "Find Doctor":
    st.title("Search Doctors")
    specs = ["All"] + db_guard(db.list_specializations)
    col1, col2 = st.columns(2)
    spec = col1.selectbox("Specialization", specs)
    dname = col2.text_input("Doctor name (optional)")
    df = db_guard(db.search_doctors, spec, dname)
    if df.empty:
        st.warning("No doctors found.")
    else:
        df = df.rename(columns={
            "doctor_id": "ID", "full_name": "Doctor", "specialization": "Specialization",
            "experience_yrs": "Experience (yrs)", "consult_fee": "Fee (₹)",
            "available_days": "Available days",
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

# ------------------------------------------------------- Book Appointment
elif page == "Book Appointment":
    st.title("Book an Appointment")
    phone = st.text_input("Enter your registered phone number")
    if phone:
        patient = db_guard(db.find_patient_by_phone, phone)
        if patient.empty:
            st.warning("No patient found. Please register first.")
        else:
            pid = int(patient.iloc[0]["patient_id"])
            st.success(f"Welcome, {patient.iloc[0]['full_name']} (Patient ID {pid})")

            specs = ["All"] + db_guard(db.list_specializations)
            spec = st.selectbox("Specialization", specs)
            docs = db_guard(db.search_doctors, spec)
            labels = {
                f"{r.full_name} — {r.specialization} (₹{r.consult_fee:.0f})": int(r.doctor_id)
                for r in docs.itertuples()
            }
            choice = st.selectbox("Doctor", list(labels.keys()))
            doctor_id = labels[choice]

            appt_date = st.date_input(
                "Appointment date",
                value=date.today() + timedelta(days=1),
                min_value=date.today(),
                max_value=date.today() + timedelta(days=60),
            )

            slots = db_guard(db.get_available_slots, doctor_id, appt_date)
            if not slots:
                st.error("No free slots on this date (doctor unavailable or fully booked). "
                         "Try another date.")
            else:
                slot = st.selectbox("Available time slots", slots)
                reason = st.text_input("Reason for visit")
                if st.button("Confirm Booking", type="primary"):
                    ok, msg = db_guard(db.book_appointment, pid, doctor_id, appt_date, slot, reason)
                    (st.success if ok else st.error)(msg)

# ---------------------------------------------------------- My Appointments
elif page == "My Appointments":
    st.title("Appointment History")
    phone = st.text_input("Enter your registered phone number")
    if phone:
        patient = db_guard(db.find_patient_by_phone, phone)
        if patient.empty:
            st.warning("No patient found with this phone number.")
        else:
            pid = int(patient.iloc[0]["patient_id"])
            hist = db_guard(db.patient_history, pid)
            if hist.empty:
                st.info("You have no appointments yet.")
            else:
                st.dataframe(hist, use_container_width=True, hide_index=True)

                st.subheader("Cancel an appointment")
                active = hist[hist["status"] == "Booked"]
                if active.empty:
                    st.caption("No active appointments to cancel.")
                else:
                    aid = st.selectbox("Appointment ID", active["appointment_id"].tolist())
                    if st.button("Cancel appointment"):
                        ok, msg = db_guard(db.cancel_appointment, int(aid), pid)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()

# ------------------------------------------------------------ Doctor Portal
elif page == "Doctor Portal":
    st.title("Doctor Portal")
    doctor = st.session_state.get("doctor_account")
    if doctor is None:
        with st.form("doctor_login"):
            email = st.text_input("Doctor email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")

        if submitted:
            account = db_guard(db.authenticate_doctor, email, password)
            if account:
                st.session_state["doctor_account"] = account
                st.rerun()
            st.error("Email or password is incorrect.")
    else:
        st.subheader(f"{doctor['full_name']} | {doctor['specialization']}")
        if st.button("Log out"):
            del st.session_state["doctor_account"]
            st.rerun()
        appointments = db_guard(db.doctor_appointments, doctor["doctor_id"])
        if appointments.empty:
            st.info("You have no appointments yet.")
        else:
            st.dataframe(appointments, use_container_width=True, hide_index=True)

# ---------------------------------------------------------- Admin Dashboard
elif page == "Admin Dashboard":
    st.title("Admin Dashboard")
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if not admin_password:
        st.error("Admin access is disabled. Set the ADMIN_PASSWORD environment variable and restart the app.")
    else:
        if not st.session_state.get("admin_authenticated", False):
            with st.form("admin_login"):
                password = st.text_input("Admin password", type="password")
                submitted = st.form_submit_button("Log in")
            if submitted:
                if hmac.compare_digest(password, admin_password):
                    st.session_state["admin_authenticated"] = True
                    st.rerun()
                st.error("Incorrect admin password.")
        else:
            if st.button("Admin log out"):
                del st.session_state["admin_authenticated"]
                st.rerun()

            st.subheader("Doctor management")
            add_tab, account_tab = st.tabs(["Add doctor", "Create login for existing doctor"])

            with add_tab:
                with st.form("add_doctor_form", clear_on_submit=True):
                    name = st.text_input("Doctor full name *")
                    specialization = st.text_input("Specialization *")
                    experience = st.number_input("Experience (years)", min_value=0, max_value=70, value=0)
                    fee = st.number_input("Consultation fee", min_value=0.0, value=500.0, step=50.0)
                    days = st.multiselect(
                        "Available days",
                        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                        default=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    )
                    email = st.text_input("Doctor login email *")
                    password = st.text_input("Temporary password (8+ characters) *", type="password")
                    submitted = st.form_submit_button("Add doctor and create login")

                if submitted:
                    if not name.strip() or not specialization.strip() or not email.strip() or not days:
                        st.error("Enter the doctor's name, specialization, email, and at least one available day.")
                    elif len(password) < 8:
                        st.error("Password must contain at least 8 characters.")
                    else:
                        ok, message, doctor_id = db_guard(
                            db.add_doctor, name.strip(), specialization.strip(), int(experience),
                            fee, ",".join(days), email, password,
                        )
                        if ok:
                            st.success(f"{message} Doctor ID: {doctor_id}.")
                        else:
                            st.error(message)

            with account_tab:
                doctors = db_guard(db.doctors_without_accounts)
                if doctors.empty:
                    st.info("Every doctor already has a login account.")
                else:
                    doctor_options = {
                        f"{row.full_name} ({row.specialization})": int(row.doctor_id)
                        for row in doctors.itertuples()
                    }
                    with st.form("link_doctor_account_form", clear_on_submit=True):
                        selected_doctor = st.selectbox("Existing doctor", list(doctor_options))
                        email = st.text_input("Doctor login email *")
                        password = st.text_input("Temporary password (8+ characters) *", type="password")
                        submitted = st.form_submit_button("Create doctor login")

                    if submitted:
                        if not email.strip():
                            st.error("Enter a doctor login email.")
                        elif len(password) < 8:
                            st.error("Password must contain at least 8 characters.")
                        else:
                            ok, message = db_guard(
                                db.create_doctor_account, doctor_options[selected_doctor], email, password
                            )
                            (st.success if ok else st.error)(message)

            st.subheader("Appointment overview")
            df = db_guard(db.all_appointments)
            if df.empty:
                st.info("No appointments recorded yet.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Total appointments", len(df))
                c2.metric("Booked", int((df["status"] == "Booked").sum()))
                c3.metric("Cancelled", int((df["status"] == "Cancelled").sum()))

                st.subheader("Appointments per doctor")
                st.bar_chart(df[df["status"] != "Cancelled"].groupby("doctor").size())

                st.subheader("All appointments")
                st.dataframe(df, use_container_width=True, hide_index=True)
