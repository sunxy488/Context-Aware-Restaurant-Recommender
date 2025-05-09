import os
import ast
import pandas as pd
import numpy as np
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import pickle

# Read restaurant basic information and validate required columns
df = pd.read_excel("data/results.xlsx")
if 'BizId' in df.columns:
    df.rename(columns={'BizId': 'business_id'}, inplace=True)

required_cols = {'ReviewCount', 'Ranking'}
missing = required_cols - set(df.columns)
if missing:
    raise KeyError(
        f"results.xlsx is missing required column(s): {', '.join(missing)}"
    )

# Basic restaurant information
df_restaurant = df[[
    'business_id', 'Name', 'Categories', 'Neighborhoods_0',
    'PriceRange', 'Rating', 'ReviewCount', 'Ranking'
]].copy()
df_restaurant.rename(columns={
    'Name': 'restaurant_name',
    'Categories': 'categories',
    'ReviewCount': 'review_count',
    'Ranking': 'ranking'
}, inplace=True)

# Create location string
df_restaurant['location'] = df_restaurant['Neighborhoods_0'].astype(str)
df_restaurant.drop(columns=['Neighborhoods_0'], inplace=True)

# Ensure string type for text columns
for col in ['categories', 'PriceRange', 'Rating',
            'review_count', 'ranking']:
    df_restaurant[col] = df_restaurant[col].astype(str)

# Read review file and aggregate English reviews
reviews = pd.read_excel("data/yelp_reviews.xlsx")


def extract_english_text(cell):
    try:
        d = ast.literal_eval(cell)
        return d.get('text', '') if d.get('language') == 'en' else ''
    except Exception:
        return ''


reviews['text'] = reviews['text'].apply(extract_english_text)
reviews = reviews[reviews['text'].astype(bool)].copy()

agg = (reviews
       .groupby('business_id')['text']
       .apply(lambda seg: ' '.join(seg))
       .reset_index()
       .rename(columns={'text': 'all_reviews'}))
df_restaurant = df_restaurant.merge(agg, on='business_id', how='left')
df_restaurant['all_reviews'] = df_restaurant['all_reviews'].fillna('')

# Build textual tags
df_restaurant['tags'] = (
        df_restaurant['categories'] + ' '
        + df_restaurant['location'] + ' '
        + df_restaurant['all_reviews']
).str.lower()

# Stemming
ps = PorterStemmer()
df_restaurant['tags'] = df_restaurant['tags'].apply(
    lambda txt: ' '.join(ps.stem(w) for w in txt.split())
)

# Working DataFrame including new features
new_df = df_restaurant[[
    'restaurant_name',
    'PriceRange',
    'Rating',
    'review_count',
    'ranking',
    'tags'
]].copy()

# TF–IDF vectorization
tfidf = TfidfVectorizer(max_features=5000, stop_words='english')
vectors = tfidf.fit_transform(new_df['tags']).toarray()

# map price range to number
price_num = new_df['PriceRange'].apply(lambda x: len(x)).values.reshape(-1, 1)
rating_num = new_df['Rating'].astype(float).values.reshape(-1, 1)
review_num = new_df['review_count'].astype(int).values.reshape(-1, 1)
rank_num = new_df['ranking'].astype(int).values.reshape(-1, 1)

# concatenate all numerical columns
num_feats = np.hstack([price_num, rating_num, review_num, rank_num])

# standardize
scaler = StandardScaler()
num_scaled = scaler.fit_transform(num_feats)

# combine text and numerical features
combined_feats = np.hstack([vectors, num_scaled])
similarity = cosine_similarity(combined_feats)

# Persist models and data
os.makedirs('models', exist_ok=True)
pickle.dump(similarity, open('models/restaurant_similarity.pkl', 'wb'))
pickle.dump(new_df, open('models/restaurant_info.pkl', 'wb'))
pickle.dump(tfidf, open('models/tfidf_vectorizer.pkl', 'wb'))
pickle.dump(vectors, open('models/restaurant_vectors.pkl', 'wb'))

print("Saved models:")
print(" - models/restaurant_similarity.pkl")
print(" - models/restaurant_info.pkl")
print(" - models/tfidf_vectorizer.pkl")
print(" - models/restaurant_vectors.pkl")


# Example recommendation function
def recommend(restaurant_name):
    if restaurant_name not in new_df['restaurant_name'].values:
        print("Restaurant not found. Please check the name.")
        return
    idx = new_df.index[new_df['restaurant_name'] == restaurant_name][0]
    sims = sorted(
        list(enumerate(similarity[idx])),
        key=lambda x: x[1], reverse=True
    )[1:11]
    print(f"Restaurants similar to '{restaurant_name}':")
    for i, score in sims:
        rec = new_df.iloc[i]
        print(f"  {rec.restaurant_name} "
              f"(sim={score:.4f}, reviews={rec.review_count}, rank={rec.ranking})")


# Quick test
if not new_df.empty:
    recommend(new_df['restaurant_name'].iloc[0])
