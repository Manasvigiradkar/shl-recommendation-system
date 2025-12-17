import pandas as pd

# Load original SHL training data
df = pd.read_csv("data/train_data.csv", encoding="latin1")

# Normalize URL format
df["Assessment_url"] = df["Assessment_url"].str.replace(
    "https://www.shl.com/solutions/products/",
    "https://www.shl.com/products/",
    regex=False
)

# Save normalized version
df.to_csv("data/train_data_normalized.csv", index=False)

print("✅ train_data_normalized.csv created successfully")

