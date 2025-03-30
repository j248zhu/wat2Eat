# -*- coding: utf-8 -*-
import streamlit as st
import googlemaps
from datetime import datetime
from openai import OpenAI
import requests
from streamlit_geolocation import streamlit_geolocation

# Initialize OpenAI and Google Maps API clients
client = OpenAI(api_key=st.secrets["openai"]["api_key"])
gmaps = googlemaps.Client(key=st.secrets["google"]["api_key"])

# Popular cuisines and dishes
popular_cuisines = [
    "Canadian", "Italian", "Chinese", "Indian", "Japanese", "Korean",
    "Middle Eastern", "Vietnamese", "Caribbean", "Mexican", "French",
    "Greek", "Thai", "Ethiopian", "American", "Spanish"
]

popular_dishes = [
    "Poutine", "Hamburger", "Hot Dog", "Fried Chicken", "Pizza",
    "Pasta", "Sushi", "Ramen", "Dim Sum", "Peking Duck",
    "Tandoori Chicken", "Biryani", "Shawarma", "Pho",
    "Jerk Chicken", "Tacos", "Burritos", "Pad Thai",
    "Tom Yum Soup", "Doro Wat with Injera",
    "Croissant", "Gyros", "Moussaka",
    "Ice Cream", "Waffles", "Chocolate Cake",
    "Apple Pie", "Cheesecake", "Churros"
]

# Initialize session state for tracking results
if 'results' not in st.session_state:
    st.session_state.results = []
if 'shown_places' not in st.session_state:
    st.session_state.shown_places = set()

# Display app title and current date/time
st.title("Wat2Eat - Find Restaurants")
current_time = datetime.now().strftime("%A, %B %d, %Y, %I:%M %p %Z")
st.write(f"**Current Date/Time**: {current_time}")

# Function to get user's current location using Google Maps Geolocation API
def get_user_location():
    if 'last_location' in st.session_state:
        return st.session_state.last_location  # Return cached data
    
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={st.secrets['google']['api_key']}"
    response = requests.post(url)
    if response.status_code == 200:
        location_data = response.json()
        lat = location_data['location']['lat']
        lon = location_data['location']['lng']
        st.session_state.last_location = (lat, lon)  # Cache the result
        return lat, lon
    else:
        st.error("Could not retrieve your current location. Please input it manually.")
        return None, None


# Function to get coordinates from a user-entered location using Google Maps Geocoding API
def get_coordinates_from_location(location_query):
    geocode_result = gmaps.geocode(location_query)
    if geocode_result:
        lat = geocode_result[0]['geometry']['location']['lat']
        lon = geocode_result[0]['geometry']['location']['lng']
        return lat, lon
    else:
        st.error(f"Could not find coordinates for '{location_query}'.")
        return None, None

# Step 1: Privacy-focused location handling
st.subheader("Find Restaurants")

# Initialize session state
if 'user_coords' not in st.session_state:
    st.session_state.user_coords = None

# Inputs
user_location_input = st.text_input(
    "Enter a location (e.g., 'CN Tower, Toronto' or 'Yonge & Bloor, Toronto'):",
    placeholder="Landmark or intersection, City"
)
use_current_location = st.checkbox("Use my current location", value=True)

# Unified geolocation button
if use_current_location and st.button("Find Near Me"):
    with st.spinner("Locating you (check browser permissions)..."):
        geolocation = streamlit_geolocation()
        if geolocation and geolocation['latitude']:
            st.session_state.user_coords = (geolocation['latitude'], geolocation['longitude'])
            print(f"DEBUG: Using location {st.session_state.user_coords}")  # Console only
            st.success("Ready to search!")
        else:
            st.error("Couldn't access location. Please enter an address.")

# Manual location fallback
elif user_location_input.strip():
    st.session_state.user_coords = get_coordinates_from_location(user_location_input)
    print(f"DEBUG: Using manual location {st.session_state.user_coords}")  # Console only

# Error prevention
try:
    if st.session_state.user_coords:
        lat, lon = st.session_state.user_coords  # Now safely defined
        # Your restaurant search logic here
except NameError:
    st.error("Location service unavailable. Please try again.")
    st.session_state.user_coords = None



# Step 2: Pre-processing - Collect user preferences
st.header("Your Preferences")

# Dietary restrictions
st.subheader("Dietary Restrictions")
nut_allergy = st.checkbox("I have a nut allergy")
fish_allergy = st.checkbox("I have a fish allergy")
shellfish_allergy = st.checkbox("I have a shellfish allergy")
vegetarian = st.checkbox("I prefer vegetarian options")
halal = st.checkbox("I prefer halal options")
spice_tolerance = st.slider("Spice Tolerance Level:", 0, 4, 2, format="%d (0: None, 4: Spicy)")
other_allergy = st.text_input("Other allergies (please specify):")

# Price preferences
st.subheader("Price Preferences")
price_level_display = ["\$", "\$\$", "\$\$\$", "\$\$\$\$"]
price_level_logic = [1, 2, 3, 4]  # Corresponding values for Google Maps API's price_level
price_level_choice = st.radio("Select price range:", price_level_display)
price_level_index = price_level_display.index(price_level_choice)
selected_price_level = price_level_logic[price_level_index]

# Search radius preference
st.subheader("Search Radius")
search_radius_km = st.slider(
    label="Select search radius (max 20 km):",
    min_value=1,
    max_value=20,
    value=3,
    step=1,
) * 1000  # Convert km to meters for Google Maps API

# Cuisine/Dish preference
st.subheader("What Are You Craving?")
user_query = st.text_input("What cuisine or dish are you craving? (Hit Enter to search)")
st.write("Please give the program a few seconds to run, it will display the top 3 results and you can hit \"Refine Search\" to repeat your existing filters.")
st.write("If there are no more results, you will need to modify your search using the \"Modify Inputs\" button.")
st.write("If you're unsure of what you want, click or tap \"Show Popular Options\".")

if not user_query:
    if st.button("Show Popular Options"):
        st.write("### Popular Cuisines:")
        for cuisine in popular_cuisines:
            st.write(f"- {cuisine}")
        st.write("### Popular Dishes:")
        for dish in popular_dishes:
            st.write(f"- {dish}")

# Step 3: Search for restaurants based on preferences using Google Maps API
filtered_results = []

if lat is not None and lon is not None:
    query = f"{user_query} restaurants near me" if user_query else f"restaurants near me"
    
    response = gmaps.places_nearby(
        location=(lat, lon),  # Use coordinates from Geolocation or Geocoding API
        radius=search_radius_km,
        type="restaurant",
        keyword=user_query,
        min_price=selected_price_level,
        max_price=selected_price_level,
    )
    
    # Filter results based on dietary restrictions
    filtered_results = [
        place for place in response.get("results", [])
        if place["place_id"] not in st.session_state.shown_places and (
            not fish_allergy or ("sushi" not in place["name"].lower() and 
                                 "seafood" not in place["name"].lower())
        ) and (
            not nut_allergy or ("nuts" not in place.get("description", "").lower())
        ) and (
            spice_tolerance == 0 or ("spicy" not in place.get("description", "").lower())
        )
    ]
    
    if filtered_results:
        # Display top 3 restaurants with OpenAI recommendations for dishes
        top_restaurants = filtered_results[:3]
        
        for i, place in enumerate(top_restaurants):
            restaurant_name = place.get('name')
            cuisine_type = user_query if user_query else 'unknown cuisine'
            price_tier_index = place.get('price_level', -1)  # Get price level (-1 if missing)
            price_tier_display = price_level_display[price_tier_index - 1] if price_tier_index > 0 else 'N/A'
            
            google_maps_link = f"https://www.google.com/maps/place/?q=place_id:{place.get('place_id')}"
            
            # Ask GPT for best value dishes at this restaurant based on name and cuisine type
            gpt_prompt_dishes = f"What are some of the best value or most popular dishes to get at {restaurant_name}, which serves {cuisine_type}?"
            gpt_response_dishes = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": gpt_prompt_dishes}
                ]
            )
            best_value_dishes = gpt_response_dishes.choices[0].message.content
            
            # Display restaurant info
            st.write(f"**{i+1}. {restaurant_name}**")
            st.write(f"Address: {place.get('vicinity', 'N/A')}")
            st.write(f"Rating: {place.get('rating', 'N/A')} ⭐️")
            st.write(f"Price Tier: {price_tier_display}")
            st.markdown(f"[View on Google Maps]({google_maps_link})")
            
            # Display best value dishes recommendation
            st.write(f"Dishes to Try: {best_value_dishes}")
            st.write("---")

# Step 4: Add buttons for refining search or modifying inputs
if filtered_results:
    if st.button("Refine Search"):
        # Remove already shown places from session state and re-run search
        for place in filtered_results[:3]:
            st.session_state.shown_places.add(place["place_id"])
        st.rerun()
else:
    st.write("No results for what you're searching for, please try again and modify your inputs.")
    if st.button("Modify Inputs"):
        # Allow user to go back and modify inputs
        pass

