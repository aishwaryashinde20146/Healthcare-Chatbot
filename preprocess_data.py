# Remove/encode non-numeric columns before StandardScaler

import pandas as pd
from sklearn.preprocessing import LabelEncoder

# Step 1: Check your data types
print("Data types in your dataset:")
print(df.dtypes)

# Step 2: Remove high-cardinality columns (like UUIDs)
columns_to_remove = []
for col in df.columns:
    if df[col].dtype == 'object':
        unique_ratio = df[col].nunique() / len(df)
        if unique_ratio > 0.95:  # More than 95% unique values
            columns_to_remove.append(col)
            print(f"Removing: {col} (unique values: {df[col].nunique()})")

df = df.drop(columns=columns_to_remove)

# Step 3: Encode remaining categorical columns
categorical_cols = df.select_dtypes(include=['object']).columns
if len(categorical_cols) > 0:
    print(f"Encoding: {categorical_cols.tolist()}")
    le = LabelEncoder()
    for col in categorical_cols:
        df[col] = le.fit_transform(df[col].astype(str))

# Step 4: Now your data is ready for StandardScaler
print("✅ Data preprocessing complete - all columns are now numeric!")
print("Data types after preprocessing:")
print(df.dtypes) 