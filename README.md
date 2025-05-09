# Restaurant Recommendation System

A web application that provides restaurant recommendations based on user queries. The system extracts keywords from user input and offers relevant restaurant suggestions. It supports two recommendation modes: query-based and restaurant-name-based.

## Features

- **Keyword Extraction**: Extracts relevant restaurant keywords from user queries using NLP techniques
- **Dual Recommendation Modes**:
  - **Query-Based**: Recommends restaurants based on extracted keywords from user input
  - **Restaurant-Based**: Recommends similar restaurants to a selected restaurant
- **Detailed Information**: Displays restaurant names, ratings, and price ranges
- **Real-Time Environmental Factors**:
  - **Weather Information**: Retrieves and considers current weather conditions for user's location
  - **Traffic Information**: Calculates traffic conditions and estimated travel times to recommended restaurants
- **Social Context Classification**: Provides restaurant options suitable for dating, family gatherings, friend meetups, and professional meetings
- **Responsive UI**: Interface adapts to different devices with integrated map visualization
- **AI Chatbot Assistant**: Natural language interaction with the recommendation system powered by Gemini API
- **Zero-Shot Classification**: Uses transformer models to categorize restaurants by social contexts without explicit training
- **Interactive Map**: Shows restaurant locations with traffic overlay and categorized markers

## Directory Structure

```
restaurant-recommender/
├─ app.py                # Flask application entry point
├─ recommender.py        # Core recommendation functionality
├─ extract_keywords.py   # Keyword extraction functionality
├─ restaurant_type.py    # Restaurant social context classification
├─ requirements.txt      # Project dependencies
├─ Restaurant_Recommend_TF-IDF.py # TF-IDF model training script
├─ Restaurant_Recommend_SBert.py  # Sentence-BERT model training script
├─ test-zeroshot-result.py # Script for testing social context classification
├─ zeroshot-classify.py    # Zero-shot classification implementation
├─ get_reviews.py          # Script for retrieving restaurant reviews
├─ test-rs.py              # Testing script for recommendation system
├─ models/               # TF-IDF based models
│   ├─ restaurant_info.pkl        # Restaurant information
│   ├─ restaurant_similarity.pkl  # Similarity matrix
│   ├─ tfidf_vectorizer.pkl      # TF-IDF vectorizer
│   ├─ count_vectorizer.pkl      # Count vectorizer
│   └─ restaurant_vectors.pkl    # Restaurant vectors
├─ models_sbert/         # Sentence-BERT based models
│   ├─ restaurant_info_sbert.pkl        # Restaurant information
│   ├─ restaurant_similarity_sbert.pkl  # SBERT similarity matrix
│   └─ restaurant_embeddings_sbert.pkl  # SBERT embedding vectors
├─ data/                 # Data files
│   ├─ results.xlsx             # Restaurant information
│   ├─ yelp_reviews.xlsx        # Restaurant reviews
│   └─ labeled.xlsx             # Social context labeled data
├─ templates/
│   └─ index.html        # Main page template
└─ static/
    ├─ css/
    │   └─ styles.css    # Custom styles
    └─ js/
        └─ main.js       # Frontend interaction logic
```

## Technical Approach

### Recommendation Methods
- **TF-IDF Model**: Processes restaurant data and reviews to create a keyword-based recommendation system
- **Sentence-BERT Model**: Uses state-of-the-art transformer embeddings for more semantic content matching
- **Hybrid Features**: Combines textual features with numerical attributes (price, rating, reviews, ranking)

### Zero-Shot Classification
- Classifies restaurants into social contexts (romantic, family, friendship, professional) without requiring explicit training
- Uses two approaches:
  - **BART-MNLI**: Large model fine-tuned for natural language inference
  - **SBERT-Seed**: Sentence embedding similarity with seed sentences for each category

### AI Chatbot
- Powered by Google's Gemini API
- Provides context-aware responses based on:
  - User queries
  - Current weather and traffic conditions
  - Restaurant recommendations
  - Social context preferences

## Installation and Setup

1. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Download the spaCy English language model (for keyword extraction):
   ```
   python -m spacy download en_core_web_trf
   ```

3. Configure environment variables:
   - Create a `.env` file in the project root and add the following API keys:
     ```
     HERE_API_KEY=your_here_api_key_here
     WEATHER_API_KEY=your_openweathermap_api_key_here
     GEMINI_API_KEY=your_gemini_api_key_here
     ```
   - The HERE API key is used for real-time traffic information
   - The OpenWeatherMap API key is used for weather information
   - The Gemini API key is used for the AI chatbot assistant

4. Ensure data and model files are ready:
   - Required data files:
     - `data/results.xlsx`: Contains restaurant information
     - `data/yelp_reviews.xlsx`: Contains restaurant reviews
     - `data/labeled.xlsx`: Contains social context labeled data (optional)
   - Required model files:
     - `models/restaurant_info.pkl`: Restaurant information model
     - `models/restaurant_similarity.pkl`: Similarity matrix
     - `models/tfidf_vectorizer.pkl`: TF-IDF vectorizer
     - `models/count_vectorizer.pkl`: Count vectorizer
     - `models/restaurant_vectors.pkl`: Restaurant vectors
     - `models_sbert/restaurant_info_sbert.pkl`: SBERT restaurant information
     - `models_sbert/restaurant_similarity_sbert.pkl`: SBERT similarity matrix
     - `models_sbert/restaurant_embeddings_sbert.pkl`: SBERT embeddings

5. Start the Flask application:
   ```
   python app.py
   ```

6. Access the application in your browser:
   ```
   http://localhost:5000
   ```

## Usage Guide

### Query-Based Recommendation
1. Type your query in the search box, for example:
   - "Sushi in Manhattan"
   - "I want to eat Italian food in Greenwich Village"
   - "Spicy Sichuan food"
2. Press Enter or click the "Search" button
3. The system will display extracted keywords and a list of recommended restaurants

### Restaurant-Based Recommendation
1. Select a restaurant from the dropdown list
2. Click the "Recommend" button
3. The system will display a list of restaurants similar to your selection

### AI Chatbot Assistant
Use the chat interface to interact with the recommendation system, which considers:
- Your specific needs
- Current time
- Weather conditions
- Real-time traffic information
- Suitable social contexts (dating, family, friend gathering, or business)

### Interactive Map
- View recommended restaurants on the map
- Filter restaurants by social context (romantic, family, friendship, professional)
- Toggle traffic information to see travel conditions
- Use the location button to center the map on your current position

## Model Training

### TF-IDF Model Training
To train the TF-IDF based recommendation model:
```
python Restaurant_Recommend_TF-IDF.py
```

### Sentence-BERT Model Training
To train the Sentence-BERT based recommendation model:
```
python Restaurant_Recommend_SBert.py
```

### Zero-Shot Classification Evaluation
To evaluate the social context classification performance:
```
python test-zeroshot-result.py
```

## Technology Stack

- **Backend**: Flask, Python, spaCy, scikit-learn
- **Frontend**: HTML, CSS, JavaScript, Leaflet maps
- **Recommendation Algorithms**:
  - TF-IDF vectorization with cosine similarity
  - Sentence-BERT embeddings with cosine similarity
  - Hybrid feature combination (text + numerical attributes)
- **NLP Components**:
  - spaCy with PyTextRank for keyword extraction
  - Transformer models for zero-shot classification
  - Sentence-BERT for semantic embeddings
- **External APIs**:
  - OpenWeatherMap API: For real-time weather information
  - HERE Routing API v8: For real-time traffic information
  - Mapbox Maps API: For map visualization and traffic data layer
  - Google Gemini API: For natural language interaction 