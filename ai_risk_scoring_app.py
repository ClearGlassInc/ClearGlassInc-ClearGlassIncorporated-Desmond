import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_curve, auc
import joblib

# 1. Load the dataset
# Assuming the CSV is in the same directory. If using the URL, replace this line.
df = pd.read_csv('Maternal_Health_Risk_Data_Set_Modified.csv')

# 2. Remove PII (CitizenID)
if 'CitizenID' in df.columns:
    df = df.drop(columns=['CitizenID'])

# 3. Remove duplicates
df = df.drop_duplicates()

# 4. Handle missing values using median imputation
df = df.fillna(df.median(numeric_only=True))

print("Data cleaning complete.")
print(f"Dataset shape: {df.shape}")
print(df.head())

# 1. Identify features (X) and target (y)
X = df.drop(columns=['RiskLevel'])
y = df['RiskLevel']

# 2. 80:20 train-test split with stratification
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# 3. Implement Random Forest Classifier
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# 4. Evaluate performance
y_pred = rf_model.predict(X_test)
y_proba = rf_model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)

print(f"Accuracy: {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"F1-Score: {f1:.4f}")

# 5. Plot ROC-AUC Curve
fpr, tpr, _ = roc_curve(y_test, y_proba)
roc_auc = auc(fpr, tpr)

plt.figure(figsize=(8, 6))
plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic (ROC) - Random Forest')
plt.legend(loc="lower right")
plt.show()

# 6. Print Feature Importances
importances = rf_model.feature_importances_
feature_names = X.columns
feat_imp_df = pd.DataFrame({'Feature': feature_names, 'Importance': importances}).sort_values(by='Importance', ascending=False)
print("\nFeature Importances:")
print(feat_imp_df)

# 7. Save the trained model
joblib.dump(rf_model, 'risk_model.joblib')
print("\nModel saved as risk_model.joblib")

from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam

# 1. Scale the data
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 2. Build the Deep Neural Network
model = Sequential([
    Dense(16, input_dim=X_train_scaled.shape[1], activation='relu'),
    Dense(8, activation='relu'),
    Dense(1, activation='sigmoid') # Binary classification
])

# 3. Compile the model
model.compile(
    loss='binary_crossentropy',
    optimizer='adam',
    metrics=['accuracy']
)

# 4. Train the model
history = model.fit(
    X_train_scaled, y_train,
    epochs=50,
    batch_size=32,
    validation_split=0.1,
    verbose=1
)

# 5. Evaluate the model
y_pred_dnn_proba = model.predict(X_test_scaled)
y_pred_dnn = (y_pred_dnn_proba > 0.5).astype(int)

dnn_accuracy = accuracy_score(y_test, y_pred_dnn)
dnn_precision = precision_score(y_test, y_pred_dnn)
dnn_recall = recall_score(y_test, y_pred_dnn)
dnn_f1 = f1_score(y_test, y_pred_dnn)

print(f"\nDNN Accuracy: {dnn_accuracy:.4f}")
print(f"DNN Precision: {dnn_precision:.4f}")
print(f"DNN Recall: {dnn_recall:.4f}")
print(f"DNN F1-Score: {dnn_f1:.4f}")

# 6. Save the trained model
model.save('risk_model_dnn.keras')
print("DNN Model saved as risk_model_dnn.keras")