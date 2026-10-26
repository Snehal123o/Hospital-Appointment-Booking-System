-- Hospital Appointment Booking and Management System
-- Run in MySQL:  mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS hospital_appointment_db;
USE hospital_appointment_db;

CREATE TABLE IF NOT EXISTS patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name  VARCHAR(100) NOT NULL,
    age        INT NOT NULL,
    gender     ENUM('Male','Female','Other') NOT NULL,
    phone      VARCHAR(15) NOT NULL UNIQUE,
    email      VARCHAR(100),
    address    VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doctors (
    doctor_id      INT AUTO_INCREMENT PRIMARY KEY,
    full_name      VARCHAR(100) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    experience_yrs INT DEFAULT 0,
    consult_fee    DECIMAL(8,2) DEFAULT 500.00,
    available_days VARCHAR(60) DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat'
);

CREATE TABLE IF NOT EXISTS doctor_accounts (
    doctor_id      INT PRIMARY KEY,
    email          VARCHAR(254) NOT NULL UNIQUE,
    password_salt  CHAR(32) NOT NULL,
    password_hash  CHAR(64) NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS appointments (
    appointment_id   INT AUTO_INCREMENT PRIMARY KEY,
    patient_id       INT NOT NULL,
    doctor_id        INT NOT NULL,
    appointment_date DATE NOT NULL,
    time_slot        VARCHAR(11) NOT NULL,
    reason           VARCHAR(255),
    status           ENUM('Booked','Cancelled','Completed') DEFAULT 'Booked',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (doctor_id)  REFERENCES doctors(doctor_id),
    -- Double-booking prevention at database level.
    -- active_key is NULL for cancelled rows, so a cancelled slot can be re-booked.
    active_key VARCHAR(40) GENERATED ALWAYS AS (
        IF(status = 'Cancelled', NULL,
           CONCAT(doctor_id, '|', appointment_date, '|', time_slot))
    ) STORED,
    UNIQUE KEY uq_doctor_slot (active_key)
);

INSERT INTO doctors (full_name, specialization, experience_yrs, consult_fee, available_days) VALUES
('Dr. Anil Patil',     'Cardiologist',     15, 800.00, 'Mon,Tue,Wed,Thu,Fri'),
('Dr. Sneha Kulkarni', 'Dermatologist',     8, 600.00, 'Mon,Wed,Fri,Sat'),
('Dr. Rahul Deshmukh', 'Orthopedic',       12, 700.00, 'Tue,Thu,Sat'),
('Dr. Priya Joshi',    'Pediatrician',     10, 500.00, 'Mon,Tue,Wed,Thu,Fri,Sat'),
('Dr. Vikram Shinde',  'General Physician', 6, 400.00, 'Mon,Tue,Wed,Thu,Fri,Sat'),
('Dr. Meera Jadhav',   'Gynecologist',     14, 750.00, 'Mon,Tue,Thu,Fri'),
('Dr. Suresh More',    'ENT Specialist',    9, 550.00, 'Mon,Wed,Thu,Sat');
