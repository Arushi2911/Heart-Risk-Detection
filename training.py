import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import accuracy_score, recall_score, roc_auc_score, confusion_matrix, classification_report
import joblib

X_train = pd.read_csv("X_train_scaled.csv")
y_train = pd.read_csv("y_train.csv").squeeze()
X_val = pd.read_csv("X_val_scaled.csv")
y_val = pd.read_csv("y_val.csv").squeeze()
X_test = pd.read_csv("X_test_scaled.csv")
y_test = pd.read_csv("y_test.csv").squeeze()

weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])

# XGBClassifier
xgb = XGBClassifier(
    random_state=42,
    eval_metric='logloss',
    n_jobs=-1,
    reg_lambda=1,
    reg_alpha=0.1,
    scale_pos_weight=weight
)

# Hyperparameter
para = {
    'n_estimators': [200, 400],
    'max_depth': [3, 4],
    'learning_rate': [0.05, 0.1],
    'subsample': [0.7, 0.8],
    'colsample_bytree': [0.7, 0.8],
    'gamma': [0, 0.2]
}

search = RandomizedSearchCV(
    estimator=xgb,
    param_distributions=para,
    n_iter=20,
    cv=3,
    scoring='recall',
    n_jobs=-1,
    verbose=2,
    random_state=42
)

search.fit(X_train, y_train)
best_model = search.best_estimator_
print("Best Parameters:", search.best_params_)

# Validation 
threshold = 0.44
y_valProb = best_model.predict_proba(X_val)[:, 1]
y_valPred = (y_valProb >= threshold).astype(int)

print("Validation Accuracy:", accuracy_score(y_val, y_valPred))
print("Validation Recall:", recall_score(y_val, y_valPred))
print("Validation ROC-AUC:", roc_auc_score(y_val, y_valProb))
print("\nValidation Confusion Matrix:\n", confusion_matrix(y_val, y_valPred))
print("\nValidation Classification Report:\n", classification_report(y_val, y_valPred))

# Test predictions
y_test_prob = best_model.predict_proba(X_test)[:, 1]
y_test_pred = (y_test_prob >= threshold).astype(int)

print("Test Accuracy:", accuracy_score(y_test, y_test_pred))
print("Test Recall:", recall_score(y_test, y_test_pred))
print("Test ROC-AUC:", roc_auc_score(y_test, y_test_prob))
print("\nTest Confusion Matrix:\n", confusion_matrix(y_test, y_test_pred))
print("\nTest Classification Report:\n", classification_report(y_test, y_test_pred))


joblib.dump(best_model, "model.pkl")
