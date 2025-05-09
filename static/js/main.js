// init map - default location is New York
const map = L.map('map', {
    zoomControl: true,
    attributionControl: true
}).setView([40.75171244845984, -73.98179241229592], 13);

// use colorful map style
L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    maxZoom: 19,
    minZoom: 10,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
}).addTo(map);

// HERE Traffic Tiles layer - will be initialized later
let trafficTileLayer = null;
let hereApiKey = null;
let trafficInfo = {};
let trafficRoute = null;
let isTrafficLayerVisible = false;

// add location control
L.control.locate({
    position: 'topleft',
    strings: {
        title: "Show my location"
    },
    locateOptions: {
        maxZoom: 15
    }
}).addTo(map);

// user location info
let userLocation = {
    latitude: null,
    longitude: null
};

// current recommended restaurants list
let currentRecommendations = [];

// store markers on the map
let markers = [];
// store categorized restaurant markers
let categoryMarkers = {
    dating: [],
    family: [],
    friend: [],
    professional: []
};
// categorized restaurant data
let categoryData = {};

// try to get user location and set map center
function getUserLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function (position) {
                // successfully get location
                userLocation.latitude = position.coords.latitude;
                userLocation.longitude = position.coords.longitude;

                map.setView([userLocation.latitude, userLocation.longitude], 15);

                // add a marker at user location
                L.marker([userLocation.latitude, userLocation.longitude])
                    .addTo(map)
                    .openPopup()
                    .bindTooltip('My location', { direction: 'top', offset: [-15, -15] });

                // load HERE API key
                loadHereApiKey();
            },
            function (error) {
                // failed to get location
                console.error("Failed to get location:", error.message);

                // set default location to New York
                userLocation.latitude = 40.75171244845984;
                userLocation.longitude = -73.98179241229592;

                // show error message
                const errorMessages = {
                    1: "You have denied location sharing. Recommendations will use the default location.",
                    2: "Location information is unavailable. Recommendations will use the default location.",
                    3: "Location request timed out. Recommendations will use the default location."
                };

                const message = errorMessages[error.code] || "Unable to get your location. Recommendations will use the default location.";

                // consider showing a prompt
                alert(message);

                // load HERE API key anyway
                loadHereApiKey();
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    } else {
        console.error("Your browser doesn't support geolocation");

        // set default location to New York
        userLocation.latitude = 40.75171244845984;
        userLocation.longitude = -73.98179241229592;

        // load HERE API key anyway
        loadHereApiKey();
    }
}

// load HERE API key from server
function loadHereApiKey() {
    fetch('/api/here_traffic_key')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('HERE API key error:', data.error);
                return;
            }

            hereApiKey = data.apiKey;
            console.log('HERE API key loaded successfully');

            // initialize traffic tile layer
            initTrafficTileLayer();
        })
        .catch(error => {
            console.error('Failed to load HERE API key:', error);
        });
}

// initialize traffic tile layer
function initTrafficTileLayer() {
    // remove existing layer if any
    if (trafficTileLayer) {
        map.removeLayer(trafficTileLayer);
        trafficTileLayer = null;
    }

    console.log('Initializing traffic layer');

    // Using Mapbox's traffic layer
    const mapboxToken = 'pk.eyJ1IjoieGlhb3l1c3VuMjAyNCIsImEiOiJjbWFlNXR0b3IwM3NsMmlvb2FqYW1xb3RoIn0.zFiPFkuUil8Ewx8gJLiKhg';

    // Create layers for different traffic conditions
    trafficTileLayer = L.layerGroup();

    // Define colors for different traffic congestion levels
    const congestionColors = {
        'low': '#2ECC40',      // Green - Smooth
        'moderate': '#FF851B', // Orange - Moderate
        'heavy': '#FF4136',    // Red - Congested
        'severe': '#85144b'    // Deep red - Severely congested
    };

    // Add Mapbox traffic tile layer
    const trafficBaseLayer = L.tileLayer(
        'https://api.mapbox.com/styles/v1/mapbox/traffic-day-v2/tiles/{z}/{x}/{y}?access_token=' + mapboxToken,
        {
            maxZoom: 20,
            minZoom: 5,
            opacity: 0.75,
            attribution: '© Mapbox'
        }
    );

    // Add layer to the layer group
    trafficBaseLayer.addTo(trafficTileLayer);

    // Create traffic legend
    const trafficLegend = L.control({ position: 'bottomleft' });

    trafficLegend.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'info legend traffic-legend');
        div.innerHTML = '<h4>Traffic Conditions</h4>';

        for (const level in congestionColors) {
            div.innerHTML +=
                '<div class="legend-item">' +
                '<i style="background:' + congestionColors[level] + '"></i> ' +
                getLevelLabel(level) +
                '</div>';
        }

        return div;
    };

    function getLevelLabel(level) {
        switch (level) {
            case 'low': return 'Smooth';
            case 'moderate': return 'Moderate';
            case 'heavy': return 'Congested';
            case 'severe': return 'Severely Congested';
            default: return level;
        }
    }

    map.legendControl = trafficLegend;

    // Add layer error event handler
    trafficBaseLayer.on('tileerror', function (error, tile) {
        console.error('Traffic layer loading error:', error, tile ? tile.src : 'Unknown');
    });

    // Add layer load event handler
    trafficBaseLayer.on('load', function () {
        console.log('Traffic layer loaded successfully');
    });

    // Add CSS style to the page
    if (!document.getElementById('traffic-legend-style')) {
        const style = document.createElement('style');
        style.id = 'traffic-legend-style';
        style.innerHTML = `
            .traffic-legend {
                background: white;
                padding: 10px;
                border-radius: 5px;
                box-shadow: 0 1px 5px rgba(0,0,0,0.4);
                z-index: 1000;
            }
            .traffic-legend h4 {
                margin: 0 0 10px 0;
                font-size: 14px;
                text-align: center;
                font-weight: bold;
                color: #333;
            }
            .legend-item {
                display: flex;
                align-items: center;
                margin-bottom: 5px;
                font-size: 12px;
            }
            .legend-item i {
                width: 20px;
                height: 4px;
                margin-right: 8px;
                border-radius: 2px;
            }
            /* Ensure the traffic legend has enough space from other legends */
            .leaflet-bottom.leaflet-left .leaflet-control {
                margin-bottom: 10px;
            }
            /* Use layers to ensure the traffic legend displays above other legends */
            .leaflet-control.traffic-legend {
                z-index: 1001 !important;
                margin-bottom: 220px !important;
            }
        `;
        document.head.appendChild(style);
    }

    console.log('Traffic layer initialization complete');
}

// load page after 2 seconds
document.addEventListener('DOMContentLoaded', function () {
    setTimeout(getUserLocation, 2000);

    // load restaurants list after page loaded
    loadRestaurants();

    // load categorized restaurant data
    loadCategorizedRestaurants();

    // set category checkbox event listener
    setupCategoryCheckboxes();

    // Set traffic button click event
    document.getElementById('traffic-toggle-btn').addEventListener('click', toggleTrafficLayer);
});

// disable some interaction features
map.touchZoom.disable();
map.doubleClickZoom.disable();
map.boxZoom.disable();
if (map.tap) map.tap.disable();

// clear all markers on the map
function clearMarkers() {
    markers.forEach(m => map.removeLayer(m));
    markers = [];
}

// clear specific category markers
function clearCategoryMarkers(category) {
    if (categoryMarkers[category]) {
        categoryMarkers[category].forEach(m => map.removeLayer(m));
        categoryMarkers[category] = [];
    }
}

// clear all category markers
function clearAllCategoryMarkers() {
    for (const category in categoryMarkers) {
        clearCategoryMarkers(category);
    }
}

// clear result list and markers
function clearResults() {
    document.getElementById('result-list').innerHTML = '';
    clearMarkers();

    // clear current recommended list
    currentRecommendations = [];
}

// load restaurants list
function loadRestaurants() {
    const select = document.getElementById('restaurant-select');
    select.innerHTML = '<option value="">-- Loading Restaurants... --</option>';

    fetch('/api/restaurants')
        .then(response => response.json())
        .then(data => {
            select.innerHTML = '<option value="">-- Select Restaurant --</option>';
            data.restaurants.forEach(restaurant => {
                const option = document.createElement('option');
                option.value = restaurant;
                option.textContent = restaurant;
                select.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Failed to load restaurants:', error);
            select.innerHTML = '<option value="">-- Failed to Load --</option>';
        });
}

// handle recommend by restaurant name event
document.getElementById('btn-recommend').addEventListener('click', recommendByRestaurant);

// recommend by restaurant name
function recommendByRestaurant() {
    const select = document.getElementById('restaurant-select');
    const restaurantName = select.value;
    if (!restaurantName) {
        alert('Please select a restaurant');
        return;
    }

    // show loading status
    document.getElementById('result-list').innerHTML = '<div class="loading">Finding recommendations...</div>';
    clearMarkers();

    // call API
    fetch(`/api/recommend_by_name?name=${encodeURIComponent(restaurantName)}`)
        .then(r => r.json())
        .then(json => {
            // clear loading status
            document.getElementById('result-list').innerHTML = '';

            if (!json.data || json.data.length === 0) {
                document.getElementById('result-list').innerHTML = '<div>No similar restaurants found</div>';
                return;
            }

            // save current recommended results
            currentRecommendations = json.data;

            // add title
            const titleDiv = document.createElement('div');
            titleDiv.className = 'result-title';
            titleDiv.innerHTML = `<b>Restaurant Recommendations Based on "${restaurantName}":</b>`;
            document.getElementById('result-list').appendChild(titleDiv);

            // show recommended results
            displayResults(json.data);
            // update map markers
            updateMapMarkers(json.data);
        })
        .catch(error => {
            console.error(error);
            document.getElementById('result-list').innerHTML = '<div>Error while getting recommendations</div>';
        });
}

// show recommended results list
function displayResults(data) {
    // add to list
    data.forEach((item, index) => {
        const resultItem = document.createElement('div');
        resultItem.className = 'restaurant-item';
        resultItem.innerHTML = `
          <div class="restaurant-name">${index + 1}. ${item.name}</div>
          <div class="restaurant-info">
            ${item.rating ? `Rating: ${item.rating}` : ''}
            ${item.price ? ` · Price: ${item.price}` : ''}
            ${item.reviews !== undefined ? ` · Reviews: ${item.reviews}` : ''}
          </div>
        `;

        // if has location info, add click event
        if (item.latitude && item.longitude) {
            resultItem.addEventListener('click', () => {
                // find corresponding marker
                const markerIndex = markers.findIndex(m =>
                    m.getLatLng().lat === item.latitude &&
                    m.getLatLng().lng === item.longitude);

                if (markerIndex !== -1) {
                    // if found corresponding marker, open popup
                    markers[markerIndex].openPopup();
                }
            });
        }

        document.getElementById('result-list').appendChild(resultItem);
    });
}

// update markers on the map
function updateMapMarkers(data) {
    // clear existing markers
    clearMarkers();

    // clear traffic route if any
    clearTrafficRoute();

    // filter out items without location info
    const validData = data.filter(item => item.latitude && item.longitude);

    if (validData.length === 0) return;

    // custom restaurant marker icon
    const restaurantIcon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    // add new markers
    validData.forEach(item => {
        const m = L.marker([item.latitude, item.longitude], { icon: restaurantIcon })
            .addTo(map)
            .bindPopup(`
                <div class="popup-content">
                    <b>${item.name}</b>
                    ${item.address ? `<br>${item.address}` : ''}
                    ${item.rating ? `<br>Rating: ${item.rating}` : ''}
                    ${item.price ? `<br>Price: ${item.price}` : ''}
                    ${item.reviews !== undefined ? `<br>Reviews: ${item.reviews}` : ''}
                    <br><button class="traffic-btn" onclick="showTrafficTo(${item.latitude}, ${item.longitude}, '${item.name}')">Show Traffic</button>
                </div>
            `);

        markers.push(m);
    });

    // adjust map view to show all markers
    if (markers.length > 0) {
        const group = L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
    }

    // ensure legend is displayed correctly, hide recommendation item
    const recommendationItem = document.querySelector('.recommendation-item');
    if (recommendationItem) {
        recommendationItem.style.display = 'none';
    }

    // update legend display
    updateLegendDisplay();
}

// get DOM elements
const chatButton = document.getElementById('chat-button');
const chatContainer = document.getElementById('chat-container');
const chatClose = document.querySelector('.chat-close');
const chatMessages = document.querySelector('.chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');

// open/close chat box
chatButton.addEventListener('click', () => {
    chatContainer.classList.toggle('hidden');
    if (!chatContainer.classList.contains('hidden')) {
        chatInput.focus();
    }
});

// close button
chatClose.addEventListener('click', () => {
    chatContainer.classList.add('hidden');
});

// send message
function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    // add user message to chat interface
    addMessage(message, 'user');
    chatInput.value = '';

    // show typing status
    showTypingIndicator();

    // prepare data object to send to server, including categorized restaurant data
    const requestData = {
        message: message,
        latitude: userLocation.latitude,
        longitude: userLocation.longitude,
        // add four categories of restaurant data
        categorized_restaurants: categoryData
    };

    // send message to server
    fetch('/api/chatbot', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
    })
        .then(response => response.json())
        .then(data => {
            // hide typing status
            hideTypingIndicator();

            // add bot reply
            addMessage(data.response, 'bot');

            // clear current recommended list
            clearResults();

            // if has recommended data, show in map and list
            if (data.data && data.data.length > 0) {
                // save current recommended results
                currentRecommendations = data.data;

                // show recommended results
                displayResults(data.data);

                // update map markers
                updateMapMarkers(data.data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            hideTypingIndicator();
            addMessage('Sorry, I encountered an issue. Please try again later.', 'bot');
        });
}

// send button click event
chatSend.addEventListener('click', sendMessage);

// chat input keypress event
chatInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// add message to chat interface
function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = text;

    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);

    // scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// show typing status
function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-typing';
    typingDiv.id = 'typing-indicator';

    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';

    for (let i = 0; i < 3; i++) {
        const dot = document.createElement('div');
        dot.className = 'typing-dot';
        typingIndicator.appendChild(dot);
    }

    typingDiv.appendChild(typingIndicator);
    chatMessages.appendChild(typingDiv);

    // scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// hide typing status
function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// load categorized restaurant data
function loadCategorizedRestaurants() {
    fetch('/api/categorized_restaurants')
        .then(response => response.json())
        .then(data => {
            // check if there is an error
            if (data.error) {
                console.error('Categorized restaurant data loading error:', data.error, data.details || '');
                categoryData = {}; // set to empty object
                return;
            }

            // data validity check
            if (!data || Object.keys(data).length === 0) {
                console.warn('No valid categorized restaurant data');
                categoryData = {};
                return;
            }

            categoryData = data;
            console.log('Categorized restaurant data loaded successfully');
        })
        .catch(error => {
            console.error('Categorized restaurant data loading error:', error);
            categoryData = {};
        });
}

// set category checkbox event listener
function setupCategoryCheckboxes() {
    const checkboxes = document.querySelectorAll('input[name="category"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            const category = this.value;
            // update legend display
            updateLegendDisplay();

            if (this.checked) {
                showCategoryMarkers(category);
            } else {
                clearCategoryMarkers(category);
            }
        });
    });
}

// update legend display
function updateLegendDisplay() {
    const legend = document.getElementById('map-legend');
    const checkboxes = document.querySelectorAll('input[name="category"]:checked');

    // if no category is selected, hide legend
    if (checkboxes.length === 0) {
        legend.style.display = 'none';
        return;
    }

    // show legend
    legend.style.display = 'block';

    // hide all category legend items
    document.querySelectorAll('.dating-item, .family-item, .friend-item, .professional-item, .recommendation-item').forEach(item => {
        item.style.display = 'none';
    });

    // hide recommendation legend item
    // only show selected category legend
    checkboxes.forEach(checkbox => {
        const category = checkbox.value;
        const itemClass = `.${category}-item`;
        const legendItem = document.querySelector(itemClass);
        if (legendItem) {
            legendItem.style.display = 'flex';
        }
    });
}

// show markers for specific category
function showCategoryMarkers(category) {
    // first clear markers for this category
    clearCategoryMarkers(category);

    if (!categoryData[category] || categoryData[category].length === 0) {
        console.warn(`No ${category} category restaurant data or data is empty`);
        return;
    }

    // set different category circle colors
    const colors = {
        dating: '#E91E63',   // pink
        family: '#4CAF50',   // green
        friend: '#2196F3',   // blue
        professional: '#FF9800'  // orange
    };

    // check how many restaurants have latitude and longitude data
    let validCount = 0;
    let invalidList = [];

    // create circle markers
    categoryData[category].forEach((item, index) => {
        if (item.latitude && item.longitude) {
            try {
                const lat = parseFloat(item.latitude);
                const lng = parseFloat(item.longitude);

                if (isNaN(lat) || isNaN(lng)) {
                    invalidList.push(item.name);
                    return;
                }

                const circleMarker = L.circleMarker([lat, lng], {
                    radius: 8,
                    fillColor: colors[category],
                    color: '#fff',
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                }).addTo(map);

                // add popup window with traffic button
                circleMarker.bindPopup(`
                    <div class="popup-content">
                        <b>${item.name}</b>
                        <br>Category: ${category.charAt(0).toUpperCase() + category.slice(1)}
                        ${item.address ? `<br>${item.address}` : ''}
                        <br><button class="traffic-btn" onclick="showTrafficTo(${lat}, ${lng}, '${item.name.replace(/'/g, "\\'")}')">Show Traffic</button>
                    </div>
                `);

                // save marker reference
                categoryMarkers[category].push(circleMarker);
                validCount++;
            } catch (e) {
                console.error(`Error creating marker for ${item.name}:`, e);
                invalidList.push(item.name);
            }
        } else {
            invalidList.push(item.name);
        }
    });

    if (invalidList.length > 5) {
        console.warn(`${category} category: ${validCount} restaurants displayed, ${invalidList.length} restaurants not displayed due to coordinate issues`);
    }
}

// clear traffic route
function clearTrafficRoute() {
    if (trafficRoute) {
        map.removeLayer(trafficRoute);
        trafficRoute = null;
    }
}

// toggle traffic layer visibility
function toggleTrafficLayer() {
    console.log('Toggling traffic layer, current status:', isTrafficLayerVisible ? 'visible' : 'hidden');

    if (!trafficTileLayer) {
        console.log('Traffic layer not initialized, initializing...');
        initTrafficTileLayer();

        if (!trafficTileLayer) {
            console.error('Traffic layer initialization failed');
            return;
        }
    }

    if (isTrafficLayerVisible) {
        console.log('Hiding traffic layer');
        map.removeLayer(trafficTileLayer);
        if (map.legendControl) {
            map.removeControl(map.legendControl);
        }
        isTrafficLayerVisible = false;
        document.getElementById('traffic-toggle-btn').classList.remove('active');
    } else {
        console.log('Showing traffic layer');
        map.addLayer(trafficTileLayer);

        // Add traffic legend to bottom left of map
        if (map.legendControl) {
            map.legendControl.addTo(map);
        }

        isTrafficLayerVisible = true;
        document.getElementById('traffic-toggle-btn').classList.add('active');
    }
}

// global function to show traffic to a restaurant
window.showTrafficTo = function (lat, lon, name) {
    if (!userLocation.latitude || !userLocation.longitude) {
        alert('Your location is not available. Cannot show traffic information.');
        return;
    }

    // clear existing traffic route
    clearTrafficRoute();

    // loading indicator
    const popups = document.querySelectorAll('.leaflet-popup-content');
    popups.forEach(popup => {
        if (popup.innerHTML.includes(name)) {
            const btn = popup.querySelector('.traffic-btn');
            if (btn) {
                btn.textContent = 'Loading...';
                btn.disabled = true;
            }
        }
    });

    // fetch traffic info from server
    fetch(`/api/traffic_info?origin_lat=${userLocation.latitude}&origin_lon=${userLocation.longitude}&dest_lat=${lat}&dest_lon=${lon}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Traffic info error:', data.error);
                alert('Failed to get traffic information.');
                return;
            }

            // store traffic info
            trafficInfo = data;

            // create a simple line with color based on traffic status
            trafficRoute = L.polyline([
                [userLocation.latitude, userLocation.longitude],
                [lat, lon]
            ], {
                color: data.status_color || '#FF0000',
                weight: 5,
                opacity: 0.8,
                dashArray: '10, 10'
            }).addTo(map);

            // add popup to the route
            trafficRoute.bindPopup(`
                <div class="traffic-popup">
                    <h4>Traffic to ${name}</h4>
                    <p>Status: <span style="color: ${data.status_color}">${data.status}</span></p>
                    <p>Travel time: ${data.duration_min} minutes</p>
                    <p>Jam factor: ${data.jam_factor}/10</p>
                </div>
            `).openPopup();

            // ensure traffic tiles are visible
            if (!isTrafficLayerVisible && trafficTileLayer) {
                map.addLayer(trafficTileLayer);

                // Add traffic legend to bottom left of map
                if (map.legendControl) {
                    map.legendControl.addTo(map);
                }

                isTrafficLayerVisible = true;
                document.getElementById('traffic-toggle-btn').classList.add('active');
            }

            // reset button
            popups.forEach(popup => {
                if (popup.innerHTML.includes(name)) {
                    const btn = popup.querySelector('.traffic-btn');
                    if (btn) {
                        btn.textContent = 'Show Traffic';
                        btn.disabled = false;
                    }
                }
            });
        })
        .catch(error => {
            console.error('Failed to load traffic info:', error);
            alert('Failed to get traffic information.');

            // reset button
            popups.forEach(popup => {
                if (popup.innerHTML.includes(name)) {
                    const btn = popup.querySelector('.traffic-btn');
                    if (btn) {
                        btn.textContent = 'Show Traffic';
                        btn.disabled = false;
                    }
                }
            });
        });
} 