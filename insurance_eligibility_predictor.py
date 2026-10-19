import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

# Insurance Eligibility Predictor (Classification)
print("=== Insurance Eligibility Predictor ===")

# Load your dataset (assuming df is already loaded)
# df = pd.read_csv('your_dataset.csv')  # Uncomment and modify path as needed

# Check data types and identify non-numeric columns
print("\nDataset Info:")
print(f"Dataset shape: {df.shape}")
print("\nData types:")
print(df.dtypes)
print("\nFirst few rows:")
print(df.head())

# Define features and target
X = df.drop(columns=['eligibility'])
y = df['eligibility']

print(f"\nTarget distribution:")
print(y.value_counts())

# Identify numeric and categorical columns
numeric_columns = X.select_dtypes(include=[np.number]).columns.tolist()
categorical_columns = X.select_dtypes(include=['object', 'category']).columns.tolist()

print(f"\nNumeric columns ({len(numeric_columns)}): {numeric_columns}")
print(f"Categorical columns ({len(categorical_columns)}): {categorical_columns}")

# Handle categorical columns with high cardinality (like UUIDs)
high_cardinality_columns = []
for col in categorical_columns:
    unique_ratio = df[col].nunique() / len(df)
    if unique_ratio > 0.95:  # If more than 95% values are unique (likely IDs)
        high_cardinality_columns.append(col)
        print(f"High cardinality column detected: {col} (unique ratio: {unique_ratio:.3f})")

# Remove high cardinality columns (like UUIDs) that don't provide predictive value
if high_cardinality_columns:
    print(f"\nRemoving high cardinality columns: {high_cardinality_columns}")
    X = X.drop(columns=high_cardinality_columns)
    categorical_columns = [col for col in categorical_columns if col not in high_cardinality_columns]

# Update column lists after removing high cardinality columns
numeric_columns = X.select_dtypes(include=[np.number]).columns.tolist()
categorical_columns = X.select_dtypes(include=['object', 'category']).columns.tolist()

print(f"\nFinal columns for modeling:")
print(f"Numeric columns: {numeric_columns}")
print(f"Categorical columns: {categorical_columns}")

# Create preprocessing pipeline
preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), numeric_columns),
        ('cat', OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore'), categorical_columns)
    ],
    remainder='passthrough'  # Keep any remaining columns as-is
)

# Split the data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTrain set shape: {X_train.shape}")
print(f"Test set shape: {X_test.shape}")

# Create complete pipeline with preprocessing and model
pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', XGBClassifier(random_state=42, eval_metric='logloss'))
])

# Fit the pipeline
print("\nTraining the model...")
pipeline.fit(X_train, y_train)

# Make predictions
print("Making predictions...")
y_pred = pipeline.predict(X_test)
y_pred_proba = pipeline.predict_proba(X_test)

# Evaluate model
print("\n=== Model Performance ===")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Calculate ROC-AUC score
if len(np.unique(y)) == 2:  # Binary classification
    roc_auc = roc_auc_score(y_test, y_pred_proba[:, 1])
else:  # Multi-class classification
    roc_auc = roc_auc_score(y_test, y_pred_proba, multi_class='ovr')

print(f"\nROC-AUC Score: {roc_auc:.4f}")

# Feature importance (if available)
try:
    if hasattr(pipeline.named_steps['classifier'], 'feature_importances_'):
        # Get feature names after preprocessing
        feature_names = []
        
        # Add numeric feature names
        feature_names.extend(numeric_columns)
        
        # Add categorical feature names (one-hot encoded)
        if categorical_columns:
            cat_encoder = pipeline.named_steps['preprocessor'].named_transformers_['cat']
            cat_feature_names = cat_encoder.get_feature_names_out(categorical_columns)
            feature_names.extend(cat_feature_names)
        
        # Get feature importances
        importances = pipeline.named_steps['classifier'].feature_importances_
        
        # Create feature importance dataframe
        feature_importance_df = pd.DataFrame({
            'feature': feature_names[:len(importances)],
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        print("\n=== Top 10 Feature Importances ===")
        print(feature_importance_df.head(10))
        
except Exception as e:
    print(f"Could not extract feature importances: {e}")

print("\n=== Model Training Complete ===")

# Save the model (optional)
# import joblib
# joblib.dump(pipeline, 'insurance_eligibility_model.pkl')
# print("Model saved as 'insurance_eligibility_model.pkl'") 