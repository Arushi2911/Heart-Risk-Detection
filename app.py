from flask import Flask, request, render_template
import pandas as pd
import pickle
import os

app = Flask(__name__)

# Load model
model_path = os.path.join(os.path.dirname(__file__), 'model.pkl')
with open(model_path, 'rb') as f:
    model = pickle.load(f)

# Feature engineering 
def engineer_features(df):
    df['height'] = df['height'] / 100  # in meters
    df['bmi'] = df['weight'] / (df['height'] ** 2)
    df['pulse_pressure'] = df['ap_hi'] - df['ap_lo']
    df['health_index'] = (df['active'] * 1) - (df['smoke'] * 0.5) - (df['alco'] * 0.5)
    df['cholesterol_gluc_interaction'] = df['cholesterol'] * df['gluc']
    return df

@app.route('/', methods=['GET', 'POST'])
def index():
    prediction_text = ''
    if request.method == 'POST':
        data = request.form.to_dict()
        
        df = pd.DataFrame([{
            'age': int(data['age']),
            'height': float(data['height']),
            'weight': float(data['weight']),
            'ap_hi': int(data['systolic_bp']),
            'ap_lo': int(data['diastolic_bp']),
            'cholesterol': {'normal':1,'above_normal':2,'well_above_normal':3}[data['cholesterol']],
            'gluc': {'normal':1,'above_normal':2,'well_above_normal':3}[data['glucose']],
            'smoke': 1 if data['smoke']=='yes' else 0,
            'alco': 1 if data['alcohol']=='yes' else 0,
            'active': 1 if data['active']=='yes' else 0
        }])
        
        df = engineer_features(df)
        
        features = ['age', 'height', 'weight', 'ap_hi', 'ap_lo', 'cholesterol', 
                    'gluc', 'smoke', 'alco', 'active', 'bmi', 'pulse_pressure', 
                    'health_index', 'cholesterol_gluc_interaction']
        
        X = df[features]
        pred = int(model.predict(X)[0])
        prediction_text = f'Prediction: {"High Risk" if pred==1 else "Low Risk"}'
    
    return render_template('index.html', prediction_text=prediction_text)

if __name__ == '__main__':
    app.run(debug=True)
