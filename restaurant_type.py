import pandas as pd
import os
import pickle

# Config paths
input_path = "data/yelp_reviews_classified_output8000.xlsx"
output_xlsx = "scene_statistics_per_restaurant.xlsx"
output_pkl = "models/categorized_restaurants.pkl"

# Load data   
df = pd.read_excel(input_path)

# Validate required columns
for col in ("business_id", "business_name", "category", "text"):
    if col not in df.columns:
        raise KeyError(f"Input file must contain a '{col}' column.")

# Compute total review counts
total_reviews = (
    df
    .groupby("business_id")
    .size()
    .rename("n_reviews")
    .reset_index()
)

# Pivot to count each category
pivot = (
    df
    .pivot_table(
        index=["business_id", "business_name"],
        columns="category",
        values="text",
        aggfunc="count",
        fill_value=0
    )
    .reset_index()
)

# Merge total_reviews into pivot
result = pivot.merge(total_reviews, on="business_id")

# Reorder rows to match original appearance
order_df = df[["business_id", "business_name"]].drop_duplicates()
result = order_df.merge(
    result,
    on=["business_id", "business_name"],
    how="left"
)

# Reorder columns: name, id, n_reviews, then sorted category columns
cat_cols = sorted([
    c for c in result.columns
    if c not in ("business_id", "business_name", "n_reviews")
])
result = result[["business_name", "business_id", "n_reviews"] + cat_cols]

# Save summary to Excel
result.to_excel(output_xlsx, index=False)
print(f"Saved scene statistics to '{output_xlsx}'")

# Categorize restaurants by thresholds
dating_list = result.loc[result['dating'] >= 3, 'business_name'].tolist()
family_list = result.loc[result['family'] >= 20, 'business_name'].tolist()
friend_list = result.loc[result['friend'] >= 3, 'business_name'].tolist()
pro_list = result.loc[result['professional'] >= 3, 'business_name'].tolist()

# Build a DataFrame with columns aligned
cats = {
    'dating': dating_list,
    'family': family_list,
    'friend': friend_list,
    'professional': pro_list
}
max_len = max(len(v) for v in cats.values())
for k, v in cats.items():
    # pad shorter lists with NaN so all columns have equal length
    if len(v) < max_len:
        cats[k] = v + [pd.NA] * (max_len - len(v))

df_categorized = pd.DataFrame(cats)

# Save categorized restaurants as a pickle
os.makedirs(os.path.dirname(output_pkl), exist_ok=True)
with open(output_pkl, "wb") as f:
    pickle.dump(df_categorized, f)
print(f"Saved categorized restaurants to '{output_pkl}'")
print("\n===== Categorized Restaurants Preview =====")
print(df_categorized.head(10).to_string(index=False))
