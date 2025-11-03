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

        # Fetch user’s last 6 records for trend graph
            cursor.execute("""
                SELECT created_at, risk_percentage FROM user_record 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT 6
            """, (user_id,))
            history = cursor.fetchall()
            cursor.close()

            # Reverse to show oldest → newest
            history = history[::-1]
            labels = [record[0].strftime("%d %b") for record in history]
            percentages = [float(record[1]) for record in history]

            return jsonify({
                "risk": risk,
                "percentage": round(probability, 2),
                "labels": labels,
                "percentages": percentages
            })

        except Exception as e:
            print("Error:", e)
            return jsonify({"error": str(e)})

    return render_template('index.html', name=name)