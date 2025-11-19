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
    
    # MAPA DE CALOR GEOGRÁFICO
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
                help='Columna con valores "si" para lluvias y "nan" para otros'
            )
            
            # Valor para el mapa de calor
            value_col = st.selectbox(
                "Columna para valores del mapa de calor",
                df.select_dtypes(include=[np.number]).columns.tolist() if not df.empty else []
            )
            
            # Opciones de filtro MANUAL
            filtro_lluvia = st.radio(
                "Filtrar por reportes de lluvia:",
                ["Mostrar todos", "Solo reportes por lluvia", "Excluir reportes por lluvia"]
            )
        
        # Aplicar filtro MANUAL de lluvias según selección
        map_df = df.copy()
        if lluvia_col != "Ninguna" and lluvia_col in df.columns:
            if filtro_lluvia == "Solo reportes por lluvia":
                map_df = map_df[map_df[lluvia_col] == "si"]
                st.info(f"✅ Filtrado: Mostrando solo reportes por lluvia ({len(map_df)} registros)")
            elif filtro_lluvia == "Excluir reportes por lluvia":
                map_df = map_df[map_df[lluvia_col].isna() | (map_df[lluvia_col] != "si")]
                st.info(f"✅ Filtrado: Excluyendo reportes por lluvia ({len(map_df)} registros)")
            else:
                st.info("📊 Mostrando todos los registros (sin filtrar)")
        
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
        
        # Crear mapa de calor
        if st.button("🔄 Generar Mapa de Calor"):
            if lat_col and lon_col and value_col:
                try:
                    # Crear mapa base
                    center_lat = map_df[lat_col].mean()
                    center_lon = map_df[lon_col].mean()
                    
                    m = folium.Map(
                        location=[center_lat, center_lon],
                        zoom_start=map_zoom,
                        tiles='OpenStreetMap'
                    )
                    
                    # Añadir puntos de calor
                    for idx, row in map_df.iterrows():
                        # Calcular tamaño basado en el valor (si es numérico)
                        try:
                            valor = float(row[value_col])
                            radius = max(heat_radius, heat_radius * (valor / map_df[value_col].max()))
                        except:
                            radius = heat_radius
                        
                        popup_text = f"""
                        <b>Valor:</b> {row[value_col]}<br>
                        <b>Lat:</b> {row[lat_col]:.4f}<br>
                        <b>Lon:</b> {row[lon_col]:.4f}<br>
                        """
                        if colonia_col != "Ninguna" and colonia_col in row:
                            popup_text += f"<b>Colonia:</b> {row[colonia_col]}<br>"
                        
                        folium.CircleMarker(
                            location=[row[lat_col], row[lon_col]],
                            radius=radius,
                            popup=folium.Popup(popup_text, max_width=300),
                            color=heat_color,
                            fill=True,
                            fillColor=heat_color,
                            fillOpacity=heat_opacity,
                            opacity=0.8
                        ).add_to(m)
                    
                    # Añadir título al mapa
                    title_html = f'''
                    <h3 align="center" style="font-size:20px"><b>{chart_title}</b></h3>
                    '''
                    m.get_root().html.add_child(folium.Element(title_html))
                    
                    # Mostrar mapa
                    folium_static(m, width=800, height=map_height)
                    
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
                    
                except Exception as e:
                    st.error(f"❌ Error al generar mapa: {e}")
            else:
                st.warning("⚠️ Por favor selecciona las columnas requeridas")
    
    # GRÁFICO DE BARRAS
    elif chart_type == "Gráfico de Barras":
        st.subheader("📊 Configuración del Gráfico de Barras")
        
        col1, col2 = st.columns(2)
        
        with col1:
            x_col = st.selectbox("Columna para eje X", df.columns, key="bar_x")
        with col2:
            y_col = st.selectbox("Columna para eje Y", 
                                df.select_dtypes(include=[np.number]).columns.tolist(), 
                                key="bar_y")
        
        # Opciones adicionales
        color_col = st.selectbox("Columna para colorear (opcional)", 
                                ["Ninguna"] + list(df.columns), key="bar_color")
        
        # Personalización adicional para barras
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            orientation = st.radio("Orientación", ["Vertical", "Horizontal"])
            barmode = st.selectbox("Modo de barras", ["group", "stack"])
        with col_opt2:
            color_scale = st.selectbox("Escala de colores", 
                                      ["Viridis", "Plasma", "Inferno", "Magma", "Cividis"])
        
        if st.button("🔄 Generar Gráfico de Barras"):
            try:
                if orientation == "Vertical":
                    if color_col != "Ninguna":
                        fig = px.bar(df, x=x_col, y=y_col, color=color_col, 
                                    title=chart_title, barmode=barmode,
                                    color_continuous_scale=color_scale.lower())
                    else:
                        fig = px.bar(df, x=x_col, y=y_col, 
                                    title=chart_title)
                else:
                    if color_col != "Ninguna":
                        fig = px.bar(df, y=x_col, x=y_col, color=color_col,
                                    title=chart_title, barmode=barmode,
                                    color_continuous_scale=color_scale.lower())
                    else:
                        fig = px.bar(df, y=x_col, x=y_col, 
                                    title=chart_title)
                
                # Aplicar personalización
                fig.update_layout(
                    title={
                        'text': chart_title,
                        'x': 0.5,
                        'xanchor': 'center',
                        'font': {'size': title_size, 'family': font_family}
                    },
                    xaxis_title={
                        'text': xaxis_title,
                        'font': {'size': label_size, 'family': font_family}
                    },
                    yaxis_title={
                        'text': yaxis_title,
                        'font': {'size': label_size, 'family': font_family}
                    },
                    font={'family': font_family},
                    showlegend=True
                )
                
                # Ajustar tamaño de etiquetas de ejes
                fig.update_xaxes(tickfont=dict(size=label_size-2))
                fig.update_yaxes(tickfont=dict(size=label_size-2))
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Botón de descarga
                st.markdown("---")
                st.subheader("💾 Descargar Gráfico")
                st.markdown(
                    get_image_download_link(fig, "grafico_barras.png"), 
                    unsafe_allow_html=True
                )
                
            except Exception as e:
                st.error(f"❌ Error al generar gráfico: {e}")

else:
    st.info("👆 Por favor carga un archivo de datos en el sidebar para comenzar")

# Información adicional
with st.sidebar.expander("ℹ️ Instrucciones de Uso"):
    st.markdown("""
    **📝 Instrucciones:**
    
    **Mapas de Calor:**
    1. Sube archivo con columnas de latitud/longitud
    2. Selecciona columnas para coordenadas
    3. Usa filtro MANUAL de lluvias si es necesario
    4. Personaliza títulos y apariencia
    5. Genera y descarga
    
    **Filtro de Lluvias:**
    - **Mostrar todos**: Sin filtro
    - **Solo lluvias**: Solo registros con "si"
    - **Excluir lluvias**: Registros sin "si"
    
    **Personalización:**
    - Edita títulos y etiquetas
    - Ajusta tamaños de fuente
    - Modifica colores y estilos
    """)

st.markdown("---")
st.markdown("*Sistema de Visualización - Desarrollado con Streamlit*")
