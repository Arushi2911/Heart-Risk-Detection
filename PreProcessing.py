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
TARGET = 'cardio'
INPUT_FEATURES = ['age_years','height','weight','ap_hi','ap_lo','cholesterol','gluc','smoke','alco','active']

def IQR(series):
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)

    IQR = Q3 - Q1
    min_v = Q1 - 1.5 * IQR
    max_v = Q3 + 1.5 * IQR

    return series.clip(lower=min_v, upper=max_v)

exclude = ['gluc','alco','smoke','cholesterol','active']

for num_feature in [f for f in INPUT_FEATURES if f not in exclude]:
    for gender_category in df[TARGET].unique():
        mask = df[TARGET] == gender_category
        df.loc[mask, num_feature] = IQR(df.loc[mask, num_feature])


print("\nAfter Dealing with Outliers\n")
print("Dataset shape after cleaning:", df.shape)
print(df[['height', 'weight', 'ap_hi', 'ap_lo']].describe())

#Feature Engineering
mask = df["ap_hi"] < df["ap_lo"]
df = df[~mask].copy()
df["ap_hi"] = df["ap_hi"].clip(90, 180)
df["ap_lo"] = df["ap_lo"].clip(60, 110)
df['height'] = df['height'] / 100
df['bmi'] = df['weight'] / ((df['height'] / 100) ** 2)
df['pulse_pressure'] = df['ap_hi'] - df['ap_lo']
df['cholesterol_gluc_interaction'] = df['cholesterol'] * df['gluc']
df["pulse_pressure"] = df["pulse_pressure"].clip(30, 80)


# Drop 'age' column (keep age_years)
df = df.drop(columns=['age'])
df = df[['age_years'] + [col for col in df.columns if col != 'age_years']]
df = df.drop(columns=['height'])
# Gender mapping
df['gender'] = df['gender'].map({1: 0, 2: 1})


df.to_csv("cleaned_data.csv", index=False)
