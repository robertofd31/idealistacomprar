
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import requests
from datetime import datetime
import time
import os
import json

# Función para verificar si el archivo de caché existe
def check_cache_file():
    return os.path.exists('properties_cache.json')

# Función para obtener la edad del caché en segundos
def get_cache_age():
    if not check_cache_file():
        return float('inf')
    file_time = os.path.getmtime('properties_cache.json')
    current_time = time.time()
    return current_time - file_time

# Función para guardar datos en caché
def save_to_cache(data, query_time):
    cache_data = {
        'data': data,
        'query_time': query_time.isoformat()
    }
    with open('properties_cache.json', 'w') as f:
        json.dump(cache_data, f)

# Función para cargar datos desde caché
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
        return load_from_cache()

    url = "https://idealista7.p.rapidapi.com/listhomes"
    headers = {
        "x-rapidapi-key": "aa2dd641d5msh2565cfba16fdf3cp172729jsn62ebc6b556b5",
        "x-rapidapi-host": "idealista7.p.rapidapi.com"
    }

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
    current_page = 1

    with st.spinner(f'Cargando página {current_page}...'):
        querystring["numPage"] = str(current_page)
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        if "elementList" in data:
            all_properties.extend(data["elementList"])
            total_pages = data.get("totalPages", 1)
            total_properties = data.get("total", 0)

            st.info(f"Encontradas {total_properties} propiedades en {total_pages} páginas")
            progress_bar = st.progress(1/total_pages)
            progress_text = st.empty()

            for page in range(2, total_pages + 1):
                progress_text.text(f'Cargando página {page} de {total_pages}...')
                progress_bar.progress(page/total_pages)

                querystring["numPage"] = str(page)
                time.sleep(0.5)

                response = requests.get(url, headers=headers, params=querystring)
                page_data = response.json()

                if "elementList" in page_data:
                    all_properties.extend(page_data["elementList"])

            progress_bar.progress(1.0)
            progress_text.empty()

    query_time = datetime.now()
    save_to_cache(all_properties, query_time)
    return all_properties, query_time

# Título de la aplicación
st.title("Explorador de Propiedades - Estilo Idealista")

# Barra lateral
st.sidebar.header("Filtros de Resultados")

# Botón para forzar actualización de datos
force_reload = st.sidebar.button("Forzar Actualización de Datos")

# Cargar datos
try:
    properties, query_time = fetch_properties_data(force_reload=force_reload)
    df_properties = pd.DataFrame(properties)

    # Mostrar info de la última consulta
    if query_time:
        time_diff = datetime.now() - query_time
        hours, remainder = divmod(time_diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            time_str = f"{hours} horas, {minutes} minutos"
        elif minutes > 0:
            time_str = f"{minutes} minutos, {seconds} segundos"
        else:
            time_str = f"{seconds} segundos"

        st.sidebar.info(f"Última actualización: hace {time_str}")
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# Mostrar info de búsqueda fija
st.sidebar.header("Búsqueda de Propiedades")
st.sidebar.info("Búsqueda fija: Viviendas en venta en Madrid hasta 150.000€")

# Configurar filtros
min_price = int(df_properties["price"].min())
max_price = int(df_properties["price"].max())
min_rooms = int(df_properties["rooms"].min())
max_rooms = int(df_properties["rooms"].max())
min_size_val = int(df_properties["size"].min())
min_bath_val = int(df_properties["bathrooms"].min())

price_range = st.sidebar.slider(
    "Rango de precio (€)",
    min_value=min_price,
    max_value=max_price,
    value=(min_price, max_price)
)

rooms_range = st.sidebar.slider(
    "Número de habitaciones",
    min_value=min_rooms,
    max_value=max_rooms,
    value=(min_rooms, max_rooms)
)

min_size = st.sidebar.number_input(
    "Tamaño mínimo (m²)",
    min_value=min_size_val,
    value=min_size_val
)

min_bathrooms = st.sidebar.number_input(
    "Baños mínimos",
    min_value=min_bath_val,
    value=min_bath_val
)

municipalities = list(df_properties["municipality"].unique())
selected_municipalities = st.sidebar.multiselect(
    "Selecciona municipios",
    options=municipalities,
    default=[]
)

exclude_rented = st.sidebar.checkbox("Excluir propiedades alquiladas", True)
exclude_text = st.sidebar.text_input("Excluir si contiene en descripción", "")
include_keyword = st.sidebar.text_input("Buscar en descripción", "")

# Aplicar filtros
filtered_df = df_properties[
    (df_properties["price"] >= price_range[0]) &
    (df_properties["price"] <= price_range[1]) &
    (df_properties["rooms"] >= rooms_range[0]) &
    (df_properties["rooms"] <= rooms_range[1]) &
    (df_properties["size"] >= min_size) &
    (df_properties["bathrooms"] >= min_bathrooms)
]

if selected_municipalities:
    filtered_df = filtered_df[filtered_df["municipality"].isin(selected_municipalities)]

if include_keyword:
    filtered_df = filtered_df[filtered_df["description"].str.contains(include_keyword, case=False, na=False)]

if exclude_text:
    exclude_terms = exclude_text.split('|')
    for term in exclude_terms:
        filtered_df = filtered_df[~filtered_df["description"].str.contains(term.strip(), case=False, na=False)]

exclude_default = "subasta|pendiente de|puja|desahucio|local sin cambio de uso|cambio de uso|posisio|nuda propiedad|no se puede hipotecar|ocupado|ocupada|pujas|ocupacional|ilegal|okupada|okupado|sin posesi|procedimiento judicial"
if exclude_rented:
    exclude_default += "|alquilado"

filtered_df = filtered_df[~filtered_df["description"].str.contains(exclude_default, case=False, na=False)]

# Mostrar resultados
st.subheader(f"Resultados encontrados: {len(filtered_df)} propiedades")

# Crear mapa
if "latitude" in filtered_df.columns and "longitude" in filtered_df.columns:
    st.subheader("Mapa de propiedades")
    m = folium.Map(location=[40.4168, -3.7038], zoom_start=10)

    for _, row in filtered_df.iterrows():
        if pd.notna(row["latitude"]) and pd.notna(row["longitude"]):
            popup_text = f"""
            <b>Precio:</b> {row['price']}€<br>
            <b>Habitaciones:</b> {row['rooms']}<br>
            <b>Tamaño:</b> {row['size']}m²<br>
            <a href="{row['url']}" target="_blank">Ver en Idealista</a>
            """
            folium.Marker(
                [row["latitude"], row["longitude"]],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=f"{row['price']}€ - {row['rooms']} hab.",
                icon=folium.Icon(color="red", icon="home")
            ).add_to(m)

    folium_static(m)

# Mostrar estadísticas
if len(filtered_df) > 0:
    st.subheader("Estadísticas de las propiedades filtradas")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Precio medio", f"{int(filtered_df['price'].mean())}€")
    with col2:
        st.metric("Tamaño medio", f"{int(filtered_df['size'].mean())}m²")
    with col3:
        avg_price_sqm = int(filtered_df['price'].sum() / filtered_df['size'].sum())
        st.metric("Precio medio por m²", f"{avg_price_sqm}€/m²")

    # Mostrar propiedades como tarjetas
    for _, row in filtered_df.iterrows():
        st.markdown("---")
        col1, col2 = st.columns([1, 2])

        with col1:
            if pd.notna(row.get("thumbnail")):
                st.image(row["thumbnail"], use_container_width=True)
            else:
                st.image("https://placehold.co/300x200?text=Sin+Imagen", use_container_width=True)

        with col2:
            st.markdown(f"### {row['price']} €")
            st.markdown(f"**{row['rooms']} habitaciones**, **{row['bathrooms']} baños**, **{row['size']} m²**")

            location_text = row['municipality']
            if pd.notna(row.get('district')):
                location_text += f", {row['district']}"
            st.markdown(f"📍 {location_text}")

            price_per_sqm = round(row['price'] / row['size'], 2) if row['size'] > 0 else "N/A"
            st.markdown(f"**Precio/m²:** {price_per_sqm} €/m²")

            if pd.notna(row.get('description')) and isinstance(row['description'], str):
                desc_text = row['description'][:200] + "..."
            else:
                desc_text = "Sin descripción disponible"
            st.markdown(f"**Descripción:** {desc_text}")

            st.markdown(f"[Ver en Idealista]({row['url']})")

else:
    st.warning("No se encontraron propiedades con los filtros seleccionados.")
