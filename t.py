import requests, folium, json, os
from folium.plugins import MarkerCluster

CACHE_FILE = "refinery_cache.json"

def get_wikidata():
    print("Strategy 1: Fetching from Wikidata...")
    url = 'https://query.wikidata.org/sparql'
    # Broad query: Items that are a subclass of 'refinery' in Russia
    query = """
    SELECT ?item ?itemLabel ?coords ?operatorLabel WHERE {
      ?item wdt:P31/wdt:P279* wd:Q43224; wdt:P17 wd:Q159; wdt:P625 ?coords.
      OPTIONAL { ?item wdt:P137 ?operator. }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    } LIMIT 100
    """
    try:
        r = requests.get(url, params={'query': query}, headers={'User-Agent': 'RefineryBot/1.0'}, timeout=15)
        results = r.json()['results']['bindings']
        return [{'name': res['itemLabel']['value'], 'lat': float(res['coords']['value'].split(' ')[1][:-1]), 
                 'lon': float(res['coords']['value'].split(' ')[0][6:]), 'source': 'Wikidata'} for res in results]
    except: return []

def get_overpass():
    print("Strategy 2: Wikidata failed. Trying Overpass API (OSM)...")
    url = "https://overpass-api.de/api/interpreter"
    query = '[out:json][timeout:30];area["ISO3166-1"="RU"]->.a;(node["industrial"="refinery"](area.a);way["industrial"="refinery"](area.a););out center;'
    try:
        r = requests.post(url, data={'data': query}, timeout=35)
        elements = r.json().get('elements', [])
        return [{'name': e.get('tags', {}).get('name', 'Unnamed'), 'lat': e.get('lat') or e['center']['lat'], 
                 'lon': e.get('lon') or e['center']['lon'], 'source': 'OSM'} for e in elements]
    except: return []

def load_data():
    if os.path.exists(CACHE_FILE):
        print("Using local cache.")
        with open(CACHE_FILE, 'r') as f: return json.load(f)
    
    data = get_wikidata()
    if not data: data = get_overpass()
    
    if data:
        with open(CACHE_FILE, 'w') as f: json.dump(data, f)
    return data

def main():
    data = load_data()
    if not data:
        print("All sources failed. Check your internet or API status.")
        return

    m = folium.Map(location=[61, 105], zoom_start=3)
    cluster = MarkerCluster().add_to(m)
    for p in data:
        folium.Marker([p['lat'], p['lon']], popup=f"{p['name']} ({p['source']})").add_to(cluster)
    
    m.save("refineries_fallback.html")
    print(f"Success! Plotted {len(data)} locations from {data[0]['source'] if data else 'N/A'}.")

main()