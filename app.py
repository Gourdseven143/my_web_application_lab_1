from flask import Flask, render_template_string, request
import osmnx as ox
import networkx as nx
from geopy.geocoders import Nominatim
from folium import Map, Marker, Icon, PolyLine, Figure
import os

# -----------------------------
# 1️⃣ Initialize Flask app and geocoder
# -----------------------------
app = Flask(__name__)
geolocator = Nominatim(user_agent="kl_route_app")

# -----------------------------
# 2️⃣ Geocoding function
# -----------------------------
def smart_geocode(location_name):
    try:
        query = f"{location_name}, Malaysia"
        location = geolocator.geocode(query, timeout=10, country_codes="MY", addressdetails=True)
        return location
    except Exception as e:
        print("Geocoding error:", e)
        return None

# -----------------------------
# 3️⃣ Home page
# -----------------------------
@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kuala Lumpur Route Finder</title>
        <style>
            body { font-family: Arial; text-align: center; margin-top: 50px; }
            input { padding: 8px; margin: 5px; width: 250px; }
            button { padding: 8px 16px; }
            iframe { margin-top: 20px; border: none; }
        </style>
    </head>
    <body>
        <h2>🚗 Shortest Route Finder (Kuala Lumpur)</h2>
        <form action="/route" method="post">
            <input type="text" name="pointA" placeholder="Enter starting point (e.g. UPM)" required><br>
            <input type="text" name="pointB" placeholder="Enter destination (e.g. KLCC)" required><br>
            <button type="submit">Find Route</button>
        </form>
        {% if error %}
            <p style="color: red;">❌ {{ error }}</p>
        {% endif %}
        {% if map_html %}
            <iframe src="{{ map_html }}" width="90%" height="600"></iframe>
        {% endif %}
    </body>
    </html>
    ''')

# -----------------------------
# 4️⃣ Route calculation page
# -----------------------------
@app.route('/route', methods=['POST'])
def route():
    pointA = request.form['pointA']
    pointB = request.form['pointB']

    # Automatic geocoding
    locA = smart_geocode(pointA)
    locB = smart_geocode(pointB)

    if not locA or not locB:
        return render_template_string('''
            <p>❌ Could not find the entered location. Please check spelling or provide a more complete name.</p>
            <a href="/">⬅ Back</a>
        ''')

    # Load Kuala Lumpur road network (30km radius)
    print("📍 Loading road network...")
    G = ox.graph_from_point(
        (3.1390, 101.6869),
        dist=30000,
        network_type="drive"
    )

    # Nearest nodes
    orig_node = ox.distance.nearest_nodes(G, locA.longitude, locA.latitude)
    dest_node = ox.distance.nearest_nodes(G, locB.longitude, locB.latitude)

    # Shortest path
    print("🚗 Calculating shortest path...")
    route = nx.astar_path(G, orig_node, dest_node, weight='length')

    # Total distance
    route_length_m = nx.path_weight(G, route, weight='length')
    route_length_km = route_length_m / 1000

    # Create Folium map
    center_lat = (locA.latitude + locB.latitude) / 2
    center_lon = (locA.longitude + locB.longitude) / 2
    m = Map(location=[center_lat, center_lon], zoom_start=12)
    fig = Figure(width="100%", height="600px")
    fig.add_child(m)

    # Draw route
    route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]
    PolyLine(route_coords, color='red', weight=5, opacity=0.8).add_to(m)

    # Start and end markers
    Marker([locA.latitude, locA.longitude], popup=f"Start: {pointA}", icon=Icon(color='green', icon='play')).add_to(m)
    Marker([locB.latitude, locB.longitude], popup=f"End: {pointB}", icon=Icon(color='red', icon='flag')).add_to(m)

    # -----------------------------
    # Save map to static folder
    # -----------------------------
    if not os.path.exists('static'):
        os.makedirs('static')
    map_filename = 'static/route_map.html'
    fig.save(map_filename)

    # Render page
    return render_template_string('''
        <h2>✅ Shortest Route Found!</h2>
        <p><b>From:</b> {{ pointA }} <br><b>To:</b> {{ pointB }}</p>
        <p>📏 Total Distance: {{ distance_km }} km</p>
        <iframe src="/{{ map_filename }}" width="90%" height="600"></iframe>
        <br><a href="/">⬅ Back</a>
    ''', pointA=pointA, pointB=pointB, distance_km=round(route_length_km, 2), map_filename=map_filename)

# -----------------------------
# 5️⃣ Run Flask
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
