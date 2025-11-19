import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import geopandas as gpd
from io import BytesIO
import json
from datetime import datetime
import numpy as np

# Configuración de la página
st.set_page_config(
    page_title="Análisis de Incidentes - Magdalena Contreras",
    page_icon="📊",
    layout="wide"
)

# Título principal
st.title("📊 Dashboard de Análisis de Incidentes - Magdalena Contreras")
st.markdown("---")

# Función para cargar y limpiar datos
@st.cache_data
def load_data(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo: {str(e)}")
        return None

# Función para cargar GeoJSON
@st.cache_data
def load_geojson(uploaded_geojson):
    try:
        gdf = gpd.read_file(uploaded_geojson)
        return gdf
    except Exception as e:
        st.error(f"Error al cargar el archivo GeoJSON: {str(e)}")
        return None

# Función para crear mapa
def create_heatmap(df_filtered, lat_col, lon_col, geojson_data=None, colonia_column=None, show_heatmap=True, show_boundaries=True):
    """Crea un mapa de calor con los datos filtrados"""
    # Filtrar coordenadas válidas
    coordenadas_validas = df_filtered[[lat_col, lon_col]].dropna()
    
    if coordenadas_validas.empty:
        return None
    
    # Calcular centro del mapa de manera segura
    try:
        avg_lat = coordenadas_validas[lat_col].mean()
        avg_lon = coordenadas_validas[lon_col].mean()
    except Exception as e:
        # Usar coordenadas por defecto de Magdalena Contreras
        avg_lat = 19.32
        avg_lon = -99.24
    
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)
    
    # Preparar datos para heatmap
    heat_data = []
    for idx, row in df_filtered.dropna(subset=[lat_col, lon_col]).iterrows():
        heat_data.append([row[lat_col], row[lon_col], 1])
    
    # Añadir heatmap si está activado
    if show_heatmap and heat_data:
        heatmap_layer = HeatMap(heat_data, radius=15, blur=10, gradient={
            0.4: 'blue',
            0.6: 'cyan',
            0.7: 'lime',
            0.8: 'yellow',
            1.0: 'red'
        }, name="Mapa de Calor")
        heatmap_layer.add_to(m)
    
    # Añadir capa GeoJSON si está disponible y activada
    if show_boundaries and geojson_data is not None:
        try:
            # Asegurarse de que el GeoJSON esté en WGS84
            if geojson_data.crs != 'EPSG:4326':
                geojson_data = geojson_data.to_crs('EPSG:4326')
            
            # Configurar tooltip
            tooltip_fields = [colonia_column] if colonia_column else []
            tooltip_aliases = ["Colonia:"] if colonia_column else []
            
            geojson_layer = folium.GeoJson(
                geojson_data,
                name="Límites de Colonias",
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': 'blue',
                    'weight': 2,
                    'fillOpacity': 0.1
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=tooltip_fields,
                    aliases=tooltip_aliases,
                    localize=True
                ) if tooltip_fields else None
            )
            geojson_layer.add_to(m)
        except Exception as e:
            st.warning(f"No se pudo cargar el GeoJSON: {str(e)}")
    
    # Añadir control de capas
    folium.LayerControl().add_to(m)
    
    return m

# Sidebar para carga de archivos
st.sidebar.header("📁 Cargar Archivos")

uploaded_file = st.sidebar.file_uploader(
    "Subir archivo Excel de incidentes", 
    type=['xlsx'],
    help="Suba el archivo Excel con los datos de incidentes"
)

uploaded_geojson = st.sidebar.file_uploader(
    "Subir archivo GeoJSON de colonias (opcional)", 
    type=['geojson', 'json'],
    help="Suba un archivo GeoJSON con los polígonos de las colonias para mejorar el mapa"
)

# Cargar datos
if uploaded_file is not None:
    df = load_data(uploaded_file)
    
    if df is not None:
        # Mostrar información básica del dataset
        st.sidebar.markdown("---")
        st.sidebar.subheader("📈 Configuración de Columnas")
        
        # Selección manual de columnas
        available_columns = df.columns.tolist()
        
        colonia_col = st.sidebar.selectbox(
            "Selecciona la columna de COLONIAS:",
            available_columns,
            index=available_columns.index('colonia') if 'colonia' in available_columns else 0
        )
        
        tipo_incidente_col = st.sidebar.selectbox(
            "Selecciona la columna de TIPO DE INCIDENTE:",
            available_columns,
            index=available_columns.index('tipo_de_reporte_(incidente)') if 'tipo_de_reporte_(incidente)' in available_columns else 0
        )
        
        # Buscar columnas relacionadas con lluvia
        lluvia_col_options = [None] + available_columns
        lluvia_default_index = 0
        for i, col in enumerate(available_columns):
            if 'lluvia' in col.lower() or 'lluvias' in col.lower():
                lluvia_default_index = i + 1
                break
        
        lluvia_col = st.sidebar.selectbox(
            "Selecciona la columna de REPORTE POR LLUVIAS (opcional):",
            lluvia_col_options,
            index=lluvia_default_index
        )
        
        # Buscar columnas de coordenadas
        lat_col_options = [col for col in available_columns if 'lat' in col.lower()]
        lon_col_options = [col for col in available_columns if 'lon' in col.lower() or 'long' in col.lower()]
        
        lat_col = st.sidebar.selectbox(
            "Selecciona la columna de LATITUD:",
            available_columns,
            index=available_columns.index(lat_col_options[0]) if lat_col_options else 0
        )
        
        lon_col = st.sidebar.selectbox(
            "Selecciona la columna de LONGITUD:",
            available_columns,
            index=available_columns.index(lon_col_options[0]) if lon_col_options else 0
        )
        
        # Procesar datos según las columnas seleccionadas
        df_processed = df.copy()
        
        # Limpieza básica de datos
        df_processed['colonia_processed'] = df_processed[colonia_col].astype(str).str.strip().str.title()
        df_processed = df_processed.dropna(subset=['colonia_processed'])
        
        # Convertir fecha si existe
        fecha_cols = [col for col in available_columns if 'fecha' in col.lower()]
        if fecha_cols:
            fecha_col = fecha_cols[0]
            df_processed['fecha_processed'] = pd.to_datetime(df_processed[fecha_col], errors='coerce')
        
        # Convertir coordenadas a numérico
        df_processed['lat_processed'] = pd.to_numeric(df_processed[lat_col], errors='coerce')
        df_processed['lon_processed'] = pd.to_numeric(df_processed[lon_col], errors='coerce')
        
        # Procesar columna de lluvia si existe
        if lluvia_col:
            # Convertir a string y limpiar
            df_processed['lluvia_processed'] = df_processed[lluvia_col].astype(str).str.strip().str.lower()
            # Considerar 'si' como True, todo lo demás (incluido NaN) como False
            df_processed['es_lluvia'] = df_processed['lluvia_processed'] == 'si'
        else:
            df_processed['es_lluvia'] = False
        
        # Filtrar coordenadas inválidas o fuera de rango razonable para México
        df_processed = df_processed[
            (df_processed['lat_processed'].between(19.0, 20.0)) & 
            (df_processed['lon_processed'].between(-99.3, -99.1))
        ]
        
        # Mostrar información básica del dataset
        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 Resumen de Datos")
        st.sidebar.write(f"Total de registros: {len(df):,}")
        st.sidebar.write(f"Total de colonias: {df_processed['colonia_processed'].nunique()}")
        st.sidebar.write(f"Registros con coordenadas válidas: {df_processed[['lat_processed', 'lon_processed']].notna().all(axis=1).sum()}")
        if lluvia_col:
            st.sidebar.write(f"Incidentes por lluvia: {df_processed['es_lluvia'].sum()}")
        
        # Filtros en sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filtros")
        
        # Filtro por tipo de incidente
        tipos_incidente = ['Todos'] + sorted(df_processed[tipo_incidente_col].dropna().unique().tolist())
        selected_tipo = st.sidebar.selectbox(
            "Tipo de incidente:",
            tipos_incidente
        )
        
        # Filtro por lluvia
        filtro_lluvia = st.sidebar.selectbox(
            "Filtrar por lluvia:",
            ['Todos', 'Solo incidentes por lluvia', 'Excluir incidentes por lluvia']
        )
        
        # Aplicar filtros
        df_filtered = df_processed.copy()
        
        if selected_tipo != 'Todos':
            df_filtered = df_filtered[df_filtered[tipo_incidente_col] == selected_tipo]
        
        if filtro_lluvia == 'Solo incidentes por lluvia':
            df_filtered = df_filtered[df_filtered['es_lluvia'] == True]
        elif filtro_lluvia == 'Excluir incidentes por lluvia':
            df_filtered = df_filtered[df_filtered['es_lluvia'] == False]
        
        # Configuración del mapa
        st.sidebar.markdown("---")
        st.sidebar.subheader("🗺️ Configuración del Mapa")
        
        show_heatmap = st.sidebar.checkbox("Mostrar mapa de calor", value=True)
        show_boundaries = st.sidebar.checkbox("Mostrar límites de colonias", value=True)
        
        # Cargar GeoJSON si está disponible
        geojson_data = None
        colonia_column = None
        
        if uploaded_geojson is not None:
            geojson_data = load_geojson(uploaded_geojson)
            if geojson_data is not None:
                # Seleccionar columna para nombres de colonias
                available_geojson_columns = [col for col in geojson_data.columns if col != 'geometry']
                if available_geojson_columns:
                    colonia_column = st.sidebar.selectbox(
                        "Selecciona la columna del GeoJSON con nombres de colonias:",
                        available_geojson_columns
                    )
        
        # Layout principal
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🗺️ Mapa de Calor de Incidentes")
            
            # Crear mapa
            m = create_heatmap(df_filtered, 'lat_processed', 'lon_processed', geojson_data, colonia_column, show_heatmap, show_boundaries)
            
            if m is not None:
                # Mostrar mapa
                folium_static(m, width=700, height=500)
                
                # Botón para descargar mapa
                try:
                    map_html = m._repr_html_()
                    st.download_button(
                        label="📥 Descargar Mapa (HTML)",
                        data=map_html,
                        file_name="mapa_calor_incidentes.html",
                        mime="text/html"
                    )
                except Exception as e:
                    st.warning("No se pudo generar el archivo HTML del mapa")
            else:
                st.warning("No hay datos de coordenadas válidas para generar el mapa de calor.")
        
        with col2:
            st.subheader("🏆 Top 10 Colonias Más Afectadas")
            
            # Contar incidentes por colonia
            colonia_counts = df_filtered['colonia_processed'].value_counts().head(10)
            
            if not colonia_counts.empty:
                # Crear gráfico de barras
                fig_bar = px.bar(
                    x=colonia_counts.values,
                    y=colonia_counts.index,
                    orientation='h',
                    title="Top 10 Colonias con Más Incidentes",
                    labels={'x': 'Número de Incidentes', 'y': 'Colonia'},
                    color=colonia_counts.values,
                    color_continuous_scale='reds'
                )
                
                fig_bar.update_layout(
                    height=250,
                    showlegend=False,
                    yaxis={'categoryorder': 'total ascending'},
                    margin=dict(l=0, r=0, t=50, b=0)
                )
                
                st.plotly_chart(fig_bar, use_container_width=True)
                
                # Botones para descargar gráfico de barras
                col_download1, col_download2 = st.columns(2)
                
                with col_download1:
                    try:
                        # Descargar como PNG
                        img_bytes = fig_bar.to_image(format="png")
                        st.download_button(
                            label="📥 Descargar (PNG)",
                            data=img_bytes,
                            file_name="top10_colonias_incidentes.png",
                            mime="image/png"
                        )
                    except Exception as e:
                        st.error("Error al generar PNG")
                
                with col_download2:
                    # Descargar como HTML
                    html_bytes = fig_bar.to_html().encode()
                    st.download_button(
                        label="📥 Descargar (HTML)",
                        data=html_bytes,
                        file_name="top10_colonias_incidentes.html",
                        mime="text/html"
                    )
            else:
                st.warning("No hay datos suficientes para generar el gráfico de colonias.")
            
            # GRÁFICA: Colonias más afectadas por lluvia
            if lluvia_col:
                st.subheader("🌧️ Top 10 Colonias por Incidentes de Lluvia")
                
                # Filtrar solo incidentes de lluvia
                df_lluvia = df_filtered[df_filtered['es_lluvia'] == True]
                colonia_lluvia_counts = df_lluvia['colonia_processed'].value_counts().head(10)
                
                if not colonia_lluvia_counts.empty:
                    # Crear gráfico de barras para lluvia
                    fig_bar_lluvia = px.bar(
                        x=colonia_lluvia_counts.values,
                        y=colonia_lluvia_counts.index,
                        orientation='h',
                        title="Top 10 Colonias con Más Incidentes de Lluvia",
                        labels={'x': 'Número de Incidentes', 'y': 'Colonia'},
                        color=colonia_lluvia_counts.values,
                        color_continuous_scale='blues'
                    )
                    
                    fig_bar_lluvia.update_layout(
                        height=250,
                        showlegend=False,
                        yaxis={'categoryorder': 'total ascending'},
                        margin=dict(l=0, r=0, t=50, b=0)
                    )
                    
                    st.plotly_chart(fig_bar_lluvia, use_container_width=True)
                    
                    # Botones para descargar gráfico de lluvia
                    col_download3, col_download4 = st.columns(2)
                    
                    with col_download3:
                        try:
                            # Descargar como PNG
                            img_bytes_lluvia = fig_bar_lluvia.to_image(format="png")
                            st.download_button(
                                label="📥 Descargar (PNG)",
                                data=img_bytes_lluvia,
                                file_name="top10_colonias_lluvia.png",
                                mime="image/png"
                            )
                        except Exception as e:
                            st.error("Error al generar PNG para gráfica de lluvia")
                    
                    with col_download4:
                        # Descargar como HTML
                        html_bytes_lluvia = fig_bar_lluvia.to_html().encode()
                        st.download_button(
                            label="📥 Descargar (HTML)",
                            data=html_bytes_lluvia,
                            file_name="top10_colonias_lluvia.html",
                            mime="text/html"
                        )
                    
                    # Mostrar estadísticas de lluvia
                    st.info(f"**Total de incidentes por lluvia:** {len(df_lluvia)}")
                else:
                    st.warning("No se encontraron incidentes de lluvia en los datos filtrados.")
        
        # Sección adicional de análisis
        st.markdown("---")
        st.subheader("📈 Análisis Detallado")
        
        col3, col4 = st.columns(2)
        
        with col3:
            # Distribución por tipo de incidente
            st.write("**Distribución de Tipos de Incidente**")
            tipo_counts = df_filtered[tipo_incidente_col].value_counts().head(10)
            if not tipo_counts.empty:
                fig_pie = px.pie(
                    values=tipo_counts.values,
                    names=tipo_counts.index,
                    title="Top 10 Tipos de Incidente Más Comunes"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
                
                # Botón para descargar gráfico de torta
                col_pie1, col_pie2 = st.columns(2)
                with col_pie1:
                    try:
                        img_bytes_pie = fig_pie.to_image(format="png")
                        st.download_button(
                            label="📥 Descargar Gráfico (PNG)",
                            data=img_bytes_pie,
                            file_name="distribucion_tipos_incidente.png",
                            mime="image/png"
                        )
                    except Exception as e:
                        st.error("Error al generar PNG")
                
                with col_pie2:
                    html_bytes_pie = fig_pie.to_html().encode()
                    st.download_button(
                        label="📥 Descargar Gráfico (HTML)",
                        data=html_bytes_pie,
                        file_name="distribucion_tipos_incidente.html",
                        mime="text/html"
                    )
            else:
                st.warning("No hay datos de tipos de incidente.")
        
        with col4:
            # Evolución temporal
            st.write("**Evolución Temporal de Incidentes**")
            if 'fecha_processed' in df_filtered.columns:
                df_temp = df_filtered.dropna(subset=['fecha_processed'])
                if not df_temp.empty:
                    df_temp['fecha'] = df_temp['fecha_processed'].dt.date
                    daily_counts = df_temp['fecha'].value_counts().sort_index()
                    
                    fig_line = px.line(
                        x=daily_counts.index,
                        y=daily_counts.values,
                        title="Incidentes por Día",
                        labels={'x': 'Fecha', 'y': 'Número de Incidentes'}
                    )
                    fig_line.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig_line, use_container_width=True)
                    
                    # Botón para descargar gráfico de línea
                    col_line1, col_line2 = st.columns(2)
                    with col_line1:
                        try:
                            img_bytes_line = fig_line.to_image(format="png")
                            st.download_button(
                                label="📥 Descargar Gráfico (PNG)",
                                data=img_bytes_line,
                                file_name="evolucion_temporal_incidentes.png",
                                mime="image/png"
                            )
                        except Exception as e:
                            st.error("Error al generar PNG")
                    
                    with col_line2:
                        html_bytes_line = fig_line.to_html().encode()
                        st.download_button(
                            label="📥 Descargar Gráfico (HTML)",
                            data=html_bytes_line,
                            file_name="evolucion_temporal_incidentes.html",
                            mime="text/html"
                        )
                else:
                    st.warning("No hay datos de fechas válidas para el análisis temporal.")
            else:
                st.warning("No se encontró columna de fecha en los datos.")
        
        # Tabla de datos
        st.markdown("---")
        st.subheader("📋 Vista Previa de Datos")
        
        # Mostrar tabla con las columnas seleccionadas
        columnas_mostrar = [colonia_col, tipo_incidente_col]
        if lluvia_col:
            columnas_mostrar.append(lluvia_col)
        if 'fecha_processed' in df_filtered.columns:
            columnas_mostrar.append('fecha_processed')
        
        st.dataframe(
            df_filtered[columnas_mostrar].head(50),
            use_container_width=True,
            height=300
        )
        
        # Descargar datos filtrados
        try:
            csv = df_filtered.to_csv(index=False, encoding='utf-8')
            st.download_button(
                label="📥 Descargar Datos Filtrados (CSV)",
                data=csv,
                file_name="datos_incidentes_filtrados.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error("Error al generar el archivo CSV")
    
    else:
        st.error("No se pudieron cargar los datos. Por favor, verifica el formato del archivo.")

else:
    # Mensaje inicial cuando no hay archivo cargado
    st.markdown("""
    ## Bienvenido al Dashboard de Análisis de Incidentes
    
    **Para comenzar:**
    1. Sube tu archivo Excel con los datos de incidentes en el panel izquierdo
    2. Configura las columnas manualmente según tu archivo
    3. (Opcional) Sube un archivo GeoJSON con los límites de las colonias
    4. Explora los mapas de calor y gráficos generados automáticamente
    
    **Características:**
    - 🗺️ Mapa de calor interactivo de incidentes
    - 🏆 Top 10 colonias más afectadas
    - 🌧️ Top 10 colonias afectadas por lluvia
    - 📈 Gráficos descargables en PNG y HTML
    - 🔍 Filtros por tipo de incidente y lluvia
    - ⚙️ Control de capas del mapa
    - 📊 Análisis temporal y por categorías
    """)

# Footer
st.markdown("---")
st.markdown(
    "Desarrollado con Streamlit • "
    "Visualización de datos de incidentes en Magdalena Contreras"
)

# Información sobre Kaleido - CORREGIDO
st.sidebar.markdown("---")
st.sidebar.subheader("ℹ️ Información de Instalación")

st.sidebar.markdown("**Para exportar gráficos a PNG:**")
st.sidebar.markdown("1. Instala kaleido en tu entorno:")
st.sidebar.code("pip install kaleido")
st.sidebar.markdown("2. En Streamlit Cloud, agrégalo a `requirements.txt`")
st.sidebar.markdown("3. Reinicia la aplicación")
st.sidebar.markdown("📝 *Sin kaleido, solo podrás exportar en formato HTML*")
