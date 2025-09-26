import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import OrdinalEncoder
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

df = pd.read_csv(r"Heart_Disease_Dataset.csv")

print("Data Information\n")

df.info()

print(df.head())

print("Dataset Shape: ")
print(df.shape)

print("Dataset descriptive statistics")
print(df.describe())

print("Missing Values")
print(df.isnull().sum())

print("Total No. of missing Values")
print(df.isnull().sum().sum())

print("No. of duplicate rows")
print(df.duplicated().sum())

df = df.drop(columns=['id'])
df['cardio'].value_counts(normalize=True)

df['age_years'] = (df['age'] / 365).astype(int)
df.describe()


#Deal with missing values
print("\nAfter Dealing with Missing values")
df['smoke'] = df['smoke'].fillna(df['smoke'].mode()[0])
df['active']  = df['active'].fillna(df['active'].mode()[0])
df.info()

ordinal_cols = ['cholesterol', 'gluc']

encoder = OrdinalEncoder(categories=[['normal', 'above normal', 'well above normal'],
                                     ['normal', 'above normal', 'well above normal']])

df[ordinal_cols] = encoder.fit_transform(df[ordinal_cols])

print(df.head(10))

#Boxplot to see outliers
numeric_cols = ['height', 'weight', 'ap_hi', 'ap_lo']
plt.figure(figsize=(12,8))

for i, col in enumerate(numeric_cols):
    plt.subplot(2, 2, i+1)
    plt.boxplot(df[col])
    plt.title(f'Boxplot of {col}')

plt.tight_layout()
plt.show()


#Dealing with outliers
# Height: 70 cm to 220 cm
df = df[(df['height'] >= 70) & (df['height'] <= 220)]

# Weight: 30 kg to 200 kg
df = df[df['weight'] >= 30]

# Systolic BP: from 70 to 250 mmHg
df = df[(df['ap_hi'] >= 70) & (df['ap_hi'] <= 250)]

# Diastolic BP : from 40 to 180 mmHg
df = df[(df['ap_lo'] >= 40) & (df['ap_lo'] <= 180)]

print("\nAfter Dealing with Outliers\n")
print("Dataset shape after cleaning:", df.shape)
print(df[['height', 'weight', 'ap_hi', 'ap_lo']].describe())

#Removed column 'age' keeping age_years col
df = df.drop(columns=['age'])
df = df[['age_years'] + [col for col in df.columns if col != 'age_years']]

# Replace 1 to 0 for women and from 2 to 1 for men
df['gender'] = df['gender'].map({1: 0, 2: 1})

#Scaling and Normalization
scaler = MinMaxScaler()

to_scale = ['age_years','height','weight','ap_hi','ap_lo',]
df[to_scale] = scaler.fit_transform(df[to_scale])

print("\nAfter Scaling")
print(df[to_scale].head())

#Dividing the Dataset
X = df.drop("cardio", axis=1)
y = df["cardio"]

#training and temporary set
X_train, X_temp, y_train, y_temp=train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

#validation and testing set
X_val, X_test, y_val, y_test=train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

print("\nAfter Dividing Dataset into training, validation and testing dataset")
print("Train size:", X_train.shape[0])
print("Validation size:", X_val.shape[0])
print("Test size:", X_test.shape[0])
