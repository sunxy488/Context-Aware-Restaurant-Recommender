import pandas as pd
from serpapi import GoogleSearch
import time
from datetime import datetime

api_key = "5c639bb14921e4a79215e9b83eb0dcda670ea5adc1ad93376a47c6001a241530"

# Read local files
csv_df   = pd.read_csv('results.csv')
xlsx_df  = pd.read_excel('results.xlsx')

# Extract and merge all id columns, remove duplicates
ids = pd.concat([csv_df['BizId'], xlsx_df['BizId']]) \
        .dropna() \
        .astype(str) \
        .unique() \
        .tolist()

# Create mapping from business ID to name
business_names = {}
for df in [csv_df, xlsx_df]:
    for _, row in df.iterrows():
        if pd.notna(row['BizId']) and pd.notna(row['Name']):
            business_names[str(row['BizId'])] = row['Name']

# Loop through each business_id and call SerpApi's Yelp engine
all_reviews = []
# Process only first 20 businesses
for i, business_id in enumerate(ids[:20], 1):
    print(f"\n[{i}/20] Fetching reviews for business {business_id} ({business_names.get(business_id, 'Unknown Business')})...")
    
    search = GoogleSearch({
        "api_key": api_key,
        "engine": "yelp_reviews",
        "place_id": business_id,
    })
    
    try:
        result = search.get_dict()
        
        if "error" in result:
            print(f"Warning: Error returned for business {business_id}: {result['error']}")
            continue
            
        reviews = result.get("reviews", [])
        print(f"Retrieved {len(reviews)} reviews")
        
        for rev in reviews:
            review_data = {
                "business_id": business_id,
                "business_name": business_names.get(business_id, "Unknown Business"),
                "username": rev.get("user", {}).get("name"),
                "rating": rev.get("rating"),
                "time_created": rev.get("date"),
                "text": rev.get("comment"),
            }
            all_reviews.append(review_data)
            
        # Save backup every 10 businesses to prevent data loss
        if i % 10 == 0:
            temp_df = pd.DataFrame(all_reviews)
            temp_df.to_excel(f'yelp_reviews_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx', 
                           index=False)
            
        # Add delay to avoid too many requests
        time.sleep(1)
        
    except Exception as e:
        print(f"Error: Exception occurred while processing business {business_id}: {str(e)}")
        continue

print(f"\nTotal reviews collected: {len(all_reviews)}")

# Save final results
reviews_df = pd.DataFrame(all_reviews)
output_filename = f'yelp_reviews_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
reviews_df.to_excel(output_filename, index=False)
print(f"Review data saved to file: {output_filename}")

# Display statistics
print("\nStatistics:")
print(f"Total businesses: {len(ids)}")
print(f"Successfully processed businesses: {len(reviews_df['business_id'].unique())}")
print(f"Average reviews per business: {len(reviews_df) / len(reviews_df['business_id'].unique()):.1f}")
print("\nRating distribution:")
print(reviews_df['rating'].value_counts().sort_index())