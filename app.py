import pandas as pd
import requests
from datetime import datetime
import time
import os
import json

# Verificar si el archivo de caché existe
def check_cache_file():
    return os.path.exists('properties_cache.json')

# Obtener la edad del caché en segundos
def get_cache_age():
    if not check_cache_file():
        return float('inf')  # Si no existe, devolver infinito
    
    file_time = os.path.getmtime('properties_cache.json')
    current_time = time.time()
    return current_time - file_time

# Guardar datos en caché
def save_to_cache(data, query_time):
    cache_data = {
        'data': data,
        'query_time': query_time.isoformat()
    }
    with open('properties_cache.json', 'w') as f:
        json.dump(cache_data, f)
    print(f"Datos guardados en caché: {len(data)} propiedades")

# Cargar datos desde caché
def load_from_cache():
    if not check_cache_file():
        return None, None
    
    with open('properties_cache.json', 'r') as f:
        cache_data = json.load(f)
    
    query_time = datetime.fromisoformat(cache_data['query_time'])
    return cache_data['data'], query_time

# Función para llamar a la API y obtener todas las páginas
def fetch_properties_data(force_reload=False):
    # Verificar si hay caché válido (menos de 1 hora)
    cache_age = get_cache_age()
    
    if not force_reload and cache_age < 3600:  # 1 hora en segundos
        print(f"Usando caché existente (edad: {int(cache_age/60)} minutos)")
        return load_from_cache()
    
    print("Obteniendo datos nuevos desde la API...")
    
    url = "https://idealista7.p.rapidapi.com/listhomes"
    headers = {
        "x-rapidapi-key": "aa2dd641d5msh2565cfba16fdf3cp172729jsn62ebc6b556b5",
        "x-rapidapi-host": "idealista7.p.rapidapi.com"
    }

    # Parámetros fijos de la consulta
    querystring = {
        "order": "lowestprice",
        "operation": "sale",
        "locationId": "0-EU-ES-28",
        "locationName": "Madrid",
        "maxItems": "40",
        "location": "es",
        "locale": "es",
        "maxPrice": "150000"
    }

    all_properties = []

    # Iniciar con la página 1
    current_page = 1
    querystring["numPage"] = str(current_page)

    print(f'Cargando página {current_page}...')
    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    if "elementList" in data:
        all_properties.extend(data["elementList"])

        # Obtener información de paginación
        total_pages = data.get("totalPages", 1)
        total_properties = data.get("total", 0)

        print(f"Encontradas {total_properties} propiedades en {total_pages} páginas")

        # Recorrer el resto de páginas
        for page in range(2, total_pages + 1):
            print(f'Cargando página {page} de {total_pages}...')
            
            querystring["numPage"] = str(page)
            time.sleep(0.5)  # Pequeña pausa para no sobrecargar la API

            response = requests.get(url, headers=headers, params=querystring)
            page_data = response.json()

            if "elementList" in page_data:
                all_properties.extend(page_data["elementList"])

    # Guardar timestamp de la consulta
    query_time = datetime.now()
    
    # Guardar en caché
    save_to_cache(all_properties, query_time)
    
    return all_properties, query_time

# Función para filtrar propiedades
def filter_properties(properties, filters):
    df = pd.DataFrame(properties)
    
    # Aplicar filtros básicos
    filtered_df = df[
        (df["price"] >= filters["price_min"]) &
        (df["price"] <= filters["price_max"]) &
        (df["rooms"] >= filters["rooms_min"]) &
        (df["rooms"] <= filters["rooms_max"]) &
        (df["size"] >= filters["min_size"]) &
        (df["bathrooms"] >= filters["min_bathrooms"])
    ]
    
    # Filtrar por municipios
    if filters["municipalities"]:
        filtered_df = filtered_df[filtered_df["municipality"].isin(filters["municipalities"])]
    
    # Filtrar por palabras clave en descripción
    if filters["include_keyword"]:
        filtered_df = filtered_df[filtered_df["description"].str.contains(filters["include_keyword"], case=False, na=False)]
    
    # Filtrar por texto a excluir
    if filters["exclude_text"]:
        exclude_terms = filters["exclude_text"].split('|')
        for term in exclude_terms:
            filtered_df = filtered_df[~filtered_df["description"].str.contains(term.strip(), case=False, na=False)]
    
    # Filtros predefinidos
    exclude_default = "subasta|pendiente de|puja|desahucio|local sin cambio de uso|cambio de uso|posisio|nuda propiedad|no se puede hipotecar|ocupado|ocupada|pujas|ocupacional|ilegal|okupada|okupado|sin posesi|procedimiento judicial"
    if filters["exclude_rented"]:
        exclude_default += "|alquilado"
    
    filtered_df = filtered_df[~filtered_df["description"].str.contains(exclude_default, case=False, na=False)]
    
    return filtered_df

# Demostración de uso
# Obtener datos (usará caché si existe y es reciente)
properties, query_time = fetch_properties_data(force_reload=False)

if properties:
    # Convertir a DataFrame para análisis
    df = pd.DataFrame(properties)
    
    # Mostrar información sobre los datos
    print(f"\nDatos cargados: {len(properties)} propiedades")
    if query_time:
        time_diff = datetime.now() - query_time
        minutes, seconds = divmod(time_diff.seconds, 60)
        print(f"Última actualización: hace {minutes} minutos, {seconds} segundos")
    
    # Ejemplo de filtros
    filters = {
        "price_min": 50000,
        "price_max": 120000,
        "rooms_min": 2,
        "rooms_max": 4,
        "min_size": 50,
        "min_bathrooms": 1,
        "municipalities": [],  # Vacío para incluir todos
        "exclude_rented": True,
        "exclude_text": "",
        "include_keyword": ""
    }
    
    # Aplicar filtros
    filtered_df = filter_properties(properties, filters)
    
    # Mostrar resultados
    print(f"\nResultados filtrados: {len(filtered_df)} propiedades")
    
    # Mostrar algunas estadísticas
    if len(filtered_df) > 0:
        print(f"Precio medio: {int(filtered_df['price'].mean())}€")
        print(f"Tamaño medio: {int(filtered_df['size'].mean())}m²")
        avg_price_sqm = int(filtered_df['price'].sum() / filtered_df['size'].sum())
        print(f"Precio medio por m²: {avg_price_sqm}€/m²")
        
        # Mostrar las 5 propiedades más baratas
        print("\n5 propiedades más baratas:")
        cheapest = filtered_df.sort_values('price').head(5)
        for _, row in cheapest.iterrows():
            print(f"{row['price']}€ - {row['rooms']} hab, {row['size']}m² - {row['municipality']}")
            if 'url' in row:
                print(f"  URL: {row['url']}")
else:
    print("No se pudieron cargar los datos.")
