import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import pickle

X_train = pd.read_csv("X_train.csv")
X_val = pd.read_csv("X_val.csv")
X_test = pd.read_csv("X_test.csv")

to_scale = ['age_years','weight','ap_hi','ap_lo','bmi','pulse_pressure','cholesterol_gluc_interaction']
scaler = MinMaxScaler()
X_train[to_scale] = scaler.fit_transform(X_train[to_scale])
X_val[to_scale] = scaler.transform(X_val[to_scale])
X_test[to_scale] = scaler.transform(X_test[to_scale])

print("\nAfter Scaling\n", X_train[to_scale].head())

X_train.to_csv("X_train_scaled.csv", index=False)
X_val.to_csv("X_val_scaled.csv", index=False)
X_test.to_csv("X_test_scaled.csv", index=False)

with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)
