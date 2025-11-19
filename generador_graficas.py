import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import json

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Visualización de Datos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("🌍 Sistema de Visualización de Datos")
st.markdown("---")

# Función para descargar gráficos
def get_image_download_link(fig, filename="grafico.png"):
    """Genera un link de descarga para gráficos de Plotly"""
    buffer = BytesIO()
    fig.write_image(buffer, format="png", width=1200, height=800)
    buffer.seek(0)
    image_data = buffer.getvalue()
    b64 = base64.b64encode(image_data).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">📥 Descargar {filename}</a>'
    return href

# Función para limpiar y convertir columnas numéricas
def clean_numeric_column(series):
    """Limpia y convierte una columna a numérica"""
    # Reemplazar comas por puntos para decimales
    series = series.astype(str).str.replace(',', '.')
    # Convertir a numérico, los errores se convierten en NaN
    return pd.to_numeric(series, errors='coerce')

# Sidebar - Carga de archivos
st.sidebar.header("📁 Carga de Archivos")

# Cargar archivo de datos
uploaded_file = st.sidebar.file_uploader(
    "Sube tu archivo de datos",
    type=["csv", "xlsx"],
    help="Formatos soportados: CSV, Excel"
)

# Cargar archivo GeoJSON
uploaded_geojson = st.sidebar.file_uploader(
    "Sube archivo GeoJSON (opcional)",
    type=["geojson", "json"],
    help="Para mapas con polígonos de colonias"
)

# Inicializar variables
df = None
gdf = None

# Procesar archivo de datos
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.sidebar.success(f"✅ Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")
        
        # Mostrar información básica del dataset
        with st.sidebar.expander("📊 Info del Dataset"):
            st.write(f"**Filas:** {df.shape[0]}")
            st.write(f"**Columnas:** {df.shape[1]}")
            st.write("**Tipos de datos:**")
            st.write(df.dtypes)
                
    except Exception as e:
        st.sidebar.error(f"Error al cargar archivo: {e}")

# Procesar GeoJSON
if uploaded_geojson is not None:
    try:
        gdf = gpd.read_file(uploaded_geojson)
        st.sidebar.success(f"✅ GeoJSON cargado: {len(gdf)} features")
        
        with st.sidebar.expander("🗺️ Info GeoJSON"):
            st.write(f"**Columnas GeoJSON:** {list(gdf.columns)}")
            
    except Exception as e:
        st.sidebar.error(f"Error al cargar GeoJSON: {e}")

# Si hay datos cargados, mostrar opciones de visualización
if df is not None:
    st.header("🎨 Selección de Tipo de Gráfico")
    
    # Selección de tipo de gráfico
    chart_type = st.selectbox(
        "¿Qué tipo de visualización quieres crear?",
        [
            "Mapa de Calor Geográfico",
            "Gráfico de Barras", 
            "Gráfico de Líneas",
            "Gráfico de Dispersión",
            "Histograma",
            "Mapa de Calor de Correlación",
            "Gráfico de Pastel"
        ]
    )
    
    st.markdown("---")
    
    # SECCIÓN DE PERSONALIZACIÓN COMÚN
    st.subheader("✏️ Personalización del Gráfico")
    
    col_custom1, col_custom2, col_custom3 = st.columns(3)
    
    with col_custom1:
        chart_title = st.text_input("Título del gráfico", "Mi Gráfico")
        title_size = st.slider("Tamaño del título", 10, 30, 18)
        
    with col_custom2:
        xaxis_title = st.text_input("Título del eje X", "Eje X")
        yaxis_title = st.text_input("Título del eje Y", "Eje Y")
        
    with col_custom3:
        label_size = st.slider("Tamaño de etiquetas", 8, 20, 12)
        font_family = st.selectbox("Fuente", ["Arial", "Helvetica", "Times New Roman", "Courier New"])
    
    # PREVISUALIZACIÓN EN TIEMPO REAL
    st.subheader("👁️ Previsualización en Tiempo Real")
    auto_update = st.checkbox("Actualización automática", value=True, 
                             help="Activar para ver cambios en tiempo real")

    # MAPA DE CALOR GEOGRÁFICO - VERSIÓN CORREGIDA
    if chart_type == "Mapa de Calor Geográfico":
        st.subheader("🌍 Configuración del Mapa de Calor")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Selección de columnas para coordenadas
            lat_col = st.selectbox("Selecciona columna de Latitud", df.columns, key="lat")
            lon_col = st.selectbox("Selecciona columna de Longitud", df.columns, key="lon")
            
            # Opción para columna de colonia (si existe)
            colonia_col = st.selectbox(
                "Selecciona columna de Colonia (opcional)", 
                ["Ninguna"] + list(df.columns),
                key="colonia"
            )
            
        with col2:
            # Filtro MANUAL para reportes de lluvias
            lluvia_col = st.selectbox(
                "Columna de reportes de lluvia (opcional)",
                ["Ninguna"] + list(df.columns),
                help='Columna con valores "si" para lluvias, "no" o "nan" para no lluvias'
            )
            
            # Valor para el mapa de calor - incluir todas las columnas numéricas
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            # Si no hay columnas numéricas, mostrar todas las columnas
            if not numeric_columns:
                value_col = st.selectbox(
                    "Columna para valores del mapa de calor",
                    df.columns.tolist()
                )
                st.warning("⚠️ La columna seleccionada no es numérica. Se intentará convertir.")
            else:
                value_col = st.selectbox(
                    "Columna para valores del mapa de calor",
                    numeric_columns
                )
            
            # Opciones de filtro MANUAL
            if lluvia_col != "Ninguna" and lluvia_col in df.columns:
                filtro_lluvia = st.radio(
                    "Filtrar por reportes de lluvia:",
                    ["Mostrar todos", "Solo reportes por lluvia", "Excluir reportes por lluvia"]
                )
            else:
                filtro_lluvia = "Mostrar todos"
        
        # CONFIGURACIÓN GEOJSON
        if uploaded_geojson is not None and gdf is not None:
            st.subheader("🗺️ Configuración de Capas GeoJSON")
            
            col_geo1, col_geo2 = st.columns(2)
            
            with col_geo1:
                # Seleccionar columna de colonias en GeoJSON
                geojson_colonia_col = st.selectbox(
                    "Columna de colonias en GeoJSON",
                    gdf.columns,
                    help="Selecciona la columna que contiene los nombres de las colonias"
                )
            
            with col_geo2:
                # Seleccionar columna de alcaldías en GeoJSON
                geojson_alcaldia_col = st.selectbox(
                    "Columna de alcaldías en GeoJSON (opcional)",
                    ["Ninguna"] + list(gdf.columns),
                    help="Selecciona la columna que contiene las alcaldías"
                )
                
                show_geojson = st.checkbox("Mostrar polígonos GeoJSON", value=True)
        
        # Personalización específica del mapa
        st.subheader("🎨 Personalización del Mapa")
        
        col_map1, col_map2 = st.columns(2)
        
        with col_map1:
            map_zoom = st.slider("Nivel de zoom", 1, 18, 12)
            heat_radius = st.slider("Radio de los puntos", 5, 30, 10)
            heat_opacity = st.slider("Opacidad", 0.1, 1.0, 0.7)
            
        with col_map2:
            heat_color = st.color_picker("Color de los puntos", "#FF0000")
            map_height = st.slider("Altura del mapa (pixels)", 400, 1000, 600)
        
        # PREPARACIÓN DE DATOS - CORRECCIÓN APPLICADA
        map_df = df.copy()
        
        # 1. Limpiar y convertir columnas de coordenadas a numéricas
        st.info("🔧 Convirtiendo coordenadas a formato numérico...")
        map_df[lat_col] = clean_numeric_column(map_df[lat_col])
        map_df[lon_col] = clean_numeric_column(map_df[lon_col])
        
        # 2. Limpiar y convertir columna de valores a numérica si es necesario
        if value_col not in numeric_columns:
            map_df[value_col] = clean_numeric_column(map_df[value_col])
            st.info(f"🔧 Convirtiendo columna '{value_col}' a formato numérico...")
        
        # 3. Aplicar filtro MANUAL de lluvias según selección
        if lluvia_col != "Ninguna" and lluvia_col in map_df.columns:
            # Limpiar y estandarizar la columna de lluvias
            map_df[lluvia_col] = map_df[lluvia_col].astype(str).str.lower().str.strip()
            
            # Reemplazar 'nan' y valores vacíos por 'no'
            map_df[lluvia_col] = map_df[lluvia_col].replace(['nan', 'null', 'none', ''], 'no')
            
            if filtro_lluvia == "Solo reportes por lluvia":
                original_count = len(map_df)
                map_df = map_df[map_df[lluvia_col] == "si"]
                st.success(f"✅ Filtrado: {len(map_df)} de {original_count} registros (solo lluvias)")
            elif filtro_lluvia == "Excluir reportes por lluvia":
                original_count = len(map_df)
                map_df = map_df[map_df[lluvia_col] != "si"]
                st.success(f"✅ Filtrado: {len(map_df)} de {original_count} registros (excluyendo lluvias)")
            else:
                st.info("📊 Mostrando todos los registros (sin filtrar por lluvias)")
        
        # 4. Eliminar filas con valores NaN en coordenadas o valores
        original_count = len(map_df)
        map_df = map_df.dropna(subset=[lat_col, lon_col, value_col])
        cleaned_count = len(map_df)
        
        if original_count != cleaned_count:
            st.warning(f"⚠️ Se eliminaron {original_count - cleaned_count} registros con valores faltantes en coordenadas o valores")
        
        # VERIFICACIÓN FINAL DE DATOS
        if not map_df.empty:
            # Verificar que tenemos datos válidos
            valid_coords = (~map_df[lat_col].isna()) & (~map_df[lon_col].isna()) & (~map_df[value_col].isna())
            valid_data_count = valid_coords.sum()
            
            if valid_data_count > 0:
                st.success(f"✅ Datos listos: {valid_data_count} registros válidos para el mapa")
                
                # Mostrar estadísticas de las coordenadas
                with st.expander("📐 Estadísticas de Coordenadas"):
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    with col_stat1:
                        st.metric("Latitud Mínima", f"{map_df[lat_col].min():.6f}")
                        st.metric("Latitud Máxima", f"{map_df[lat_col].max():.6f}")
                    with col_stat2:
                        st.metric("Longitud Mínima", f"{map_df[lon_col].min():.6f}")
                        st.metric("Longitud Máxima", f"{map_df[lon_col].max():.6f}")
                    with col_stat3:
                        st.metric("Valor Mínimo", f"{map_df[value_col].min():.2f}")
                        st.metric("Valor Máximo", f"{map_df[value_col].max():.2f}")
                
                # CREAR MAPA DE CALOR
                if st.button("🔄 Generar Mapa de Calor") or (auto_update and st.session_state.get('last_chart_type') == "Mapa de Calor Geográfico"):
                    try:
                        # Crear mapa base
                        center_lat = map_df[lat_col].mean()
                        center_lon = map_df[lon_col].mean()
                        
                        m = folium.Map(
                            location=[center_lat, center_lon],
                            zoom_start=map_zoom,
                            tiles='OpenStreetMap'
                        )
                        
                        # Añadir capa GeoJSON si está disponible
                        if uploaded_geojson is not None and gdf is not None and show_geojson:
                            # Función de estilo para los polígonos
                            def style_function(feature):
                                return {
                                    'fillColor': '#3388ff',
                                    'color': '#3388ff',
                                    'weight': 2,
                                    'fillOpacity': 0.1,
                                }
                            
                            # Añadir GeoJSON al mapa
                            folium.GeoJson(
                                gdf,
                                style_function=style_function,
                                tooltip=folium.GeoJsonTooltip(
                                    fields=[geojson_colonia_col] + ([geojson_alcaldia_col] if geojson_alcaldia_col != "Ninguna" else []),
                                    aliases=["Colonia"] + (["Alcaldía"] if geojson_alcaldia_col != "Ninguna" else []),
                                    localize=True
                                )
                            ).add_to(m)
                        
                        # Añadir puntos de calor
                        for idx, row in map_df.iterrows():
                            # Calcular tamaño basado en el valor (si es numérico)
                            try:
                                valor = float(row[value_col])
                                # Normalizar el tamaño entre 5 y el radio máximo
                                if map_df[value_col].max() > map_df[value_col].min():
                                    normalized_val = (valor - map_df[value_col].min()) / (map_df[value_col].max() - map_df[value_col].min())
                                    radius = 5 + (heat_radius - 5) * normalized_val
                                else:
                                    radius = heat_radius
                            except:
                                radius = heat_radius
                            
                            popup_text = f"""
                            <b>Valor:</b> {row[value_col]}<br>
                            <b>Lat:</b> {row[lat_col]:.6f}<br>
                            <b>Lon:</b> {row[lon_col]:.6f}<br>
                            """
                            if colonia_col != "Ninguna" and colonia_col in row and pd.notna(row[colonia_col]):
                                popup_text += f"<b>Colonia:</b> {row[colonia_col]}<br>"
                            if lluvia_col != "Ninguna" and lluvia_col in row and pd.notna(row[lluvia_col]):
                                popup_text += f"<b>Lluvia:</b> {row[lluvia_col]}<br>"
                            
                            folium.CircleMarker(
                                location=[row[lat_col], row[lon_col]],
                                radius=radius,
                                popup=folium.Popup(popup_text, max_width=300),
                                color=heat_color,
                                fill=True,
                                fillColor=heat_color,
                                fillOpacity=heat_opacity,
                                opacity=0.8,
                                tooltip=f"Valor: {row[value_col]:.2f}"
                            ).add_to(m)
                        
                        # Añadir título al mapa
                        title_html = f'''
                        <h3 align="center" style="font-size:20px"><b>{chart_title}</b></h3>
                        '''
                        m.get_root().html.add_child(folium.Element(title_html))
                        
                        # Mostrar mapa
                        folium_static(m, width=800, height=map_height)
                        
                        # Mostrar estadísticas del mapa
                        with st.expander("📈 Estadísticas del Mapa"):
                            col_stat1, col_stat2, col_stat3 = st.columns(3)
                            with col_stat1:
                                st.metric("Total de puntos", len(map_df))
                            with col_stat2:
                                st.metric("Valor promedio", f"{map_df[value_col].mean():.2f}")
                            with col_stat3:
                                st.metric("Valor máximo", f"{map_df[value_col].max():.2f}")
                        
                        # Botones de descarga
                        st.markdown("---")
                        st.subheader("💾 Descargar Visualización")
                        
                        col_dl1, col_dl2 = st.columns(2)
                        
                        with col_dl1:
                            # Exportar datos procesados
                            csv = map_df.to_csv(index=False)
                            st.download_button(
                                label="📥 Descargar datos procesados (CSV)",
                                data=csv,
                                file_name="datos_mapa_calor.csv",
                                mime="text/csv"
                            )
                        
                        with col_dl2:
                            # Exportar mapa como HTML
                            map_html = m._repr_html_()
                            st.download_button(
                                label="📥 Descargar Mapa (HTML)",
                                data=map_html,
                                file_name="mapa_calor.html",
                                mime="text/html"
                            )
                        
                        st.session_state.last_chart_type = "Mapa de Calor Geográfico"
                        
                    except Exception as e:
                        st.error(f"❌ Error al generar mapa: {str(e)}")
                        st.info("💡 **Solución de problemas:** Verifica que las coordenadas estén en formato decimal (ej: 19.32059308, -99.22806048)")
            else:
                st.error("❌ No hay registros válidos después de la limpieza de datos. Verifica tus columnas seleccionadas.")
        else:
            st.error("❌ No hay datos válidos después de aplicar los filtros. Verifica:")
            st.error("- Las columnas de latitud y longitud contienen números")
            st.error("- La columna de valor contiene datos numéricos")
            st.error("- Los filtros no han eliminado todos los registros")

# ... (el resto del código para otros tipos de gráficos se mantiene igual)

else:
    st.info("👆 Por favor carga un archivo de datos en el sidebar para comenzar")

# Información adicional
with st.sidebar.expander("ℹ️ Instrucciones de Uso"):
    st.markdown("""
    **📝 Instrucciones para Mapas:**
    
    **Formato de Coordenadas:**
    - Latitud: 19.32059308 (formato decimal)
    - Longitud: -99.22806048 (formato decimal con signo negativo para oeste)
    
    **Formato de Lluvias:**
    - "si" = Reporte por lluvias
    - "no" o "nan" = No es reporte por lluvias
    
    **Solución de Problemas:**
    - Si ves errores, verifica que las coordenadas sean números
    - Los valores NaN en coordenadas se eliminan automáticamente
    - Las columnas no numéricas se convierten automáticamente
    """)

st.markdown("---")
st.markdown("*Sistema de Visualización - Desarrollado con Streamlit*")
