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

# Inicializar session_state para previsualización
if 'preview_fig' not in st.session_state:
    st.session_state.preview_fig = None
if 'last_chart_type' not in st.session_state:
    st.session_state.last_chart_type = None

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
        
        # Limpiar datos - manejar NaN y strings
        df = df.replace([np.nan, 'nan', 'NaN', ''], 'No especificado')
        
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
    
    # FUNCIONES DE CREACIÓN DE GRÁFICOS
    def apply_common_layout(fig):
        """Aplica el layout común a todos los gráficos"""
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
        
        return fig
    
    def create_bar_chart():
        """Crea gráfico de barras con personalización"""
        try:
            if orientation == "Vertical":
                if color_col != "Ninguna":
                    fig = px.bar(df, x=x_col, y=y_col, color=color_col, 
                                title=chart_title, barmode=barmode,
                                color_continuous_scale=color_scale.lower())
                else:
                    fig = px.bar(df, x=x_col, y=y_col, title=chart_title)
            else:
                if color_col != "Ninguna":
                    fig = px.bar(df, y=x_col, x=y_col, color=color_col,
                                title=chart_title, barmode=barmode,
                                color_continuous_scale=color_scale.lower())
                else:
                    fig = px.bar(df, y=x_col, x=y_col, title=chart_title)
            
            return apply_common_layout(fig)
            
        except Exception as e:
            st.error(f"❌ Error al generar gráfico de barras: {e}")
            return None
    
    def create_line_chart():
        """Crea gráfico de líneas con personalización"""
        try:
            if color_col != "Ninguna":
                fig = px.line(df, x=x_col, y=y_col, color=color_col, 
                             title=chart_title, markers=show_markers)
            else:
                fig = px.line(df, x=x_col, y=y_col, title=chart_title, markers=show_markers)
            
            return apply_common_layout(fig)
            
        except Exception as e:
            st.error(f"❌ Error al generar gráfico de líneas: {e}")
            return None
    
    def create_scatter_chart():
        """Crea gráfico de dispersión con personalización"""
        try:
            if color_col != "Ninguna":
                fig = px.scatter(df, x=x_col, y=y_col, color=color_col,
                                title=chart_title, size=size_col if size_col != "Ninguna" else None,
                                hover_data=hover_cols if hover_cols else None)
            else:
                fig = px.scatter(df, x=x_col, y=y_col, title=chart_title,
                                size=size_col if size_col != "Ninguna" else None,
                                hover_data=hover_cols if hover_cols else None)
            
            return apply_common_layout(fig)
            
        except Exception as e:
            st.error(f"❌ Error al generar gráfico de dispersión: {e}")
            return None
    
    def create_histogram_chart():
        """Crea histograma con personalización"""
        try:
            if color_col != "Ninguna":
                fig = px.histogram(df, x=x_col, color=color_col, 
                                  title=chart_title, nbins=n_bins,
                                  marginal=marginal_plot)
            else:
                fig = px.histogram(df, x=x_col, title=chart_title, 
                                  nbins=n_bins, marginal=marginal_plot)
            
            return apply_common_layout(fig)
            
        except Exception as e:
            st.error(f"❌ Error al generar histograma: {e}")
            return None
    
    def create_heatmap_chart():
        """Crea mapa de calor de correlación"""
        try:
            # Calcular matriz de correlación
            corr_matrix = df[numeric_cols].corr()
            
            fig = px.imshow(corr_matrix, 
                           title=chart_title,
                           color_continuous_scale=heatmap_color_scale,
                           aspect="auto")
            
            # Añadir anotaciones de valores
            if show_corr_values:
                for i in range(len(corr_matrix)):
                    for j in range(len(corr_matrix)):
                        fig.add_annotation(x=i, y=j, 
                                         text=f"{corr_matrix.iloc[i, j]:.2f}",
                                         showarrow=False,
                                         font=dict(color="white" if abs(corr_matrix.iloc[i, j]) > 0.5 else "black"))
            
            return apply_common_layout(fig)
            
        except Exception as e:
            st.error(f"❌ Error al generar mapa de calor: {e}")
            return None
    
    def create_pie_chart():
        """Crea gráfico de pastel con personalización"""
        try:
            if color_col != "Ninguna":
                fig = px.pie(df, names=names_col, values=values_col, 
                            color=color_col, title=chart_title)
            else:
                fig = px.pie(df, names=names_col, values=values_col, 
                            title=chart_title)
            
            # Personalización específica para pie chart
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(
                title={
                    'text': chart_title,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': title_size, 'family': font_family}
                },
                font={'family': font_family}
            )
            
            return fig
            
        except Exception as e:
            st.error(f"❌ Error al generar gráfico de pastel: {e}")
            return None
    
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
                help='Columna con valores "si" para lluvias'
            )
            
            # Valor para el mapa de calor
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            if not numeric_columns:
                st.warning("⚠️ No se encontraron columnas numéricas en el dataset")
                value_col = None
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
        
        # Aplicar filtro MANUAL de lluvias según selección
        map_df = df.copy()
        if lluvia_col != "Ninguna" and lluvia_col in df.columns:
            if filtro_lluvia == "Solo reportes por lluvia":
                map_df = map_df[map_df[lluvia_col] == "si"]
                st.info(f"✅ Filtrado: Mostrando solo reportes por lluvia ({len(map_df)} registros)")
            elif filtro_lluvia == "Excluir reportes por lluvia":
                map_df = map_df[map_df[lluvia_col] != "si"]
                st.info(f"✅ Filtrado: Excluyendo reportes por lluvia ({len(map_df)} registros)")
            else:
                st.info("📊 Mostrando todos los registros (sin filtrar)")
        
        # VERIFICACIÓN DE DATOS PARA EL MAPA
        if lat_col and lon_col and value_col and not map_df.empty:
            # Verificar que las columnas existan y tengan datos
            missing_lat = map_df[lat_col].isna().sum()
            missing_lon = map_df[lon_col].isna().sum()
            missing_val = map_df[value_col].isna().sum()
            
            if missing_lat > 0 or missing_lon > 0:
                st.warning(f"⚠️ Se encontraron datos faltantes: Latitud({missing_lat}), Longitud({missing_lon})")
                # Limpiar datos faltantes en coordenadas
                map_df = map_df.dropna(subset=[lat_col, lon_col])
            
            # Crear mapa de calor
            if st.button("🔄 Generar Mapa de Calor") or (auto_update and st.session_state.last_chart_type == "Mapa de Calor Geográfico"):
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
                        if lluvia_col != "Ninguna" and lluvia_col in row:
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
                            tooltip=f"Valor: {row[value_col]}"
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
                    
                except Exception as e:
                    st.error(f"❌ Error al generar mapa: {str(e)}")
        else:
            if map_df.empty:
                st.error("❌ No hay datos después de aplicar los filtros. Ajusta los criterios de filtrado.")
            else:
                st.error("❌ Por favor selecciona todas las columnas requeridas (Latitud, Longitud y Valor)")
    
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
            barmode = st.selectbox("Modo de barras", ["group", "stack", "relative"])
        with col_opt2:
            color_scale = st.selectbox("Escala de colores", 
                                      ["Viridis", "Plasma", "Inferno", "Magma", "Cividis", "Blues", "Reds"])
        
        # Previsualización en tiempo real
        if auto_update:
            preview_fig = create_bar_chart()
            if preview_fig:
                st.plotly_chart(preview_fig, use_container_width=True)
                st.session_state.preview_fig = preview_fig
                st.session_state.last_chart_type = "Gráfico de Barras"
        
        # Botón de generación final
        if st.button("🔄 Generar Gráfico Final"):
            final_fig = create_bar_chart()
            if final_fig:
                st.plotly_chart(final_fig, use_container_width=True)
                
                # Botón de descarga
                st.markdown("---")
                st.subheader("💾 Descargar Gráfico")
                st.markdown(
                    get_image_download_link(final_fig, "grafico_barras.png"), 
                    unsafe_allow_html=True
                )
    
    # GRÁFICO DE LÍNEAS
    elif chart_type == "Gráfico de Líneas":
        st.subheader("📈 Configuración del Gráfico de Líneas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            x_col = st.selectbox("Columna para eje X", df.columns, key="line_x")
        with col2:
            y_col = st.selectbox("Columna para eje Y", 
                                df.select_dtypes(include=[np.number]).columns.tolist(), 
                                key="line_y")
        
        # Opciones adicionales
        color_col = st.selectbox("Columna para colorear (opcional)", 
                                ["Ninguna"] + list(df.columns), key="line_color")
        
        show_markers = st.checkbox("Mostrar marcadores", value=True)
        
        # Previsualización en tiempo real
        if auto_update:
            preview_fig = create_line_chart()
            if preview_fig:
                st.plotly_chart(preview_fig, use_container_width=True)
                st.session_state.preview_fig = preview_fig
                st.session_state.last_chart_type = "Gráfico de Líneas"
        
        # Botón de generación final
        if st.button("🔄 Generar Gráfico Final"):
            final_fig = create_line_chart()
            if final_fig:
                st.plotly_chart(final_fig, use_container_width=True)
                
                # Botón de descarga
                st.markdown("---")
                st.subheader("💾 Descargar Gráfico")
                st.markdown(
                    get_image_download_link(final_fig, "grafico_lineas.png"), 
                    unsafe_allow_html=True
                )
    
    # GRÁFICO DE DISPERSIÓN
    elif chart_type == "Gráfico de Dispersión":
        st.subheader("🔵 Configuración del Gráfico de Dispersión")
        
        col1, col2 = st.columns(2)
        
        with col1:
            x_col = st.selectbox("Columna para eje X", df.columns, key="scatter_x")
        with col2:
            y_col = st.selectbox("Columna para eje Y", 
                                df.select_dtypes(include=[np.number]).columns.tolist(), 
                                key="scatter_y")
        
        # Opciones adicionales
        color_col = st.selectbox("Columna para colorear (opcional)", 
                                ["Ninguna"] + list(df.columns), key="scatter_color")
        
        size_col = st.selectbox("Columna para tamaño (opcional)", 
                               ["Ninguna"] + df.select_dtypes(include=[np.number]).columns.tolist())
        
        hover_cols = st.multiselect("Datos para hover (opcional)", df.columns)
        
        # Previsualización en tiempo real
        if auto_update:
            preview_fig = create_scatter_chart()
            if preview_fig:
                st.plotly_chart(preview_fig, use_container_width=True)
                st.session_state.preview_fig = preview_fig
                st.session_state.last_chart_type = "Gráfico de Dispersión"
        
        # Botón de generación final
        if st.button("🔄 Generar Gráfico Final"):
            final_fig = create_scatter_chart()
            if final_fig:
                st.plotly_chart(final_fig, use_container_width=True)
                
                # Botón de descarga
                st.markdown("---")
                st.subheader("💾 Descargar Gráfico")
                st.markdown(
                    get_image_download_link(final_fig, "grafico_dispersion.png"), 
                    unsafe_allow_html=True
                )
    
    # HISTOGRAMA
    elif chart_type == "Histograma":
        st.subheader("📊 Configuración del Histograma")
        
        x_col = st.selectbox("Columna para histograma", df.columns, key="hist_x")
        
        color_col = st.selectbox("Columna para colorear (opcional)", 
                                ["Ninguna"] + list(df.columns), key="hist_color")
        
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            n_bins = st.slider("Número de bins", 5, 100, 20)
        with col_opt2:
            marginal_plot = st.selectbox("Gráfico marginal", 
                                        [None, "box", "violin", "rug"])
        
        # Previsualización en tiempo real
        if auto_update:
            preview_fig = create_histogram_chart()
            if preview_fig:
                st.plotly_chart(preview_fig, use_container_width=True)
                st.session_state.preview_fig = preview_fig
                st.session_state.last_chart_type = "Histograma"
        
        # Botón de generación final
        if st.button("🔄 Generar Gráfico Final"):
            final_fig = create_histogram_chart()
            if final_fig:
                st.plotly_chart(final_fig, use_container_width=True)
                
                # Botón de descarga
                st.markdown("---")
                st.subheader("💾 Descargar Gráfico")
                st.markdown(
                    get_image_download_link(final_fig, "histograma.png"), 
                    unsafe_allow_html=True
                )
    
    # MAPA DE CALOR DE CORRELACIÓN
    elif chart_type == "Mapa de Calor de Correlación":
        st.subheader("🔥 Configuración del Mapa de Calor de Correlación")
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) < 2:
            st.error("❌ Se necesitan al menos 2 columnas numéricas para el mapa de calor de correlación")
        else:
            selected_cols = st.multiselect("Selecciona columnas para correlación", 
                                          numeric_cols, 
                                          default=numeric_cols[:min(5, len(numeric_cols))])
            
            if len(selected_cols) >= 2:
                col_opt1, col_opt2 = st.columns(2)
                with col_opt1:
                    heatmap_color_scale = st.selectbox("Escala de colores", 
                                                      ["Viridis", "Plasma", "Inferno", "Magma", "Cividis", "RdBu", "Blues"])
                with col_opt2:
                    show_corr_values = st.checkbox("Mostrar valores de correlación", value=True)
                
                # Previsualización en tiempo real
                if auto_update:
                    preview_fig = create_heatmap_chart()
                    if preview_fig:
                        st.plotly_chart(preview_fig, use_container_width=True)
                        st.session_state.preview_fig = preview_fig
                        st.session_state.last_chart_type = "Mapa de Calor de Correlación"
                
                # Botón de generación final
                if st.button("🔄 Generar Gráfico Final"):
                    final_fig = create_heatmap_chart()
                    if final_fig:
                        st.plotly_chart(final_fig, use_container_width=True)
                        
                        # Botón de descarga
                        st.markdown("---")
                        st.subheader("💾 Descargar Gráfico")
                        st.markdown(
                            get_image_download_link(final_fig, "mapa_calor_correlacion.png"), 
                            unsafe_allow_html=True
                        )
    
    # GRÁFICO DE PASTEL
    elif chart_type == "Gráfico de Pastel":
        st.subheader("🥧 Configuración del Gráfico de Pastel")
        
        col1, col2 = st.columns(2)
        
        with col1:
            names_col = st.selectbox("Columna para categorías", df.columns, key="pie_names")
        with col2:
            values_col = st.selectbox("Columna para valores", 
                                     df.select_dtypes(include=[np.number]).columns.tolist(), 
                                     key="pie_values")
        
        color_col = st.selectbox("Columna para colorear (opcional)", 
                                ["Ninguna"] + list(df.columns), key="pie_color")
        
        # Previsualización en tiempo real
        if auto_update:
            preview_fig = create_pie_chart()
            if preview_fig:
                st.plotly_chart(preview_fig, use_container_width=True)
                st.session_state.preview_fig = preview_fig
                st.session_state.last_chart_type = "Gráfico de Pastel"
        
        # Botón de generación final
        if st.button("🔄 Generar Gráfico Final"):
            final_fig = create_pie_chart()
            if final_fig:
                st.plotly_chart(final_fig, use_container_width=True)
                
                # Botón de descarga
                st.markdown("---")
                st.subheader("💾 Descargar Gráfico")
                st.markdown(
                    get_image_download_link(final_fig, "grafico_pastel.png"), 
                    unsafe_allow_html=True
                )

else:
    st.info("👆 Por favor carga un archivo de datos en el sidebar para comenzar")

# Información adicional
with st.sidebar.expander("ℹ️ Instrucciones de Uso"):
    st.markdown("""
    **📝 Instrucciones:**
    
    **Previsualización en Tiempo Real:**
    - Activa "Actualización automática" para ver cambios instantáneamente
    - Todos los gráficos se actualizan automáticamente
    
    **Mapas de Calor:**
    1. Sube archivo con columnas de latitud/longitud
    2. Selecciona columnas para coordenadas
    3. Usa filtro MANUAL de lluvias si es necesario
    4. Para GeoJSON: selecciona columnas de colonias y alcaldías
    5. Personaliza títulos y apariencia
    6. Genera y descarga
    
    **Filtro de Lluvias:**
    - **Mostrar todos**: Sin filtro
    - **Solo lluvias**: Solo registros con "si"
    - **Excluir lluvias**: Registros sin "si"
    """)

st.markdown("---")
st.markdown("*Sistema de Visualización - Desarrollado con Streamlit*")
