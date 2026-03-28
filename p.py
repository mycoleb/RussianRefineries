import requests
import folium
import json
import os
from folium.plugins import MarkerCluster

CACHE_FILE = "refinery_cache.json"

def get_wikidata_refineries():
    print("Connecting to Wikidata SPARQL API...")
    url = 'https://query.wikidata.org/sparql'
    
    # Query for items that are 'oil refinery' (Q43224) located in 'Russia' (Q159)
    query = """
    SELECT ?item ?itemLabel ?coords ?operatorLabel WHERE {
      ?item wdt:P31 wd:Q43224;      # Instance of oil refinery
            wdt:P17 wd:Q159;       # Country: Russia
            wdt:P625 ?coords.      # Must have coordinates
      OPTIONAL { ?item wdt:P137 ?operator. } # Optional operator/owner
      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    }
    """
    headers = {'User-Agent': 'RefineryMapper/1.0 (Mycole@example.com)', 'Accept': 'application/sparql-results+json'}
    
    try:
        response = requests.get(url, params={'query': query}, headers=headers, timeout=30)
        response.raise_for_status()
        results = response.json()['results']['bindings']
        
        # Standardize format for the map
        standardized = []
        for r in results:
            # Wikidata coords come in 'Point(lon lat)' format
            raw_coords = r['coords']['value'].replace('Point(', '').replace(')', '').split(' ')
            standardized.append({
                'name': r['itemLabel']['value'],
                'lat': float(raw_coords[1]),
                'lon': float(raw_coords[0]),
                'operator': r.get('operatorLabel', {}).get('value', 'Unknown')
            })
        return standardized
    except Exception as e:
        print(f"Wikidata Error: {e}")
        return []

def get_refinery_data():
    if os.path.exists(CACHE_FILE):
        print("Loading data from local cache...")
        with open(CACHE_FILE, 'r') as f: return json.load(f)

    # If cache fails, try Wikidata first (usually faster for Russia-wide queries)
    data = get_wikidata_refineries()
    
    if data:
        with open(CACHE_FILE, 'w') as f: json.dump(data, f)
    return data

def create_map(data):
    if not data:
        print("No data found to map.")
        return

    m = folium.Map(location=[61, 105], zoom_start=3, tiles="cartodbpositron")
    marker_cluster = MarkerCluster().add_to(m)

    for entry in data:
        folium.Marker(
            location=[entry['lat'], entry['lon']],
            popup=f"<b>{entry['name']}</b><br>Owner: {entry['operator']}",
            icon=folium.Icon(color="red", icon="industry", prefix="fa")
        ).add_to(marker_cluster)

    m.save("russian_refineries_map.html")
    print(f"Map saved! Plotted {len(data)} refineries.")

# Run
data = get_refinery_data()
create_map(data)
