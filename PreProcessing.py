import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import OrdinalEncoder

df = pd.read_csv(r"Heart_Disease_Dataset.csv")

print("Data Information\n")
df.info()
print(df.head())
print("Dataset Shape:", df.shape)
print("Dataset descriptive statistics\n", df.describe())
print("Missing Values\n", df.isnull().sum())
print("Total Missing Values:", df.isnull().sum().sum())
print("Duplicate Rows:", df.duplicated().sum())

# Drop id column
df = df.drop(columns=['id'])
df['cardio'].value_counts(normalize=True)

# age in years
df['age_years'] = (df['age'] / 365).astype(int)

# Fill missing values with mode
print("\nAfter Dealing with Missing values")
df['smoke'] = df['smoke'].fillna(df['smoke'].mode()[0])
df['active'] = df['active'].fillna(df['active'].mode()[0])
df.info()

# Ordinal encoding for cholestrol and glucose
ordinal_cols = ['cholesterol', 'gluc']
encoder = OrdinalEncoder(categories=[
    ['normal', 'above normal', 'well above normal'],
    ['normal', 'above normal', 'well above normal']
])
df[ordinal_cols] = encoder.fit_transform(df[ordinal_cols])
print(df.head(10))

# Boxplots for outliers
numeric_cols = ['height', 'weight', 'ap_hi', 'ap_lo']
plt.figure(figsize=(12, 8))
for i, col in enumerate(numeric_cols):
    plt.subplot(2, 2, i+1)
    plt.boxplot(df[col])
    plt.title(f'Boxplot of {col}')
plt.tight_layout()
plt.show()

# Remove outliers
df = df[(df['height'] >= 70) & (df['height'] <= 220)]
df = df[df['weight'] >= 30]
df = df[(df['ap_hi'] >= 70) & (df['ap_hi'] <= 250)]
df = df[(df['ap_lo'] >= 40) & (df['ap_lo'] <= 180)]

print("\nAfter Dealing with Outliers\n")
print("Dataset shape after cleaning:", df.shape)
print(df[['height', 'weight', 'ap_hi', 'ap_lo']].describe())

# Drop 'age' column (keep age_years)
df = df.drop(columns=['age'])
df = df[['age_years'] + [col for col in df.columns if col != 'age_years']]

# Gender mapping
df['gender'] = df['gender'].map({1: 0, 2: 1})


df.to_csv("cleaned_data.csv", index=False)
