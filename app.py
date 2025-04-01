import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import requests
from datetime import datetime
import time
import pickle
import os

# Título de la aplicación
st.title("Explorador de Propiedades - Estilo Idealista")

# Definir ruta para almacenamiento persistente
DATA_FILE = "idealista_properties.pkl"
TIMESTAMP_FILE = "idealista_last_query.pkl"

# Funciones para almacenamiento persistente
def save_data(df):
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(df, f)

    # Guardar timestamp
    with open(TIMESTAMP_FILE, 'wb') as f:
        pickle.dump(datetime.now(), f)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return None
    return None

def load_timestamp():
    if os.path.exists(TIMESTAMP_FILE):
        try:
            with open(TIMESTAMP_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return None
    return None

# Función para asegurar que las columnas numéricas son correctas
def ensure_numeric(df):
    for col in ['price', 'rooms', 'bathrooms', 'size']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # Reemplazar valores NaN con valores razonables
            if col == 'price':
                df[col] = df[col].fillna(0)
            elif col == 'rooms':
                df[col] = df[col].fillna(1)
            elif col == 'bathrooms':
                df[col] = df[col].fillna(1)
            elif col == 'size':
                df[col] = df[col].fillna(0)
    return df

# Función para llamar a la API
def fetch_properties_data():
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

    with st.spinner(f'Cargando página {current_page}...'):
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        if "elementList" in data:
            all_properties.extend(data["elementList"])

            # Obtener información de paginación
            total_pages = data.get("totalPages", 1)
            total_properties = data.get("total", 0)

            st.info(f"Encontradas {total_properties} propiedades en {total_pages} páginas")

            # Mostrar barra de progreso
            progress_bar = st.progress(1/total_pages)
            progress_text = st.empty()

            # Recorrer el resto de páginas (limitando a 5 para pruebas)
            for page in range(2, min(total_pages + 1, 6)):
                progress_text.text(f'Cargando página {page} de {total_pages}...')
                progress_bar.progress(page/total_pages)

                querystring["numPage"] = str(page)
                time.sleep(0.5)  # Pequeña pausa para no sobrecargar la API

                response = requests.get(url, headers=headers, params=querystring)
                page_data = response.json()

                if "elementList" in page_data:
                    all_properties.extend(page_data["elementList"])

            progress_bar.progress(1.0)
            progress_text.empty()

    # Convertir a DataFrame y asegurar tipos de datos
    df = pd.DataFrame(all_properties)
    df = ensure_numeric(df)

    # Guardar datos para persistencia
    save_data(df)

    return df

# Cargar datos almacenados si existen
df_properties = load_data()
last_query_time = load_timestamp()

# Barra lateral
st.sidebar.header("Filtros de Resultados")

# Si hay datos, mostrar filtros
if df_properties is not None:
    df_properties = ensure_numeric(df_properties)

    # Obtener rangos de los datos
    min_price = int(df_properties["price"].min())
    max_price = int(df_properties["price"].max())
    min_rooms = int(df_properties["rooms"].min())
    max_rooms = int(df_properties["rooms"].max())
    min_size_val = int(df_properties["size"].min())
    min_bath_val = int(df_properties["bathrooms"].min())

    # Filtros
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

    # Filtro por municipio
    municipalities = list(df_properties["municipality"].dropna().unique())
    selected_municipalities = st.sidebar.multiselect(
        "Selecciona municipios",
        options=municipalities,
        default=[]
    )

    # Filtro para alquilado (ahora opcional)
    exclude_rented = st.sidebar.checkbox("Excluir propiedades alquiladas", True)

    exclude_text = st.sidebar.text_input("Excluir si contiene en descripción", "")
    include_keyword = st.sidebar.text_input("Buscar en descripción", "")
else:
    st.sidebar.info("Haz clic en 'Actualizar Datos' para cargar propiedades.")
    # Valores predeterminados para evitar errores
    price_range = (0, 1)
    rooms_range = (0, 1)
    min_size = 0
    min_bathrooms = 0
    selected_municipalities = []
    exclude_rented = True
    exclude_text = ""
    include_keyword = ""

# Separador visual antes del botón
st.sidebar.markdown("---")

# Mostrar info de búsqueda fija
st.sidebar.header("Búsqueda de Propiedades")
st.sidebar.info("Búsqueda fija: Viviendas en venta en Madrid hasta 150.000€")

# Mostrar la hora de la última consulta
if last_query_time:
    time_diff = datetime.now() - last_query_time
    days = time_diff.days
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        time_str = f"{days} días, {hours} horas"
    elif hours > 0:
        time_str = f"{hours} horas, {minutes} minutos"
    elif minutes > 0:
        time_str = f"{minutes} minutos, {seconds} segundos"
    else:
        time_str = f"{seconds} segundos"

    st.sidebar.info(f"Última actualización: hace {time_str}")

# Botón para actualizar datos desde la API al final del sidebar
if st.sidebar.button("Actualizar Datos"):
    df_properties = fetch_properties_data()

# Si no hay datos, detener ejecución
if df_properties is None:
    st.info("Haz clic en 'Actualizar Datos' para cargar propiedades.")
    st.stop()

# Aplicar filtros de forma segura
try:
    # Iniciar con todos los datos
    filtered_df = df_properties.copy()

    # Aplicar filtros uno a uno
    filtered_df = filtered_df[
        (filtered_df["price"] >= price_range[0]) &
        (filtered_df["price"] <= price_range[1])
    ]

    filtered_df = filtered_df[
        (filtered_df["rooms"] >= rooms_range[0]) &
        (filtered_df["rooms"] <= rooms_range[1])
    ]

    filtered_df = filtered_df[filtered_df["size"] >= min_size]

    filtered_df = filtered_df[filtered_df["bathrooms"] >= min_bathrooms]

    # Filtrar por municipios
    if selected_municipalities:
        filtered_df = filtered_df[filtered_df["municipality"].isin(selected_municipalities)]

    # Filtrar por palabras clave en descripción
    if include_keyword:
        filtered_df = filtered_df[filtered_df["description"].str.contains(include_keyword, case=False, na=False)]

    # Filtrar por texto a excluir
    if exclude_text:
        exclude_terms = exclude_text.split('|')
        for term in exclude_terms:
            filtered_df = filtered_df[~filtered_df["description"].str.contains(term.strip(), case=False, na=False)]

    # Filtros predefinidos
    exclude_default = "subasta|pendiente de|puja|desahucio|local sin cambio de uso|cambio de uso|posisio|nuda propiedad|no se puede hipotecar|ocupado|ocupada|pujas|ocupacional|ilegal|okupada|okupado|sin posesi|procedimiento judicial"
    if exclude_rented:
        exclude_default += "|alquilado"

    filtered_df = filtered_df[~filtered_df["description"].str.contains(exclude_default, case=False, na=False)]

except Exception as e:
    st.error(f"Error al aplicar filtros: {e}")
    filtered_df = pd.DataFrame()

# Mostrar resultados
st.subheader(f"Resultados encontrados: {len(filtered_df)} propiedades")

# Crear mapa
if "latitude" in filtered_df.columns and "longitude" in filtered_df.columns and len(filtered_df) > 0:
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
        if filtered_df['size'].sum() > 0:
            avg_price_sqm = int(filtered_df['price'].sum() / filtered_df['size'].sum())
            st.metric("Precio medio por m²", f"{avg_price_sqm}€/m²")
        else:
            st.metric("Precio medio por m²", "N/A")

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

            location_text = row['municipality'] if pd.notna(row.get('municipality')) else "Desconocido"
            if pd.notna(row.get('district')):
                location_text += f", {row['district']}"
            st.markdown(f"📍 {location_text}")

            if row['size'] > 0:
                price_per_sqm = round(row['price'] / row['size'], 2)
                st.markdown(f"**Precio/m²:** {price_per_sqm} €/m²")
            else:
                st.markdown("**Precio/m²:** N/A")

            if pd.notna(row.get('description')) and isinstance(row['description'], str):
                desc_text = row['description'][:200] + "..."
            else:
                desc_text = "Sin descripción disponible"
            st.markdown(f"**Descripción:** {desc_text}")

            st.markdown(f"[Ver en Idealista]({row['url']})")

# Si no hay resultados
if len(filtered_df) == 0:
    st.warning("No se encontraron propiedades con los filtros seleccionados.")
