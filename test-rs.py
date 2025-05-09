import pickle
import numpy as np
import pandas as pd


def load_data():
    # Load precomputed similarity matrix and restaurant info
    similarity = pickle.load(open('models/restaurant_similarity.pkl', 'rb'))
    info = pickle.load(open('models/restaurant_info.pkl', 'rb'))
    return similarity, info


def get_recommendations(similarity, names, idx, K):
    # Get top-K similar restaurants (excluding itself)
    sims = list(enumerate(similarity[idx]))
    sims = sorted(sims, key=lambda x: x[1], reverse=True)
    top_indices = [i for i, _ in sims[1:K+1]]
    return [names[i] for i in top_indices]


def evaluate(similarity, info, relevant_set, query_idxs, K):
    hr_list, prec_list, rec_list, ndcg_list = [], [], [], []
    names = info['restaurant_name'].tolist()
    for idx in query_idxs:
        recs = get_recommendations(similarity, names, idx, K)
        # Binary hits for relevance
        hits = [1 if r in relevant_set else 0 for r in recs]
        # Hit Rate
        hr_list.append(1.0 if any(hits) else 0.0)
        # Precision@K
        prec_list.append(sum(hits) / K)
        # Recall@K
        rec_list.append(sum(hits) / len(relevant_set) if len(relevant_set) > 0 else 0.0)
        # NDCG@K
        dcg = sum([hit / np.log2(i + 2) for i, hit in enumerate(hits)])
        ideal_hits = [1] * min(len(relevant_set), K)
        idcg = sum([ideal_hits[i] / np.log2(i + 2) for i in range(len(ideal_hits))])
        ndcg_list.append(dcg / idcg if idcg > 0 else 0.0)

    # Aggregate metrics
    precision = np.mean(prec_list)
    recall = np.mean(rec_list)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {
        'HR': np.mean(hr_list),
        'Precision': precision,
        'Recall': recall,
        'F1': f1,
        'NDCG': np.mean(ndcg_list)
    }


def main():
    # Load data
    similarity, info = load_data()

    # Convert columns to numeric types
    info['review_count'] = info['review_count'].astype(int)
    info['Rating'] = info['Rating'].astype(float)
    info['ranking'] = info['ranking'].astype(int)

    # Define thresholds for relevance
    rating_threshold = 4.5
    review_count_threshold = info['review_count'].median()

    # Prepare explicit feedback ground truth (by rating)
    explicit_idxs = info[info['Rating'] >= rating_threshold].index.tolist()
    explicit_relevant = set(info.loc[info['Rating'] >= rating_threshold, 'restaurant_name'])

    # Prepare implicit feedback ground truth (by review count)
    implicit_idxs = info[info['review_count'] >= review_count_threshold].index.tolist()
    implicit_relevant = set(info.loc[info['review_count'] >= review_count_threshold, 'restaurant_name'])

    # Evaluate for different K values
    results = []
    for K in [1, 5, 10]:
        exp_metrics = evaluate(similarity, info, explicit_relevant, explicit_idxs, K)
        imp_metrics = evaluate(similarity, info, implicit_relevant, implicit_idxs, K)
        results.append({
            'K': K,
            **{f'exp_{m}': v for m, v in exp_metrics.items()},
            **{f'imp_{m}': v for m, v in imp_metrics.items()}
        })

    # Display results
    df_res = pd.DataFrame(results)
    print("Recommendation System Evaluation:")
    print(df_res.to_string(index=False))


if __name__ == '__main__':
    main()
