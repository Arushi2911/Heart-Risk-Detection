from flask import Flask, request, render_template, jsonify, redirect, url_for, flash, session, send_file
import io
from io import  BytesIO
import easyocr
from PIL import Image
from reportlab.pdfgen import canvas
from flask_wtf import FlaskForm
import pandas as pd
import pickle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import os
import bcrypt
import numpy as np
from datetime import datetime
import fitz, re
import mysql.connector
from flask_mysqldb import MySQL
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.secret_key = os.getenv('SECRET_KEY')

mysql = MySQL(app)


@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validation
        if not name or not email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('register'))

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_password)
            )
            mysql.connection.commit()
            cursor.close()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            if "Duplicate entry" in str(e):
                flash("This email is already registered.", "error")
            else:
                flash("An error occurred while registering. Please try again.", "error")
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Please fill out both fields.", "error")
            return redirect(url_for('login'))

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            session['user_id'] = user[0]
            flash("Login successful! Welcome back.", "success")
            return redirect(url_for('index'))  
        else:
            flash("Login failed. Invalid email or password.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/history')
def history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT record_id, created_at, bmi, ap_hi, ap_lo, risk_level, risk_percentage
        FROM user_record 
        WHERE user_id = %s 
        ORDER BY created_at DESC
    """, (user_id,))
    user_predictions = cursor.fetchall()

    # --- Calculate stats ---
    total_uploads = len(user_predictions)
    last_risk_level = user_predictions[0][5] if total_uploads > 0 else "N/A"
    last_date = user_predictions[0][1].strftime("%d %b %Y, %I:%M %p") if total_uploads > 0 else "N/A"

    cursor.close()

    return render_template(
        'history.html',
        name=session.get('name'),
        predictions=user_predictions,
        total_uploads=total_uploads,
        last_risk_level=last_risk_level,
        last_date=last_date
    )




def extract_text_from_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""

    for page in doc:
        text += page.get_text()

    if len(re.findall(r"[A-Za-z0-9]", text)) < 10:
        print("Text extraction failed — using OCR instead")
        reader = easyocr.Reader(['en'])
        ocr_text = ""
        for page_index in range(len(doc)):
            pix = doc.load_page(page_index).get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            ocr_result = reader.readtext(np.array(img), detail=0)
            ocr_text += " ".join(ocr_result) + "\n"
        text = ocr_text

    return text

model_path = os.path.join(os.path.dirname(__file__), 'model.pkl')
with open(model_path, 'rb') as f:
    model = pickle.load(f)

scaler_path = os.path.join(os.path.dirname(__file__), 'scaler.pkl')
with open(scaler_path, 'rb') as f:
    scaler = pickle.load(f)


def engineer_features(df):
    df['bmi'] = df['weight'] / ((df['height'] / 100) ** 2)
    df['pulse_pressure'] = df['ap_hi'] - df['ap_lo']
    df['health_index'] = (df['active'] * 1) - (df['smoke'] * 0.5) - (df['alco'] * 0.5)
    df['cholesterol_gluc_interaction'] = df['cholesterol'] + df['gluc']
    df = df.drop(columns=['height'])
    return df

@app.route("/extract_data", methods=["POST"])
def extract_data():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    import io
    file_bytes = io.BytesIO(file.read())
    text = extract_text_from_pdf(file_bytes)

    import re
    age = re.search(r"Age\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    gender = re.search(r"Gender\s*[:=]\s*(Male|Female)", text, re.IGNORECASE)
    weight = re.search(r"Weight\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    height = re.search(r"Height\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    ap_hi = re.search(r"(Systolic|ap_hi)\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    ap_lo = re.search(r"(Diastolic|ap_lo)\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    chol = re.search(r"Cholesterol\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    gluc = re.search(r"Glucose\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    smoke = re.search(r"Smoke\s*[:=]\s*(Yes|No)", text, re.IGNORECASE)
    alco = re.search(r"Alcohol\s*[:=]\s*(Yes|No)", text, re.IGNORECASE)
    active = re.search(r"(Exercise|Active)\s*[:=]\s*(Yes|No)", text, re.IGNORECASE)

    def yes_no_to_int(val): return 1 if val and val.lower() == "yes" else 0
    def gender_to_int(val): return 1 if val and val.lower() == "male" else 0
    def chol_to_cat(val):
        if not val: return ''
        v = int(val)
        if v < 200: return 0
        elif v < 240: return 1
        else: return 2
    def gluc_to_cat(val):
        if not val: return ''
        v = int(val)
        if v < 140: return 0
        elif v < 200: return 1
        else: return 2

    
    result = {
        "age": age.group(1) if age else '',
        "gender": gender_to_int(gender.group(1)) if gender else '',
        "weight": weight.group(1) if weight else '',
        "height": height.group(1) if height else '',
        "ap_hi": ap_hi.group(2) if ap_hi else '',
        "ap_lo": ap_lo.group(2) if ap_lo else '',
        "cholesterol": chol_to_cat(chol.group(1)) if chol else '',
        "glucose": gluc_to_cat(gluc.group(1)) if gluc else '',
        "smoke": yes_no_to_int(smoke.group(1)) if smoke else '',
        "alco": yes_no_to_int(alco.group(1)) if alco else '',
        "active": yes_no_to_int(active.group(2)) if active else ''
    }

    return jsonify(result)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT name FROM users WHERE user_id = %s", (session['user_id'],))
    user = cursor.fetchone()
    name = user[0] if user else "User"

    cursor.execute("""
        SELECT * FROM user_record 
        WHERE user_id = %s 
        ORDER BY record_id DESC 
        LIMIT 1
    """, (session['user_id'],))
    details = cursor.fetchone()
    cursor.close()

    user_data = []

    if details:
        user_data.append({
            'name': details[2],
            'age': details[3],
            'weight': details[4],
            'height': details[5],
            'ap_hi': details[6],
            'ap_lo': details[7],
            'chol': details[8],
            'gluc': details[9],
            'smoke': details[10],
            'alco': details[11],
            'active': details[12],
            'bmi': details[13],
            'risk_level' : details[14]
        })

    pdf_file = create_pdf(user_data)
    return send_file(pdf_file, as_attachment=True, download_name='medical_report.pdf')


def create_pdf(user_data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=60, bottomMargin=50)

    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = styles['Heading1']
    title_style.alignment = 1  # center
    elements.append(Paragraph("Comprehensive Medical Report", title_style))
    elements.append(Spacer(1, 12))

    # Date and patient info
    date_str = datetime.now().strftime("%B %d, %Y")
    elements.append(Paragraph(f"<b>Date:</b> {date_str}", styles['Normal']))
    elements.append(Spacer(1, 8))

    if user_data:
        data = user_data[0]

        # Personal Information Section
        elements.append(Paragraph("<b>1. Personal Information</b>", styles['Heading2']))
        personal_info = [
            ["Name", data['name']],
            ["Age", str(data['age'])],
            ["Height (cm)", str(data['height'])],
            ["Weight (kg)", str(data['weight'])],
            ["BMI", f"{data['bmi']:.2f}"]
        ]
        table = Table(personal_info, colWidths=[150, 300])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

        # Medical Parameters
        elements.append(Paragraph("<b>2. Medical Parameters</b>", styles['Heading2']))
        medical_data = [
            ["Systolic BP (mmHg)", data['ap_hi']],
            ["Diastolic BP (mmHg)", data['ap_lo']],
            ["Cholesterol Level", data['chol']],
            ["Glucose Level", data['gluc']],
            ["Smoking", "Yes" if data['smoke'] == 1 else "No"],
            ["Alcohol Consumption", "Yes" if data['alco'] == 1 else "No"],
            ["Physically Active", "Yes" if data['active'] == 1 else "No"]
        ]
        table2 = Table(medical_data, colWidths=[200, 250])
        table2.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ]))
        elements.append(table2)
        elements.append(Spacer(1, 20))

        # Placeholder for Model Prediction or Analysis
        elements.append(Paragraph("<b>3. Health Risk Assessment</b>", styles['Heading2']))
        elements.append(Paragraph(
            "The AI-based model analyzes your health metrics to predict cardiovascular risk levels. ",
            styles['Normal']
        ))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<i>Risk Level:</i> <b>{data['risk_level']}</b>", styles['Normal']))
        elements.append(Spacer(1, 8))


    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/prediction_model', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        print("User not logged in — redirecting.")
        flash("Please log in to access the dashboard.", "error")
        return redirect(url_for('login'))

    # Fetch user name
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT name FROM users WHERE user_id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    name = user[0] if user else "User"
    print(f"Logged in as: {name}")

    if request.method == 'POST':
        print("POST request received. Extracting form data...")
        data = request.form
        print("Form data:", data)

        # Extract and validate form inputs
        try:
            age_years = int(data.get('age'))
            height = float(data.get('height'))
            gender = int(data.get('gender'))
            weight = float(data.get('weight'))
            ap_hi = int(data.get('ap_hi'))
            ap_lo = int(data.get('ap_lo'))
            cholesterol = int(data.get('cholesterol'))
            glucose = int(data.get('glucose'))
            smoke = int(data.get('smoke'))
            alco = int(data.get('alco'))
            active = int(data.get('active'))
        except Exception as e:
            print("Error parsing form data:", e)
            flash(f"Invalid input data: {str(e)}", "error")
            return redirect(url_for('index'))

        # Create DataFrame
        try:
            df = pd.DataFrame([{
                'age_years': age_years,
                'height': height,
                'gender': gender,
                'weight': weight,
                'ap_hi': ap_hi,
                'ap_lo': ap_lo,
                'cholesterol': cholesterol,
                'gluc': glucose,
                'smoke': smoke,
                'alco': alco,
                'active': active
            }])
        except Exception as e:
            print("Error creating DataFrame:", e)
            flash(f"DataFrame creation error: {str(e)}", "error")
            return redirect(url_for('index'))

        # Feature engineering
        try:
            df = engineer_features(df)
            print("Feature engineering successful. Columns:", df.columns.tolist())
        except Exception as e:
            print("Error during feature engineering:", e)
            flash(f"Feature engineering failed: {str(e)}", "error")
            return redirect(url_for('index'))

        # BMI calculation
        try:
            bmi = float(df['bmi'].iloc[0])
        except Exception as e:
            flash(f"BMI calculation failed: {str(e)}", "error")
            return redirect(url_for('index'))

        # Save user record to DB
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO user_record
                (user_id, name, age, weight, height, ap_hi, ap_lo, cholesterol, glucose, smoke, alco, active, bmi)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (session['user_id'], name, age_years, weight, height, ap_hi, ap_lo,
                  cholesterol, glucose, smoke, alco, active, bmi))
            mysql.connection.commit()
            flash("Record saved successfully!", "success")
        except Exception as e:
            mysql.connection.rollback()
            print(f"Database error: {str(e)}")
            flash(f"Database error: {str(e)}", "error")
        finally:
            cursor.close()
            print("Cursor closed after DB operation.")

        # Run prediction
        try:
            print("Running prediction...")

            # ✅ Match training order exactly (excluding target)
            feature_order = [
                'age_years', 'gender', 'weight', 'ap_hi', 'ap_lo',
                'cholesterol', 'gluc', 'smoke', 'alco', 'active',
                'bmi', 'pulse_pressure','cholesterol_gluc_interaction'
            ]

            # Ensure all columns are present
            df = df[feature_order]

            # Features that were scaled during training
            scaled_features = [
                'age_years', 'weight', 'ap_hi', 'ap_lo',
                'bmi', 'pulse_pressure', 'cholesterol_gluc_interaction'
            ]

            # Apply scaling
            X_scaled = scaler.transform(df[scaled_features])
            df_scaled = df.copy()
            df_scaled[scaled_features] = X_scaled

            # Final model input
            X_model = df_scaled.values

            # Predict
            prediction = model.predict(X_model)[0]
            probability = model.predict_proba(X_model)[0][1] * 100
            if probability < 30:
                risk = "Low Risk"
            elif 30 <= probability <= 75:
                risk = "Moderate Risk"
            else:
                risk = "High Risk"


            cursor = mysql.connection.cursor()
            cursor.execute("""
                UPDATE user_record
                SET risk_level = %s, risk_percentage = %s
                WHERE user_id = %s
                ORDER BY record_id DESC LIMIT 1
            """, (risk, probability, session['user_id']))
            mysql.connection.commit()
            cursor.close()

            return jsonify({'risk': risk, 'percentage': round(probability, 2)})

        except Exception as e:
            print("❌ Error during prediction:", e)
            flash(f"Prediction error: {str(e)}", "error")

    return render_template('index.html', name=name)

from datetime import datetime

@app.route('/delete_entry/<date>', methods=['POST'])
def delete_entry(date):
    if 'user_id' not in session:
        return "Unauthorized", 403

    # Convert '03 Nov 2025, 04:57 PM' to '2025-11-03'
    try:
        parsed_date = datetime.strptime(date, "%d %b %Y, %I:%M %p").date()
    except ValueError:
        return "Invalid date format", 400

    cursor = mysql.connection.cursor()
    cursor.execute("""
        DELETE FROM user_record
        WHERE user_id = %s AND DATE(created_at) = %s
    """, (session['user_id'], parsed_date))
    mysql.connection.commit()
    cursor.close()
    return "Record deleted successfully", 200


@app.route('/get_report/<date>', methods=['GET'])
def get_report(date):
    if 'user_id' not in session:
        return "Unauthorized", 403

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT * FROM user_record
        WHERE user_id = %s AND DATE(created_at) = %s
    """, (session['user_id'], date))
    record = cursor.fetchone()
    cursor.close()

    if not record:
        return "No record found for this date", 404

    # Construct a dictionary for PDF
    user_data = [{
        'name': record[2],
        'age': record[3],
        'weight': record[4],
        'height': record[5],
        'ap_hi': record[6],
        'ap_lo': record[7],
        'chol': record[8],
        'gluc': record[9],
        'smoke': record[10],
        'alco': record[11],
        'active': record[12],
        'bmi': record[13]
    }]

    pdf_file = create_pdf(user_data)
    return send_file(pdf_file, as_attachment=True, download_name=f'report_{date}.pdf')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out successfully.")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
