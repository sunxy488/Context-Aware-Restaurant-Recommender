import os
import pickle
from sklearn.metrics.pairwise import cosine_similarity
from extract_keywords import KeywordExtractor
from nltk.stem.porter import PorterStemmer

# init stemmer
ps = PorterStemmer()


# load pre-trained models
def load_models():
    info_df = pickle.load(open('models/restaurant_info.pkl', 'rb'))
    similarity = pickle.load(open('models/restaurant_similarity.pkl', 'rb'))
    cv = pickle.load(open('models/count_vectorizer.pkl', 'rb'))
    vectors = pickle.load(open('models/restaurant_vectors.pkl', 'rb'))
    return info_df, similarity, cv, vectors


# stem text
def stem_text(text: str) -> str:
    return " ".join(ps.stem(w) for w in text.split())


# load models
try:
    new_df, similarity, cv, vectors = load_models()
    extractor = KeywordExtractor()
except Exception as e:
    print(f"Error loading models: {e}")


# recommend by name
def recommend_by_name(restaurant_name: str):
    if restaurant_name not in new_df['restaurant_name'].values:
        print('Restaurant not found, please check your input.')
        return []
    idx = new_df.index[new_df['restaurant_name'] == restaurant_name][0]
    sims = sorted(
        list(enumerate(similarity[idx])),
        key=lambda x: x[1], reverse=True
    )[1:11]
    return [(new_df.iloc[i]['restaurant_name'], score) for i, score in sims]


# recommend by keyword
def recommend_by_keyword(keywords: list[str]):
    query = " ".join(keywords).lower()
    query = stem_text(query)
    q_vec = cv.transform([query]).toarray()
    sim_q = cosine_similarity(q_vec, vectors).flatten()
    top_idxs = sim_q.argsort()[::-1][:10]
    recs_df = new_df.iloc[top_idxs].copy()
    recs_df['similarity'] = sim_q[top_idxs]

    return recs_df[['restaurant_name', 'PriceRange', 'Rating', 'review_count', 'similarity']].values.tolist()


# handle user query
def recommend(query: str):
    try:
        # extract keywords
        keywords = extractor.extract_keywords(query)
        if not keywords:
            return [], []

        # recommend by keyword
        recs = recommend_by_keyword(keywords)

        # build return results
        results = []
        for name, price, rating, reviews, score in recs:
            results.append({
                "name": name,
                "rating": rating,
                "price": price,
                "reviews": int(reviews) if str(reviews).isdigit() else 0,
                "similarity": float(score)
            })

        return keywords, results
    except Exception as e:
        print(f"Error in recommendation process: {e}")
        return [], []
