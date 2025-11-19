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
        st.sidebar.write(f"Período: {df['fecha_del_incidente'].min().date()} - {df['fecha_del_incidente'].max().date()}")
        
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
        
        # Layout principal
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🗺️ Mapa de Calor de Incidentes")
            
            # Crear mapa base
            if not df_filtered[['latitud', 'longitud']].dropna().empty:
                # Calcular centro del mapa
                avg_lat = df_filtered['latitud'].mean()
                avg_lon = df_filtered['longitud'].mean()
                
                m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)
                
                # Preparar datos para heatmap
                heat_data = []
                for idx, row in df_filtered.dropna(subset=['latitud', 'longitud']).iterrows():
                    heat_data.append([row['latitud'], row['longitud'], 1])
                
                # Añadir heatmap
                HeatMap(heat_data, radius=15, blur=10, gradient={
                    0.4: 'blue',
                    0.6: 'cyan',
                    0.7: 'lime',
                    0.8: 'yellow',
                    1.0: 'red'
                }).add_to(m)
                
                # Añadir capa GeoJSON si está disponible
                if uploaded_geojson is not None:
                    gdf = load_geojson(uploaded_geojson)
                    if gdf is not None:
                        # Asegurarse de que el GeoJSON esté en WGS84
                        if gdf.crs != 'EPSG:4326':
                            gdf = gdf.to_crs('EPSG:4326')
                        
                        folium.GeoJson(
                            gdf,
                            name="Límites de Colonias",
                            style_function=lambda x: {
                                'fillColor': 'transparent',
                                'color': 'black',
                                'weight': 1,
                                'fillOpacity': 0.1
                            },
                            tooltip=folium.GeoJsonTooltip(
                                fields=[col for col in gdf.columns if col != 'geometry'],
                                aliases=[col for col in gdf.columns if col != 'geometry']
                            )
                        ).add_to(m)
                
                # Mostrar mapa
                folium_static(m, width=700, height=500)
                
                # Botón para descargar mapa
                map_html = m._repr_html_()
                st.download_button(
                    label="📥 Descargar Mapa (HTML)",
                    data=map_html,
                    file_name="mapa_calor_incidentes.html",
                    mime="text/html"
                )
            else:
                st.warning("No hay datos de coordenadas para generar el mapa de calor.")
        
        with col2:
            st.subheader("🏆 Top 10 Colonias Más Afectadas")
            
            # Contar incidentes por colonia
            colonia_counts = df_filtered['colonia'].value_counts().head(10)
            
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
                height=500,
                showlegend=False,
                yaxis={'categoryorder': 'total ascending'}
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Botones para descargar gráfico de barras
            col_download1, col_download2 = st.columns(2)
            
            with col_download1:
                # Descargar como PNG
                img_bytes = fig_bar.to_image(format="png")
                st.download_button(
                    label="📥 Descargar Gráfico (PNG)",
                    data=img_bytes,
                    file_name="top10_colonias_incidentes.png",
                    mime="image/png"
                )
            
            with col_download2:
                # Descargar como HTML
                html_bytes = fig_bar.to_html().encode()
                st.download_button(
                    label="📥 Descargar Gráfico (HTML)",
                    data=html_bytes,
                    file_name="top10_colonias_incidentes.html",
                    mime="text/html"
                )
        
        # Sección adicional de análisis
        st.markdown("---")
        st.subheader("📈 Análisis Detallado por Colonia")
        
        col3, col4 = st.columns(2)
        
        with col3:
            # Distribución por tipo de incidente
            st.write("**Distribución de Tipos de Incidente**")
            tipo_counts = df_filtered['tipo_de_reporte_(incidente)'].value_counts().head(10)
            fig_pie = px.pie(
                values=tipo_counts.values,
                names=tipo_counts.index,
                title="Top 10 Tipos de Incidente Más Comunes"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col4:
            # Evolución temporal
            st.write("**Evolución Temporal de Incidentes**")
            df_temp = df_filtered.copy()
            df_temp['fecha'] = pd.to_datetime(df_temp['fecha_del_incidente']).dt.date
            daily_counts = df_temp['fecha'].value_counts().sort_index()
            
            fig_line = px.line(
                x=daily_counts.index,
                y=daily_counts.values,
                title="Incidentes por Día",
                labels={'x': 'Fecha', 'y': 'Número de Incidentes'}
            )
            st.plotly_chart(fig_line, use_container_width=True)
        
        # Tabla de datos
        st.markdown("---")
        st.subheader("📋 Datos Detallados")
        
        # Mostrar tabla con paginación
        st.dataframe(
            df_filtered[[
                'fecha_del_incidente', 
                'colonia', 
                'tipo_de_reporte_(incidente)',
                'descripcion_del_incidente'
            ]].head(100),
            use_container_width=True
        )
        
        # Descargar datos filtrados
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Descargar Datos Filtrados (CSV)",
            data=csv,
            file_name="datos_incidentes_filtrados.csv",
            mime="text/csv"
        )
    
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
    - 📈 Gráficos descargables en PNG y HTML
    - 🔍 Filtros por tipo de incidente
    - 📊 Análisis temporal y por categorías
    """)
    
    # Ejemplo de cómo debería verse la data
    st.info("""
    **Estructura esperada del archivo Excel:**
    - fecha_del_incidente
    - colonia
    - tipo_de_reporte_(incidente) 
    - descripcion_del_incidente
    - latitud
    - longitud
    """)

# Footer
st.markdown("---")
st.markdown(
    "Desarrollado con Streamlit • "
    "Visualización de datos de incidentes en Magdalena Contreras"
)
