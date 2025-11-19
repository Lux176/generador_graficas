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
        
        # Limpieza básica de datos
        df['colonia'] = df['colonia'].str.strip().str.title()
        df = df.dropna(subset=['colonia'])
        
        # Convertir fecha a formato datetime de manera segura
        df['fecha_del_incidente'] = pd.to_datetime(df['fecha_del_incidente'], errors='coerce')
        
        # Convertir latitud y longitud a numérico, manejando errores
        df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
        df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
        
        # Filtrar coordenadas inválidas o fuera de rango razonable para México
        df = df[
            (df['latitud'].between(19.0, 20.0)) & 
            (df['longitud'].between(-99.3, -99.1))
        ]
        
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
def create_heatmap(df_filtered, geojson_data=None, colonia_column=None, show_heatmap=True, show_boundaries=True):
    """Crea un mapa de calor con los datos filtrados"""
    # Filtrar coordenadas válidas
    coordenadas_validas = df_filtered[['latitud', 'longitud']].dropna()
    
    if coordenadas_validas.empty:
        return None
    
    # Calcular centro del mapa de manera segura
    try:
        avg_lat = coordenadas_validas['latitud'].mean()
        avg_lon = coordenadas_validas['longitud'].mean()
    except Exception as e:
        st.error(f"Error calculando centro del mapa: {str(e)}")
        # Usar coordenadas por defecto de Magdalena Contreras
        avg_lat = 19.32
        avg_lon = -99.24
    
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)
    
    # Preparar datos para heatmap
    heat_data = []
    for idx, row in df_filtered.dropna(subset=['latitud', 'longitud']).iterrows():
        heat_data.append([row['latitud'], row['longitud'], 1])
    
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
        st.sidebar.subheader("📈 Resumen de Datos")
        st.sidebar.write(f"Total de registros: {len(df):,}")
        st.sidebar.write(f"Total de colonias: {df['colonia'].nunique()}")
        st.sidebar.write(f"Registros con coordenadas válidas: {df[['latitud', 'longitud']].notna().all(axis=1).sum()}")
        
        # Manejo seguro de las fechas
        fechas_validas = df['fecha_del_incidente'].dropna()
        if not fechas_validas.empty:
            min_date = fechas_validas.min().date()
            max_date = fechas_validas.max().date()
            st.sidebar.write(f"Período: {min_date} - {max_date}")
        else:
            st.sidebar.write("Período: No disponible")
        
        # Filtros en sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filtros")
        
        # Filtro por tipo de incidente
        tipos_incidente = ['Todos'] + sorted(df['tipo_de_reporte_(incidente)'].dropna().unique().tolist())
        selected_tipo = st.sidebar.selectbox(
            "Tipo de incidente:",
            tipos_incidente
        )
        
        # Aplicar filtros
        if selected_tipo != 'Todos':
            df_filtered = df[df['tipo_de_reporte_(incidente)'] == selected_tipo].copy()
        else:
            df_filtered = df.copy()
        
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
                available_columns = [col for col in geojson_data.columns if col != 'geometry']
                if available_columns:
                    colonia_column = st.sidebar.selectbox(
                        "Selecciona la columna con nombres de colonias:",
                        available_columns
                    )
        
        # Layout principal
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🗺️ Mapa de Calor de Incidentes")
            
            # Crear mapa
            m = create_heatmap(df_filtered, geojson_data, colonia_column, show_heatmap, show_boundaries)
            
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
                st.info("""
                **Solución:**
                - Verifique que las columnas 'latitud' y 'longitud' contengan valores numéricos
                - Asegúrese de que las coordenadas estén en el rango aproximado de la Ciudad de México
                - Las coordenadas deben estar en formato decimal (ej: 19.4326, -99.1332)
                """)
        
        with col2:
            st.subheader("🏆 Top 10 Colonias Más Afectadas")
            
            # Contar incidentes por colonia
            colonia_counts = df_filtered['colonia'].value_counts().head(10)
            
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
                        st.error("Error al generar PNG. Instale: pip install kaleido")
                
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
            
            # NUEVA GRÁFICA: Colonias más afectadas por lluvia
            st.subheader("🌧️ Top 10 Colonias por Incidentes de Lluvia")
            
            # Filtrar incidentes relacionados con lluvia
            # Buscar en descripción o tipo de reporte
            lluvia_keywords = ['lluvia', 'lluvias', 'inundacion', 'inundaciones', 'encharcamiento', 'precipitacion', 'pluvial']
            
            def contains_lluvia(text):
                if pd.isna(text):
                    return False
                text_str = str(text).lower()
                return any(keyword in text_str for keyword in lluvia_keywords)
            
            # Aplicar filtro
            df_lluvia = df_filtered[
                df_filtered['descripcion_del_incidente'].apply(contains_lluvia) |
                df_filtered['tipo_de_reporte_(incidente)'].apply(contains_lluvia)
            ]
            
            colonia_lluvia_counts = df_lluvia['colonia'].value_counts().head(10)
            
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
                st.info(f"**Total de incidentes relacionados con lluvia:** {len(df_lluvia)}")
            else:
                st.warning("No se encontraron incidentes relacionados con lluvia en los datos filtrados.")
        
        # Sección adicional de análisis
        st.markdown("---")
        st.subheader("📈 Análisis Detallado")
        
        col3, col4 = st.columns(2)
        
        with col3:
            # Distribución por tipo de incidente
            st.write("**Distribución de Tipos de Incidente**")
            tipo_counts = df_filtered['tipo_de_reporte_(incidente)'].value_counts().head(10)
            if not tipo_counts.empty:
                fig_pie = px.pie(
                    values=tipo_counts.values,
                    names=tipo_counts.index,
                    title="Top 10 Tipos de Incidente Más Comunes"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.warning("No hay datos de tipos de incidente.")
        
        with col4:
            # Evolución temporal
            st.write("**Evolución Temporal de Incidentes**")
            df_temp = df_filtered.copy()
            # Usar solo fechas válidas
            df_temp = df_temp.dropna(subset=['fecha_del_incidente'])
            if not df_temp.empty:
                df_temp['fecha'] = df_temp['fecha_del_incidente'].dt.date
                daily_counts = df_temp['fecha'].value_counts().sort_index()
                
                fig_line = px.line(
                    x=daily_counts.index,
                    y=daily_counts.values,
                    title="Incidentes por Día",
                    labels={'x': 'Fecha', 'y': 'Número de Incidentes'}
                )
                fig_line.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.warning("No hay datos de fechas válidas para el análisis temporal.")
        
        # Tabla de datos
        st.markdown("---")
        st.subheader("📋 Vista Previa de Datos")
        
        # Mostrar tabla con las columnas disponibles
        columnas_disponibles = [col for col in ['fecha_del_incidente', 'colonia', 'tipo_de_reporte_(incidente)', 'descripcion_del_incidente'] 
                               if col in df_filtered.columns]
        
        st.dataframe(
            df_filtered[columnas_disponibles].head(50),
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
    2. (Opcional) Sube un archivo GeoJSON con los límites de las colonias
    3. Explora los mapas de calor y gráficos generados automáticamente
    
    **Características:**
    - 🗺️ Mapa de calor interactivo de incidentes
    - 🏆 Top 10 colonias más afectadas
    - 🌧️ Top 10 colonias afectadas por lluvia
    - 📈 Gráficos descargables en PNG y HTML
    - 🔍 Filtros por tipo de incidente
    - ⚙️ Control de capas del mapa
    - 📊 Análisis temporal y por categorías
    """)
    
    # Ejemplo de cómo debería verse la data
    st.info("""
    **Estructura esperada del archivo Excel:**
    - fecha_del_incidente
    - colonia
    - tipo_de_reporte_(incidente) 
    - descripcion_del_incidente
    - latitud (valores numéricos, ej: 19.4326)
    - longitud (valores numéricos, ej: -99.1332)
    """)

# Footer
st.markdown("---")
st.markdown(
    "Desarrollado con Streamlit • "
    "Visualización de datos de incidentes en Magdalena Contreras"
)
