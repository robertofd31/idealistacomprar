# Mostrar info de búsqueda fija
st.sidebar.header("Búsqueda de Propiedades")
st.sidebar.info("Búsqueda fija: Viviendas en venta en Madrid hasta 150.000€")

# Botón para actualizar datos desde la API
if st.sidebar.button("Buscar Propiedades"):
    df_properties = fetch_properties_data()
else:
    # Usar datos almacenados si existen
    df_properties = st.session_state.properties_data

# Mostrar la hora de la última consulta
if st.session_state.last_query_time:
    time_diff = datetime.now() - st.session_state.last_query_time
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        time_str = f"{hours} horas, {minutes} minutos"
    elif minutes > 0:
        time_str = f"{minutes} minutos, {seconds} segundos"
    else:
        time_str = f"{seconds} segundos"

    st.sidebar.info(f"Última actualización: hace {time_str}")

# Si no hay datos, detener ejecución
if df_properties is None:
    st.info("Haz clic en 'Buscar Propiedades' para cargar datos.")
    st.stop()
