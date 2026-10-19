# Quick Fix for Original Insurance Eligibility Predictor Code
# This script shows how to fix the ValueError: could not convert string to float

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, roc_auc_score

# Insurance Eligibility Predictor (Classification) - FIXED VERSION
print("=== Fixed Insurance Eligibility Predictor ===")

# Assuming your dataframe 'df' is already loaded
# df = pd.read_csv('your_dataset.csv')

# STEP 1: Identify and handle non-numeric columns
print("Original dataset shape:", df.shape)
print("Columns in dataset:", df.columns.tolist())

# Define features and target
X = df.drop(columns=['eligibility'])
y = df['eligibility']

# STEP 2: Check for non-numeric columns
print("\nChecking data types:")
print(X.dtypes)

# STEP 3: Handle non-numeric columns
# Option 1: Remove UUID/ID columns (recommended for columns with unique values)
columns_to_remove = []
for col in X.columns:
    if X[col].dtype == 'object':
        unique_ratio = X[col].nunique() / len(X)
        if unique_ratio > 0.95:  # If more than 95% values are unique
            columns_to_remove.append(col)
            print(f"Removing high cardinality column: {col} (unique values: {X[col].nunique()})")

if columns_to_remove:
    X = X.drop(columns=columns_to_remove)

# Option 2: Encode remaining categorical columns
categorical_cols = X.select_dtypes(include=['object']).columns
if len(categorical_cols) > 0:
    print(f"Encoding categorical columns: {categorical_cols.tolist()}")
    # Simple label encoding for categorical variables
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    for col in categorical_cols:
        X[col] = le.fit_transform(X[col].astype(str))

# STEP 4: Ensure all columns are numeric
print("\nFinal dataset info:")
print("Shape:", X.shape)
print("Data types after preprocessing:")
print(X.dtypes)

# STEP 5: Split the data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# STEP 6: Now StandardScaler will work properly
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print("✅ StandardScaler applied successfully!")
print(f"Training set shape: {X_train_scaled.shape}")
print(f"Test set shape: {X_test_scaled.shape}")

# STEP 7: Train the model
clf = XGBClassifier(random_state=42)
clf.fit(X_train_scaled, y_train)

# STEP 8: Evaluate model
y_pred = clf.predict(X_test_scaled)
print("\n=== Model Performance ===")
print(classification_report(y_test, y_pred))

# Calculate ROC-AUC score
try:
    if len(np.unique(y)) == 2:  # Binary classification
        y_pred_proba = clf.predict_proba(X_test_scaled)[:, 1]
        roc_auc = roc_auc_score(y_test, y_pred_proba)
    else:  # Multi-class
        y_pred_proba = clf.predict_proba(X_test_scaled)
        roc_auc = roc_auc_score(y_test, y_pred_proba, multi_class='ovr')
    
    print(f"ROC-AUC Score: {roc_auc:.4f}")
except Exception as e:
    print(f"Could not calculate ROC-AUC: {e}")

print("\n✅ Model training completed successfully!") 