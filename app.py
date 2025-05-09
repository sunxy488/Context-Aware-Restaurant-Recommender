from flask import Flask, request, jsonify, render_template
from recommender import recommend, recommend_by_name, load_models, new_df
import pandas as pd
import requests
import json
import datetime
import os
import pickle
import sys
import time
import random
import numpy as np
import hashlib
from flask_cors import CORS
from ratelimit import limits, sleep_and_retry
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from dotenv import load_dotenv

# load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Gemini API configuration
GEMINI_API_KEY = "your_here_api_key_here"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# load restaurant location data
try:
    location_df = pd.read_excel("data/results.xlsx")
    print(f"Loaded {len(location_df)} location data")

    # check required columns
    required_columns = ['Name', 'Latitude', 'Longitude']
    missing_cols = [col for col in required_columns if col not in location_df.columns]
    if missing_cols:
        print(f"Warning: location data missing required columns: {missing_cols}")

    if 'BizId' in location_df.columns:
        location_df.rename(columns={'BizId': 'business_id'}, inplace=True)

    # extract location information
    location_map = {}
    valid_coords = 0
    invalid_coords = 0

    for _, row in location_df.iterrows():
        name = row.get('Name')
        if not isinstance(name, str) or not name.strip():
            continue  # skip invalid name

        # check coordinate validity
        lat = row.get('Latitude')
        lng = row.get('Longitude')

        try:
            if pd.notna(lat) and pd.notna(lng):
                lat = float(lat)
                lng = float(lng)
                if -90 <= lat <= 90 and -180 <= lng <= 180:  # check coordinate range
                    location_map[name] = {
                        'latitude': lat,
                        'longitude': lng,
                        'address': row.get('Address', '')
                    }
                    valid_coords += 1
                else:
                    invalid_coords += 1
            else:
                invalid_coords += 1
        except (ValueError, TypeError):
            invalid_coords += 1

    print(f"Location data loaded: {len(location_map)} restaurants with valid location (valid: {valid_coords}, invalid: {invalid_coords})")

except Exception as e:
    print(f"Failed to load location data: {e}")
    import traceback

    traceback.print_exc()
    location_map = {}


@app.route("/")
def index():
    # render UI with map and input box
    return render_template("index.html")


@app.route("/api/restaurants")
def get_restaurants():
    # return all restaurants list for selection
    restaurants = new_df['restaurant_name'].tolist()
    return jsonify({"restaurants": restaurants})


@app.route("/api/recommend_by_name")
def api_recommend_by_name():
    # recommend by restaurant name
    restaurant_name = request.args.get("name", "")
    if not restaurant_name:
        return jsonify({"error": "Please provide restaurant name", "data": []})

    # call recommend by name function
    results = recommend_by_name(restaurant_name)

    # build return data
    response_data = []
    for name, score in results:
        restaurant_data = new_df[new_df['restaurant_name'] == name].iloc[0]
        data = {
            "name": name,
            "rating": restaurant_data.get('Rating', ''),
            "price": restaurant_data.get('PriceRange', ''),
            "similarity": float(score),
            "reviews": int(restaurant_data.get('review_count', 0)) if str(
                restaurant_data.get('review_count', '0')).isdigit() else 0
        }

        # add location data (if available)
        if name in location_map:
            data['latitude'] = location_map[name]['latitude']
            data['longitude'] = location_map[name]['longitude']
            data['address'] = location_map[name]['address']

        response_data.append(data)

    return jsonify({"data": response_data})


@app.route("/api/recommend")
def api_recommend():
    # get query parameters
    q = request.args.get("query", "")
    if not q:
        return jsonify({"error": "Please provide query content", "data": []})

    # call recommend function
    keywords, results = recommend(q)

    # add location data
    for item in results:
        if item['name'] in location_map:
            item['latitude'] = location_map[item['name']]['latitude']
            item['longitude'] = location_map[item['name']]['longitude']
            item['address'] = location_map[item['name']]['address']

        # ensure reviews field exists
        if 'reviews' not in item:
            # get review count from new_df
            restaurant_data = new_df[new_df['restaurant_name'] == item['name']]
            if not restaurant_data.empty:
                review_count = restaurant_data.iloc[0].get('review_count', '0')
                item['reviews'] = int(review_count) if str(review_count).isdigit() else 0

    # no longer return keywords
    return jsonify({"data": results})


# get weather data function
def get_weather(lat, lng):
    try:
        # use OpenWeatherMap API key from environment variables
        WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
        
        # If API key is not set or is the default value, log a warning
        if not WEATHER_API_KEY or WEATHER_API_KEY == "your_openweathermap_api_key_here":
            print("WARNING: WEATHER_API_KEY not properly set in environment variables")
            return {"description": "Unknown", "temperature": 20}
            
        # use OpenWeatherMap API to get weather data
        weather_api_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&units=metric&appid={WEATHER_API_KEY}"
        print(f"Requesting weather data: {weather_api_url}")

        # add timeout setting to avoid long waiting
        response = requests.get(weather_api_url, timeout=5)
        print(f"Weather API response status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Weather data: {data['weather'][0]['description']}, temperature: {data['main']['temp']}°C")
            return {
                "description": data["weather"][0]["description"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "icon": data["weather"][0]["icon"]
            }
        else:
            print(f"Weather API response error content: {response.text}")
            return {"description": "Unknown", "temperature": 20}
    except requests.exceptions.Timeout:
        print("Weather API request timeout")
        return {"description": "Unknown", "temperature": 20}
    except requests.exceptions.RequestException as e:
        print(f"Weather API request exception: {str(e)}")
        return {"description": "Unknown", "temperature": 20}
    except Exception as e:
        print(f"Failed to get weather data: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"description": "Unknown", "temperature": 20}


# get real-time traffic route information function
def get_route_traffic(origin_lat, origin_lon, dest_lat, dest_lon):
    try:
        # Use HERE API key from environment variables
        HERE_KEY = os.environ.get("HERE_API_KEY")
        
        # If API key is not set or is the default value, log a warning
        if not HERE_KEY or HERE_KEY == "your_here_api_key_here":
            print("WARNING: HERE_API_KEY not properly set in environment variables")
            return {"duration_min": None, "jam_factor": None}
        
        # Call HERE Routing API v8
        url = "https://router.hereapi.com/v8/routes"
        params = {
            "transportMode": "car",
            "origin": f"{origin_lat},{origin_lon}",
            "destination": f"{dest_lat},{dest_lon}",
            "return": "summary,travelSummary",
            "traffic": "true",
            "apikey": HERE_KEY
        }
        
        print(f"Requesting HERE route data: {url} with origin={origin_lat},{origin_lon}, dest={dest_lat},{dest_lon}")
        
        # Add timeout to avoid long waiting
        response = requests.get(url, params=params, timeout=5)
        print(f"HERE API response status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract relevant information from response
            route_summary = data['routes'][0]['sections'][0]['summary']
            
            duration = route_summary.get('duration', 0)  # seconds
            base_duration = route_summary.get('baseDuration', 0)  # seconds without traffic
            jam_factor = route_summary.get('jamFactor', 0)  # 0-10 scale
            
            # Convert duration to minutes
            duration_min = round(duration / 60)
            
            # Create traffic info
            traffic_info = {
                "duration": duration,
                "duration_min": duration_min,
                "base_duration": base_duration,
                "jam_factor": jam_factor
            }
            
            print(f"Traffic data: jam factor {jam_factor}/10, estimated travel time {duration_min} minutes")
            return traffic_info
        else:
            print(f"HERE API response error content: {response.text}")
            return {"duration_min": None, "jam_factor": None}
    except requests.exceptions.Timeout:
        print("HERE API request timeout")
        return {"duration_min": None, "jam_factor": None}
    except requests.exceptions.RequestException as e:
        print(f"HERE API request exception: {str(e)}")
        return {"duration_min": None, "jam_factor": None}
    except Exception as e:
        print(f"Failed to get route traffic data: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"duration_min": None, "jam_factor": None}


@app.route("/api/chatbot", methods=["POST"])
def chatbot():
    data = request.json
    user_message = data.get("message", "")
    user_lat = data.get("latitude")
    user_lng = data.get("longitude")

    # get categorized restaurant data
    categorized_restaurants = data.get("categorized_restaurants", {})
    if categorized_restaurants:
        category_counts = {cat: len(rest) for cat, rest in categorized_restaurants.items()}
        print(f"Received chat request, including categorized restaurant data: {category_counts}")

    # call recommend function to get keywords and recommendations
    keywords, recommendations = recommend(user_message)

    # add location data and traffic info
    for item in recommendations:
        if item['name'] in location_map:
            item['latitude'] = location_map[item['name']]['latitude']
            item['longitude'] = location_map[item['name']]['longitude']
            item['address'] = location_map[item['name']]['address']
            
            # Add real-time traffic information if user location is available
            if user_lat and user_lng and item['latitude'] and item['longitude']:
                try:
                    traffic_info = get_route_traffic(
                        user_lat, user_lng, 
                        item['latitude'], item['longitude']
                    )
                    item['traffic'] = traffic_info
                except Exception as e:
                    print(f"Error getting traffic data for {item['name']}: {str(e)}")
                    item['traffic'] = {"duration_min": None, "jam_factor": None}

    # get weather data
    weather = {"description": "Unknown", "temperature": 20}
    weather_info = "Weather information is temporarily unavailable"
    if user_lat and user_lng:
        try:
            weather = get_weather(user_lat, user_lng)
            weather_info = f"Current weather: {weather['description']}, temperature: {weather['temperature']}°C"
        except Exception as e:
            print(f"Error processing weather data: {str(e)}")
            weather_info = "Weather information is temporarily unavailable"

    # get current time
    now = datetime.datetime.now()
    time_of_day = "morning"
    if 12 <= now.hour < 18:
        time_of_day = "afternoon"
    elif now.hour >= 18:
        time_of_day = "evening"

    # build prompt
    prompt = f"""
        You are a restaurant recommendation assistant. You need to help users choose the most suitable restaurant.

        Current situation:
        - User message: "{user_message}"
        - Current time: {now.strftime('%Y-%m-%d %H:%M')}, {time_of_day}
        - {weather_info}

        The system has recommended the following restaurants based on the user's question:
        """

    if not recommendations:
        prompt += "No matching restaurants found.\n"
    else:
        for i, rest in enumerate(recommendations):
            location_info = ""
            traffic_info = ""
            
            if user_lat and user_lng and 'latitude' in rest and 'longitude' in rest:
                # calculate simple linear distance, only for reference
                distance = ((rest['latitude'] - user_lat) ** 2 + (rest['longitude'] - user_lng) ** 2) ** 0.5
                # convert to approximately kilometers
                distance_km = distance * 111
                location_info = f", approximately {distance_km:.1f} kilometers away"
                
                # Add traffic information if available
                if 'traffic' in rest and rest['traffic']['duration_min'] is not None:
                    jam_factor = rest['traffic']['jam_factor']
                    duration_min = rest['traffic']['duration_min']
                    
                    # Create traffic status description
                    traffic_status = "smooth"
                    if 2 < jam_factor <= 4:
                        traffic_status = "light congestion"
                    elif 4 < jam_factor <= 7:
                        traffic_status = "moderate congestion"
                    elif jam_factor > 7:
                        traffic_status = "heavy congestion"
                        
                    traffic_info = f", current traffic: {traffic_status} (jam factor {jam_factor}/10), estimated travel time {duration_min} minutes"

            prompt += f"{i + 1}. {rest['name']} - Rating: {rest.get('rating', 'N/A')} - Price: {rest.get('price', 'N/A')}{location_info}{traffic_info}\n"

        # add categorized restaurant information
        if categorized_restaurants:
            prompt += "\nThe system also has the following special scene categories of restaurants, please also consider these information when making recommendations:\n"

        # add total number of restaurants in each category
        for category, restaurants in categorized_restaurants.items():
            category_name = {
                'dating': 'romantic date',
                'family': 'family dinner',
                'friend': 'friends gathering',
                'professional': 'business social'
            }.get(category, category)

            # get the number of valid (with location information) restaurants
            valid_restaurants = [r for r in restaurants if 'latitude' in r and 'longitude' in r]

            if valid_restaurants:
                prompt += f"- {category_name} scene suitable restaurants: {len(valid_restaurants)}家\n"

                # add the first 3 restaurants as examples
                if len(valid_restaurants) > 0:
                    prompt += "  such as: "
                    examples = valid_restaurants[:3]
                    example_names = [r['name'] for r in examples]
                    prompt += ", ".join(example_names)
                    prompt += "\n"

    prompt += """
Please analyze the user's question carefully and recommend the most suitable restaurant based on the restaurant list and the current conditions (weather, time, etc.).
If the user's question is not about restaurant recommendations, please politely reply and guide the user back to the restaurant recommendation topic.

Provide recommendations based on the following factors:
- User's specific needs
- Current time (consider whether it is suitable for the current user's dining time)
- Restaurant ratings and prices
- Distance
- Suitable social scenarios (dating, family, friends gathering, or business)
- Traffic conditions (consider recommending closer options and ones with better traffic conditions, you should also tell user real-time traffic information from the user's location to the recommended restaurant)
"""

    # if there is weather information, add weather-related suggestions
    if weather.get("description") != "Unknown":
        prompt += "- Current weather (consider choosing a closer option if the weather is bad)\n"
    else:
        prompt += "Note: Current weather information is temporarily unavailable, please do not mention specific weather conditions in the reply.\n"

    prompt += """
Important format requirements:
1. Insert **two consecutive newline characters (\n\n)** after the intro and after each restaurant paragraph so that every paragraph is separated by a completely blank line.
2. Do not mention or list the extracted keywords in the reply
3. Do not start with "I understand your needs are" or "I understand you want..."
4. Directly recommend 2-3 most suitable restaurants
5. Use a concise paragraph format, use a separate paragraph for each recommended restaurant
6. Explain the recommendation reason briefly, do not elaborate
7. If the user's question is about a specific scene (dating/family/friends/business), prioritize recommending restaurants from these categories

Use a friendly and professional tone, use appropriate paragraph breaks, and answer directly in English.
"""

    # call Gemini API
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 800,
        }
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    try:
        response = requests.post(
            GEMINI_API_URL,
            headers=headers,
            data=json.dumps(payload)
        )

        if response.status_code == 200:
            result = response.json()
            bot_response = result["candidates"][0]["content"]["parts"][0]["text"]
            return jsonify({"response": bot_response, "data": recommendations})
        else:
            error_message = f"Sorry, I cannot process your request. Error: {response.status_code}"
            print(f"Gemini API error: {error_message}")
            print(f"Response content: {response.text}")
            return jsonify({"response": error_message})
    except Exception as e:
        error_message = f"Gemini API call failed: {str(e)}"
        print(error_message)
        import traceback
        traceback.print_exc()
        return jsonify({"response": "Sorry, I cannot respond at the moment. Please try again later."})


@app.route("/api/categorized_restaurants")
def get_categorized_restaurants():
    try:
        # load categorized restaurant data
        categorized_data = pickle.load(open('models/categorized_restaurants.pkl', 'rb'))

        # convert to serializable dictionary format
        categories = {
            'dating': categorized_data['dating'].dropna().tolist(),
            'family': categorized_data['family'].dropna().tolist(),
            'friend': categorized_data['friend'].dropna().tolist(),
            'professional': categorized_data['professional'].dropna().tolist()
        }

        # add coordinate information to each restaurant
        response_data = {}

        # summary count
        total_valid = 0
        total_missing = 0

        for category, restaurants in categories.items():
            response_data[category] = []
            valid_count = 0
            missing_count = 0

            for name in restaurants:
                if name in location_map:
                    location = location_map[name]
                    # check coordinate validity
                    if ('latitude' in location and 'longitude' in location and
                            location['latitude'] is not None and location['longitude'] is not None):
                        try:
                            # try to convert to float to check validity
                            lat = float(location['latitude'])
                            lng = float(location['longitude'])

                            # check if NaN (not a number)
                            if pd.isna(lat) or pd.isna(lng):
                                missing_count += 1
                                continue

                            if -90 <= lat <= 90 and -180 <= lng <= 180:  # check coordinate range
                                valid_count += 1
                                # ensure address is not NaN
                                address = location.get('address', '')
                                if pd.isna(address):
                                    address = ''

                                response_data[category].append({
                                    'name': name,
                                    'latitude': lat,
                                    'longitude': lng,
                                    'address': address
                                })
                            else:
                                missing_count += 1
                        except (ValueError, TypeError):
                            missing_count += 1
                    else:
                        missing_count += 1
                else:
                    missing_count += 1

            total_valid += valid_count
            total_missing += missing_count

        # print summary information
        print(
            f"Categorized restaurant data: valid:{total_valid}, missing:{total_missing}, total markers:{sum(len(markers) for markers in response_data.values())}")

        return jsonify(response_data)
    except FileNotFoundError:
        print(f"File not found: models/categorized_restaurants.pkl")
        return jsonify({"error": "Categorized restaurant data file not found", "data": {}})
    except Exception as e:
        print(f"Failed to get categorized restaurant data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to get categorized restaurant data", "details": str(e), "data": {}})


@app.route("/api/here_traffic_key")
def get_here_traffic_key():
    HERE_KEY = os.environ.get("HERE_API_KEY")
    
    # if API key is not set or is the default value, log a warning
    if not HERE_KEY or HERE_KEY == "your_here_api_key_here":
        return jsonify({"error": "HERE_API_KEY not properly set in environment variables"})
    
    # return HERE API key and tile URL
    return jsonify({
        "apiKey": HERE_KEY,
        "tileUrl": "https://traffic.maps.hereapi.com/v3/flow/mc"
    })


@app.route("/api/traffic_info")
def get_traffic_info():
    # get query parameters
    o_lat = request.args.get("origin_lat")
    o_lon = request.args.get("origin_lon")
    d_lat = request.args.get("dest_lat")
    d_lon = request.args.get("dest_lon")
    
    # check if all required parameters are provided
    if not all([o_lat, o_lon, d_lat, d_lon]):
        return jsonify({"error": "Missing parameters. Required: origin_lat, origin_lon, dest_lat, dest_lon"})
        
    try:
        # get traffic information
        traffic_info = get_route_traffic(float(o_lat), float(o_lon), float(d_lat), float(d_lon))
        
        # add origin and destination coordinates
        traffic_info['origin'] = {'lat': float(o_lat), 'lon': float(o_lon)}
        traffic_info['destination'] = {'lat': float(d_lat), 'lon': float(d_lon)}
        
        # add traffic status based on jam factor
        jam_factor = traffic_info.get('jam_factor', 0)
        if jam_factor < 2:
            traffic_info['status'] = "smooth"
            traffic_info['status_color'] = "#4CAF50"
        elif jam_factor <= 4:
            traffic_info['status'] = "light congestion"
            traffic_info['status_color'] = "#FFC107"
        elif jam_factor <= 7:
            traffic_info['status'] = "moderate congestion"
            traffic_info['status_color'] = "#FF9800"
        else:
            traffic_info['status'] = "heavy congestion"
            traffic_info['status_color'] = "#F44336"
        
        return jsonify(traffic_info)
        
    except Exception as e:
        print(f"Failed to get traffic info: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
