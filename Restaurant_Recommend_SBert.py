import os
import ast
import pandas as pd
import numpy as np
from nltk.stem.porter import PorterStemmer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import pickle
from sentence_transformers import SentenceTransformer

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
for col in ['categories', 'PriceRange', 'Rating', 'review_count', 'ranking']:
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

# Sentence-BERT
print("Encoding with Sentence-BERT…")
sbert = SentenceTransformer('all-MiniLM-L6-v2')

vectors = sbert.encode(
    new_df['tags'].tolist(),
    show_progress_bar=True,
    convert_to_numpy=True
)

# map price range to number
price_num = new_df['PriceRange'].apply(len).values.reshape(-1, 1)
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
os.makedirs('models_sbert', exist_ok=True)
pickle.dump(similarity, open('models_sbert/restaurant_similarity_sbert.pkl', 'wb'))
pickle.dump(new_df, open('models_sbert/restaurant_info_sbert.pkl', 'wb'))
pickle.dump(vectors, open('models_sbert/restaurant_embeddings_sbert.pkl', 'wb'))
print("Saved SBERT models to models_sbert/")


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
        print(f"  • {rec.restaurant_name} "
              f"(sim={score:.4f}, rating={rec.Rating}, reviews={rec.review_count})")


if not new_df.empty:
    recommend(new_df['restaurant_name'].iloc[0])
