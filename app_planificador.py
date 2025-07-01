# app_planificador.py (Versión Final)

import dash
from dash import Dash, dash_table, html, dcc, Input, Output, State, MATCH
import pandas as pd
import os
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
from fpdf import FPDF

# --- 1. CONFIGURACIÓN INICIAL Y DATOS ---
DATA_PATH = "data"
REQ_FILE = os.path.join(DATA_PATH, "requerimientos.csv")
FERT_FILE = os.path.join(DATA_PATH, "fertilizantes.csv")
DIST1_FILE = os.path.join(DATA_PATH, "distribucion_1.csv")
DIST2_FILE = os.path.join(DATA_PATH, "distribucion_2.csv")
VALV_FILE = os.path.join(DATA_PATH, "valvulas.csv")
FECHA_FILE = os.path.join(DATA_PATH, "fecha_inicio_riego.txt")
LIMITES_FILE = os.path.join(DATA_PATH, "limites_nutrientes.csv")
PLAN_SEMANAL_FILE = os.path.join(DATA_PATH, "plan_semanal_guardado.csv")
APLIC_REALES_FILE = os.path.join(DATA_PATH, "aplicaciones_reales.csv")

if not os.path.exists(DATA_PATH): os.makedirs(DATA_PATH)
if not os.path.exists('assets'): os.makedirs('assets')

# --- Funciones para definir datos por defecto ---
def definir_requerimientos(): return pd.DataFrame({'Sector': ["Chacra Vieja", "Chacra Pivot", "Chacra Isla", "Chacra Isla", "Chacra Isla", "Chacra Isla"], 'Anio': [2011, 2012, 2016, 2017, 2018, 2019], 'Sup_ha': [11, 38, 30, 34, 14, 55], 'N': [180, 200, 190, 180, 170, 140], 'P': [70, 65, 60, 45, 40, 30], 'K': [240, 230, 230, 180, 140, 120], 'Mg': [30, 25, 20, 18, 15, 15]})
def definir_fertilizantes(): return pd.DataFrame({'Producto': ["BIOINICIO", "NITRON", "BIOPRODUCCION", "BIOPREMIUM"], 'N': [0.03, 0.28, 0, 0], 'P2O5': [0.20, 0, 0, 0], 'K2O': [0, 0, 0.20, 0], 'S': [0, 0.03, 0.08, 0.06], 'MgO': [0, 0, 0, 0.06], 'Densidad': [1.188, 1.320, 1.250, 1.350], 'Precio': [2.5, 1.8, 2.0, 3.0]})
def definir_distribucion1(): return pd.DataFrame({'Mes': ["Octubre", "Noviembre", "Diciembre", "Enero", "Febrero/Marzo"], 'N': [0.10, 0.27, 0.33, 0.15, 0.15], 'P': [0, 0, 0.70, 0, 0.30], 'K': [0, 0.25, 0.45, 0.10, 0.20], 'Mg': [0, 0.30, 0.30, 0.15, 0.25]})
def definir_distribucion2(): return pd.DataFrame({'Mes': ["Octubre", "Noviembre", "Diciembre", "Enero", "Febrero/Marzo"], 'N': [0.10, 0.35, 0.35, 0.10, 0.10], 'P': [0, 0, 0.70, 0.10, 0.20], 'K': [0, 0.20, 0.50, 0.15, 0.15], 'Mg': [0, 0.30, 0.30, 0.15, 0.25]})
def definir_valvulas(): return pd.DataFrame({'Año': [2011, 2012, 2016, 2017, 2018, 2018.1, 2019, 2019.1], 'Valvula_1': [12, 4.6, 8.0, 5, 7.8, 6, 11, 8], 'Valvula_2': [26, 6.4, 9.1, 5, 7.7, np.nan, 12, np.nan], 'Valvula_3': [np.nan, np.nan, 8.5, 5, 10.4, np.nan, 12, np.nan], 'Valvula_4': [np.nan, np.nan, 9.7, 5, 8.8, np.nan, 10, np.nan]})
def definir_limites(): return pd.DataFrame({'Nutriente': ['N', 'P', 'K', 'Mg'], 'Limite_kg_ha_app': [40, 20, 35, 5]})

# --- Funciones de Lógica ---
def cargar_o_crear(filepath, default_function):
    if os.path.exists(filepath):
        try: return pd.read_csv(filepath)
        except pd.errors.EmptyDataError: return default_function()
    else:
        df = default_function(); df.to_csv(filepath, index=False); return df

def generar_plan_mensual_economico():
    try:
        df_req = cargar_o_crear(REQ_FILE, definir_requerimientos); df_fert = cargar_o_crear(FERT_FILE, definir_fertilizantes); df_dist1 = cargar_o_crear(DIST1_FILE, definir_distribucion1); df_dist2 = cargar_o_crear(DIST2_FILE, definir_distribucion2)
        col_map_nutrientes = {'N': 'N', 'P': 'P2O5', 'K': 'K2O', 'Mg': 'MgO'}; resultados_list = []
        for _, req_row in df_req.iterrows():
            if pd.isna(req_row['Anio']) or pd.isna(req_row['Sup_ha']) or req_row['Sup_ha'] <= 0: continue
            anio_req = int(req_row['Anio']); dist = df_dist1 if anio_req in [2011, 2012, 2016, 2017] else df_dist2
            for _, dist_row in dist.iterrows():
                req_nutrientes_mes = {'N': req_row['N'] * dist_row['N'], 'P': req_row['P'] * dist_row['P'], 'K': req_row['K'] * dist_row['K'], 'Mg': req_row['Mg'] * dist_row['Mg']}
                for nutriente, req_kg_ha in req_nutrientes_mes.items():
                    if pd.isna(req_kg_ha) or req_kg_ha <= 0: continue
                    col_fert = col_map_nutrientes.get(nutriente)
                    if not col_fert: continue
                    fert_disponibles = df_fert[df_fert[col_fert] > 0]
                    if fert_disponibles.empty: continue
                    best_option, min_cost = None, float('inf')
                    for _, fert_row in fert_disponibles.iterrows():
                        concentracion, precio_kg, densidad = fert_row[col_fert], fert_row['Precio'], fert_row['Densidad']
                        if any(pd.isna([concentracion, precio_kg, densidad])) or densidad == 0 or concentracion == 0: continue
                        kg_producto_ha_final = req_kg_ha / concentracion
                        costo_total = kg_producto_ha_final * req_row['Sup_ha'] * precio_kg
                        if costo_total < min_cost:
                            min_cost = costo_total
                            best_option = {'Sector': req_row['Sector'], 'Año Plantación': req_row['Anio'], 'Mes': dist_row['Mes'], 'Nutriente Cubierto': nutriente, 'Producto': fert_row['Producto'], 'Dosis_kg_ha': kg_producto_ha_final, 'Total_kg': kg_producto_ha_final * req_row['Sup_ha'], 'Dosis_lt_ha': (kg_producto_ha_final / densidad), 'Total_lt': (kg_producto_ha_final * req_row['Sup_ha'] / densidad), 'Precio_usd_ha': kg_producto_ha_final * precio_kg, 'Costo_total_usd': costo_total}
                    if best_option: resultados_list.append(best_option)
        if not resultados_list: return pd.DataFrame({'Mensaje': ["No se generaron opciones."]})
        return pd.DataFrame(resultados_list)
    except Exception as e: return pd.DataFrame({'Error': [f"Ocurrió un error: {e}"]})

def generar_plan_semanal(df_plan_mensual, df_valvulas, df_limites, fecha_inicio_riego_str):
    if df_plan_mensual.empty or "Mensaje" in df_plan_mensual.columns or "Error" in df_plan_mensual.columns: return pd.DataFrame({'Error': ["Se necesita un Plan Mensual válido."]})
    try:
        df_limites_dict = df_limites.set_index('Nutriente')['Limite_kg_ha_app'].to_dict()
        fecha_inicio_plan_global = datetime.datetime.strptime(fecha_inicio_riego_str, '%Y-%m-%d').date()
        df_fert = cargar_o_crear(FERT_FILE, definir_fertilizantes)
        col_map_nutrientes = {'N': 'N', 'P': 'P2O5', 'K': 'K2O', 'Mg': 'MgO'}
        niveles_meses_dist = ["Octubre", "Noviembre", "Diciembre", "Enero", "Febrero/Marzo"]
        plan_semanal_list = []
        for index, fila in df_plan_mensual.iterrows():
            nutriente_actual = fila['Nutriente Cubierto']
            max_kg_nutriente_puro_ha_app = float(df_limites_dict.get(nutriente_actual, 40))
            anio_plan_vintage = fila['Año Plantación']
            producto_info_list = df_fert[df_fert['Producto'] == fila['Producto']]
            if producto_info_list.empty: continue
            producto_info = producto_info_list.iloc[0]
            concentracion_nutriente = producto_info.get(col_map_nutrientes.get(nutriente_actual))
            if pd.isna(concentracion_nutriente) or concentracion_nutriente <= 0 or pd.isna(producto_info['Densidad']) or producto_info['Densidad'] <= 0: continue
            valv_row = df_valvulas[df_valvulas['Año'] == fila['Año Plantación']]
            if valv_row.empty: continue
            valvulas_activas = valv_row.drop(columns=['Año']).dropna(axis=1)
            if valvulas_activas.empty: continue
            dosis_producto_ha_mes = fila['Dosis_kg_ha']
            kg_nutriente_ha_mes = dosis_producto_ha_mes * concentracion_nutriente
            num_total_aplicaciones = np.ceil(kg_nutriente_ha_mes / max_kg_nutriente_puro_ha_app) if kg_nutriente_ha_mes > 0 else 0
            if num_total_aplicaciones == 0: continue
            tasa_producto_ha_app_real = dosis_producto_ha_mes / num_total_aplicaciones
            try: mes_offset = niveles_meses_dist.index(fila['Mes'])
            except ValueError: continue
            fecha_inicio_mes_teorico = (fecha_inicio_plan_global.replace(day=1) + relativedelta(months=mes_offset))
            fecha_de_partida = max(fecha_inicio_plan_global, fecha_inicio_mes_teorico)
            fechas_aplicacion = pd.to_datetime(pd.date_range(start=fecha_de_partida, periods=int(num_total_aplicaciones), freq='W-MON').date)
            for valv_nombre, sup_valvula_series in valvulas_activas.items():
                sup_valvula = sup_valvula_series.iloc[0]
                if pd.isna(sup_valvula) or sup_valvula <= 0: continue
                kg_producto_valvula_app = tasa_producto_ha_app_real * sup_valvula
                lt_producto_valvula_app = kg_producto_valvula_app / producto_info['Densidad']
                for app_idx in range(int(num_total_aplicaciones)):
                    fecha_app_estimada = fechas_aplicacion[app_idx]
                    plan_semanal_list.append({'Sector': fila['Sector'],'Año Plantación': anio_plan_vintage,'Mes Plan': fila['Mes'],'Producto': fila['Producto'],'Válvula': valv_nombre,'Fecha Estimada': fecha_app_estimada,'Litros Planeados': lt_producto_valvula_app})
        return pd.DataFrame(plan_semanal_list) if plan_semanal_list else pd.DataFrame()
    except Exception as e: print(f"Error EXCEPCIONAL en generar_plan_semanal: {e}"); return pd.DataFrame({'Error': [f"Error al generar plan semanal: {e}"]})

# --- LAYOUT DE LA APP Y CALLBACKS ---
external_stylesheets = ['https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap', 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined']
app = Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=external_stylesheets)
server = app.server
app.title = "Planificador de Fertilización"

# --- Carga de datos iniciales ---
df_req_inicial = cargar_o_crear(REQ_FILE, definir_requerimientos)
df_fert_inicial = cargar_o_crear(FERT_FILE, definir_fertilizantes)
df_dist1_inicial = cargar_o_crear(DIST1_FILE, definir_distribucion1)
df_dist2_inicial = cargar_o_crear(DIST2_FILE, definir_distribucion2)
df_valv_inicial = cargar_o_crear(VALV_FILE, definir_valvulas)
df_limites_inicial = cargar_o_crear(LIMITES_FILE, definir_limites)
fecha_guardada_inicial = datetime.date.today().isoformat()
if os.path.exists(FECHA_FILE):
    with open(FECHA_FILE, 'r') as f: fecha_guardada_inicial = f.read()

def crear_acordeon_item(titulo, content_id, children, icono='table_rows'):
    return html.Div([
        html.Button([html.I(className="material-symbols-outlined", children=icono), html.Span(titulo, className='accordion-text'), html.I(className="material-symbols-outlined accordion-icon", children="expand_more")], id={'type': 'accordion-toggle', 'index': content_id}, className='accordion-button'),
        html.Div(className='accordion-content', id={'type': 'accordion-collapse', 'index': content_id}, children=children)
    ])

# --- Definición de Componentes y Layouts ---
nav_sidebar = html.Div(className='nav-sidebar', children=[
    dcc.Link(html.I(className="material-symbols-outlined", children="table_chart"), href="/", className="nav-link", id="link-planificacion"),
    dcc.Link(html.I(className="material-symbols-outlined", children="rule"), href="/seguimiento", className="nav-link", id="link-seguimiento"),
    html.Div(className="config-button-wrapper", children=[html.Button(html.I(className="material-symbols-outlined", children="settings"), id="btn-abrir-config", className="config-button")])
])

def crear_modal_configuracion():
    return html.Div(id='modal-backdrop', style={'display': 'none'}, children=[
        html.Div(className='modal-container', children=[
            html.Div(className='modal-header', children=[html.H2("Configuración Global"), html.Button("×", id="btn-cerrar-config", className="close-button")]),
            html.Div(className='modal-body', children=[
                crear_acordeon_item("Acciones", "content-acciones", [html.Div(id='notificacion-parametros', style={'marginBottom': '10px'}), html.Button("Guardar Configuración", id="btn-guardar-parametros", className="Button Button-primary", style={'width': '100%'}), html.Button("Restaurar Defaults", id="btn-restaurar-parametros", className="Button Button-secondary", style={'width': '100%', 'marginTop': '10px'}),], icono='task_alt'),
                crear_acordeon_item("Fecha de Inicio", "content-fecha", [dcc.DatePickerSingle(id='fecha-inicio-riego', date=fecha_guardada_inicial, style={'width': '100%'})], icono='calendar_month'),
                crear_acordeon_item("Límites de Nutrientes", "content-limites", [dash_table.DataTable(id='tabla-limites-nutrientes', columns=[{"name": i, "id": i} for i in df_limites_inicial.columns], data=df_limites_inicial.to_dict('records'), editable=True)], icono='scale'),
                crear_acordeon_item("Requerimientos Anuales", "content-req", [dash_table.DataTable(id='tabla-req', columns=[{"name": i, "id": i} for i in df_req_inicial.columns], data=df_req_inicial.to_dict('records'), editable=True, row_deletable=True)], icono='grass'),
                crear_acordeon_item("Fertilizantes", "content-fert", [dash_table.DataTable(id='tabla-fert', columns=[{"name": i, "id": i} for i in df_fert_inicial.columns], data=df_fert_inicial.to_dict('records'), editable=True, row_deletable=True)], icono='science'),
                crear_acordeon_item("Distribución (2011-17)", "content-dist1", [dash_table.DataTable(id='tabla-dist1', columns=[{"name": i, "id": i} for i in df_dist1_inicial.columns], data=df_dist1_inicial.to_dict('records'), editable=True)], icono='percent'),
                crear_acordeon_item("Distribución (2018-19)", "content-dist2", [dash_table.DataTable(id='tabla-dist2', columns=[{"name": i, "id": i} for i in df_dist2_inicial.columns], data=df_dist2_inicial.to_dict('records'), editable=True)], icono='percent'),
                crear_acordeon_item("Superficies por Válvula", "content-valvulas", [dash_table.DataTable(id='tabla-valvulas', columns=[{"name": i, "id": i} for i in df_valv_inicial.columns], data=df_valv_inicial.to_dict('records'), editable=True)], icono='valve'),
            ])
        ])
    ])

opciones_dropdown_anio = [{'label': 'Todos los Años', 'value': 'todos'}] + \
    [{'label': str(anio), 'value': int(anio)} for anio in sorted(df_req_inicial['Anio'].unique())]
opciones_dropdown_sector = [{'label': 'Todos los Sectores', 'value': 'todos'}] + \
    [{'label': sec, 'value': sec} for sec in df_req_inicial['Sector'].unique()]

def layout_planificacion():
    return html.Div([
        html.Div(className='page-header', children=[html.H1("Planes de Fertilización")]),
        html.Div([html.Button("Generar Plan Mensual", id="btn-generar-mensual", className="Button Button-secondary"), html.Button("Generar Plan Semanal", id="btn-generar-semanal", className="Button Button-secondary")], style={'marginBottom': '20px', 'display': 'flex', 'gap': '10px'}),
        html.Div([html.Div([html.Label("Filtrar por Año:"), dcc.Dropdown(id='dropdown-filtro-anio', options=opciones_dropdown_anio, value='todos', clearable=False, style={'width': '200px'})]),
            html.Div([html.Button([html.I(className="material-symbols-outlined", children="download"), " Plan Mensual"], id="btn-download-mensual", className="Button Button-secondary"), html.Button([html.I(className="material-symbols-outlined", children="download"), " Plan Semanal"], id="btn-download-semanal", className="Button Button-secondary", style={'marginLeft': '10px'})])
        ], style={'marginBottom': '20px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'}),
        html.H4("Plan Mensual"),
        dcc.Loading(type="circle", children=[html.Div(id='plan-mensual-container')]),
        html.H4("Plan Semanal"),
        dcc.Loading(type="circle", children=[html.Div(id='plan-semanal-container')])
    ])

columnas_seguimiento_inicial = [
    {'name': 'Sector', 'id': 'Sector'}, {'name': 'Año Plantación', 'id': 'Año Plantación'},
    {'name': 'Mes Plan', 'id': 'Mes Plan'}, {'name': 'Producto', 'id': 'Producto'},
    {'name': 'Válvula', 'id': 'Válvula'}, {'name': 'Fecha Estimada', 'id': 'Fecha Estimada'},
    {'name': 'Litros Planeados', 'id': 'Litros Planeados', 'type': 'numeric', 'format': {'specifier': '.2f'}},
    {'name': 'Litros Reales Aplicados', 'id': 'Litros Reales Aplicados', 'editable': True, 'type': 'numeric'},
    {'name': 'Fecha Aplicación Real', 'id': 'Fecha Aplicación Real', 'editable': True},
    {'name': 'Observaciones', 'id': 'Observaciones', 'editable': True, 'presentation': 'input'},
]

def layout_seguimiento():
    return html.Div([
        html.Div(className='page-header', children=[html.H1("Seguimiento y Órdenes de Trabajo")]),
        html.Button("Cargar/Refrescar Plan", id="btn-cargar-seguimiento", className="Button Button-secondary"),
        html.H4("Órden de Trabajo"),
        html.Div(style={'display': 'flex', 'alignItems': 'flex-end', 'gap': '15px', 'marginBottom': '20px'}, children=[
            html.Div([html.Label("Fecha de Riego"), dcc.DatePickerSingle(id='filtro-fecha-orden', style={'width': '150px'})]),
            html.Div([html.Label("Sector"), dcc.Dropdown(id='filtro-sector-orden', options=opciones_dropdown_sector, placeholder="Todos", style={'width': '200px'})]),
            html.Div([html.Label("Año Plantación"), dcc.Dropdown(id='filtro-anio-orden', options=opciones_dropdown_anio, placeholder="Todos", style={'width': '150px'})]),
            html.Button([html.I(className="material-symbols-outlined", children="print"), "Generar Orden (PDF)"], id="btn-generar-orden-pdf", className="Button Button-secondary"),
        ]),
        html.H4("Aplicaciones Reales (Editable)"),
        dcc.Loading(type="circle", children=[dash_table.DataTable(id='tabla-aplicaciones-reales', data=[], columns=columnas_seguimiento_inicial, row_deletable=False, page_size=15, style_table={'overflowX': 'auto'})]),
        html.Br(),
        html.Button("Guardar Datos y Auto-Ajustar Plan", id="btn-guardar-reales", className="Button Button-primary"),
        html.Div(id='notificacion-seguimiento', style={'marginTop': '20px'}),
    ])

app.layout = html.Div(className='app-container', children=[
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='store-plan-mensual'), dcc.Store(id='store-plan-semanal'),
    dcc.Download(id="download-excel-mensual"), dcc.Download(id="download-excel-semanal"),
    dcc.Download(id="download-orden-pdf"),
    nav_sidebar,
    html.Div(className='main-content-wrapper', children=[
        html.Div(className='logo-header', children=[
            html.Img(src='/assets/Logo Fortin Castre.jpg', style={'height': '60px', 'marginRight': '20px'}),
            html.Img(src='/assets/Logo Rivera Grande.jpg', style={'height': '60px', 'marginLeft': '20px'})
        ]),
        html.Div(className='main-content', id='page-content', children=layout_planificacion()),
    ]),
    crear_modal_configuracion()
])

# --- Callbacks ---
@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/seguimiento': return layout_seguimiento()
    else: return layout_planificacion()

@app.callback(Output('modal-backdrop', 'style'), [Input('btn-abrir-config', 'n_clicks'), Input('btn-cerrar-config', 'n_clicks')], prevent_initial_call=True)
def toggle_config_modal(n_open, n_close):
    triggered_id = dash.callback_context.triggered_id
    if triggered_id == 'btn-abrir-config': return {'display': 'flex'}
    if triggered_id == 'btn-cerrar-config': return {'display': 'none'}
    return dash.no_update

@app.callback([Output({'type': 'accordion-collapse', 'index': MATCH}, 'className'), Output({'type': 'accordion-toggle', 'index': MATCH}, 'className')], Input({'type': 'accordion-toggle', 'index': MATCH}, 'n_clicks'), [State({'type': 'accordion-collapse', 'index': MATCH}, 'className'), State({'type': 'accordion-toggle', 'index': MATCH}, 'className')], prevent_initial_call=True)
def toggle_accordion(n, collapse_class, button_class):
    return ('accordion-content', 'accordion-button') if 'open' in collapse_class else ('accordion-content open', 'accordion-button open')

@app.callback(Output('notificacion-parametros', 'children'), [Input('btn-guardar-parametros', 'n_clicks'), Input('btn-restaurar-parametros', 'n_clicks')], [State('tabla-req', 'data'), State('tabla-fert', 'data'), State('tabla-limites-nutrientes', 'data'), State('tabla-dist1', 'data'), State('tabla-dist2', 'data'), State('tabla-valvulas', 'data'), State('fecha-inicio-riego', 'date')], prevent_initial_call=True)
def guardar_o_restaurar_parametros(n_g, n_r, req, fert, limites, d1, d2, valv, fecha):
    ctx = dash.callback_context;
    if not ctx.triggered: return ""
    btn_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if btn_id == 'btn-guardar-parametros':
        pd.DataFrame(req).to_csv(REQ_FILE, index=False); pd.DataFrame(fert).to_csv(FERT_FILE, index=False); pd.DataFrame(limites).to_csv(LIMITES_FILE, index=False); pd.DataFrame(d1).to_csv(DIST1_FILE, index=False); pd.DataFrame(d2).to_csv(DIST2_FILE, index=False); pd.DataFrame(valv).to_csv(VALV_FILE, index=False)
        with open(FECHA_FILE, 'w') as f: f.write(fecha)
        return html.P("¡Configuración guardada!", style={'color': '#1E8E3E', 'fontWeight': 'bold'})
    elif btn_id == 'btn-restaurar-parametros':
        for f in [REQ_FILE, FERT_FILE, LIMITES_FILE, DIST1_FILE, DIST2_FILE, VALV_FILE, FECHA_FILE, PLAN_SEMANAL_FILE, APLIC_REALES_FILE]:
            if os.path.exists(f): os.remove(f)
        return html.P("Valores restaurados. Refresca la página.", style={'color': 'blue', 'fontWeight': 'bold'})
    return ""

def limpiar_y_preparar_tabla(df):
    if df.empty or ("Error" in df.columns) or ("Mensaje" in df.columns):
        if "Error" in df.columns: return df.to_dict('records'), [{"name": i, "id": i} for i in df.columns]
        if "Mensaje" in df.columns: return df.to_dict('records'), [{"name": i, "id": i} for i in df.columns]
        return [], []
    for col in ['Litros Planeados', 'Litros Reales Aplicados']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    numeric_cols = df.select_dtypes(include=np.number).columns; df[numeric_cols] = df[numeric_cols].round(2)
    cols = [{"name": i, "id": i} for i in df.columns]; data = df.to_dict('records')
    return data, cols

@app.callback(Output('store-plan-mensual', 'data'), Input('btn-generar-mensual', 'n_clicks'), prevent_initial_call=True)
def generar_y_almacenar_plan_mensual(n_clicks):
    df_plan = generar_plan_mensual_economico(); return df_plan.to_dict('records')

@app.callback(Output('store-plan-semanal', 'data'), Input('btn-generar-semanal', 'n_clicks'), [State('store-plan-mensual', 'data'), State('tabla-limites-nutrientes', 'data'), State('fecha-inicio-riego', 'date')], prevent_initial_call=True)
def generar_y_almacenar_plan_semanal(n_clicks, plan_mensual_data, limites_data, fecha_guardada):
    if not plan_mensual_data: return None
    df_mensual = pd.DataFrame(plan_mensual_data); df_valv = cargar_o_crear(VALV_FILE, definir_valvulas); df_limites = pd.DataFrame(limites_data)
    df_plan = generar_plan_semanal(df_mensual, df_valv, df_limites, fecha_guardada)
    if not df_plan.empty and 'Fecha Estimada' in df_plan.columns:
        df_plan['Fecha Estimada'] = pd.to_datetime(df_plan['Fecha Estimada'])
        df_plan.sort_values(by=['Fecha Estimada', 'Válvula'], inplace=True)
        df_plan['Fecha Estimada'] = df_plan['Fecha Estimada'].dt.strftime('%Y-%m-%d')
        pd.DataFrame(df_plan).to_csv(PLAN_SEMANAL_FILE, index=False)
        return df_plan.to_dict('records')
    return None

@app.callback(Output('plan-mensual-container', 'children'), [Input('store-plan-mensual', 'data'), Input('dropdown-filtro-anio', 'value')])
def actualizar_vista_plan_mensual(plan_data, anio_seleccionado):
    if not plan_data: return []
    df = pd.DataFrame(plan_data).copy()
    if anio_seleccionado != 'todos': df = df[df['Año Plantación'] == int(anio_seleccionado)]
    data, cols = limpiar_y_preparar_tabla(df); return dash_table.DataTable(id='tabla-plan-mensual', data=data, columns=cols, page_size=10, style_table={'overflowX': 'auto'})

@app.callback(Output('plan-semanal-container', 'children'), [Input('store-plan-semanal', 'data'), Input('dropdown-filtro-anio', 'value')])
def actualizar_vista_plan_semanal(plan_data, anio_seleccionado):
    if not plan_data: return []
    df = pd.DataFrame(plan_data).copy()
    if anio_seleccionado != 'todos': df = df[df['Año Plantación'] == int(anio_seleccionado)]
    data, cols = limpiar_y_preparar_tabla(df); return dash_table.DataTable(id='tabla-plan-semanal', data=data, columns=cols, page_size=10, style_table={'overflowX': 'auto'})

@app.callback(Output("download-excel-mensual", "data"), Input("btn-download-mensual", "n_clicks"), [State('store-plan-mensual', 'data'), State('dropdown-filtro-anio', 'value')], prevent_initial_call=True)
def descargar_plan_mensual(n_clicks, data, anio_seleccionado):
    if not n_clicks or not data or dash.callback_context.triggered_id != 'btn-download-mensual': raise dash.exceptions.PreventUpdate
    df = pd.DataFrame(data).copy()
    if anio_seleccionado != 'todos': df = df[df['Año Plantación'] == int(anio_seleccionado)]
    nombre_archivo = f"plan_mensual_{anio_seleccionado}.xlsx" if anio_seleccionado != 'todos' else "plan_mensual_completo.xlsx"
    return dcc.send_data_frame(df.to_excel, nombre_archivo, sheet_name="Plan Mensual", index=False)

@app.callback(Output("download-excel-semanal", "data"), Input("btn-download-semanal", "n_clicks"), [State('store-plan-semanal', 'data'), State('dropdown-filtro-anio', 'value')], prevent_initial_call=True)
def descargar_plan_semanal(n_clicks, data, anio_seleccionado):
    if not n_clicks or not data or dash.callback_context.triggered_id != 'btn-download-semanal': raise dash.exceptions.PreventUpdate
    df = pd.DataFrame(data).copy()
    if anio_seleccionado != 'todos': df = df[df['Año Plantación'] == int(anio_seleccionado)]
    nombre_archivo = f"plan_semanal_{anio_seleccionado}.xlsx" if anio_seleccionado != 'todos' else "plan_semanal_completo.xlsx"
    return dcc.send_data_frame(df.to_excel, nombre_archivo, sheet_name="Plan Semanal", index=False)

@app.callback(Output('tabla-aplicaciones-reales', 'data'), Input('btn-cargar-seguimiento', 'n_clicks'))
def cargar_seguimiento(n_clicks):
    if n_clicks is None: raise dash.exceptions.PreventUpdate
    if not os.path.exists(APLIC_REALES_FILE) or os.path.getsize(APLIC_REALES_FILE) == 0:
        df_plan_sem = cargar_o_crear(PLAN_SEMANAL_FILE, lambda: pd.DataFrame())
        if df_plan_sem.empty: return []
        df_plan_sem['Litros Reales Aplicados'] = ''
        df_plan_sem['Fecha Aplicación Real'] = ''
        df_plan_sem['Observaciones'] = ''
        df_plan_sem.to_csv(APLIC_REALES_FILE, index=False)
        data, _ = limpiar_y_preparar_tabla(df_plan_sem)
        return data
    else:
        df_reales = pd.read_csv(APLIC_REALES_FILE)
        if not df_reales.empty and 'Fecha Estimada' in df_reales.columns:
            df_reales['Fecha Estimada'] = pd.to_datetime(df_reales['Fecha Estimada'])
            df_reales.sort_values(by=['Fecha Estimada', 'Válvula'], inplace=True)
            df_reales['Fecha Estimada'] = df_reales['Fecha Estimada'].dt.strftime('%Y-%m-%d')
        data, _ = limpiar_y_preparar_tabla(df_reales)
        return data

@app.callback(Output('notificacion-seguimiento', 'children'), Input('btn-guardar-reales', 'n_clicks'), State('tabla-aplicaciones-reales', 'data'), prevent_initial_call=True)
def guardar_datos_reales(n_clicks, data):
    if not data: return html.P("No hay datos para guardar.", style={'color': 'orange'})
    df = pd.DataFrame(data).copy(); df['Fecha Estimada'] = pd.to_datetime(df['Fecha Estimada'])
    df_modificado = df.copy()
    for index, row in df.iterrows():
        try:
            litros_reales = pd.to_numeric(row['Litros Reales Aplicados'], errors='coerce')
            if pd.notna(litros_reales):
                litros_planeados = pd.to_numeric(row['Litros Planeados'], errors='coerce')
                if pd.isna(litros_planeados): litros_planeados = 0
                diferencia = litros_reales - litros_planeados
                if diferencia != 0:
                    df_futuro = df_modificado[(df_modificado['Fecha Estimada'] > row['Fecha Estimada']) & (df_modificado['Válvula'] == row['Válvula']) & (df_modificado['Sector'] == row['Sector'])].sort_values(by='Fecha Estimada')
                    if not df_futuro.empty:
                        idx_siguiente_riego = df_futuro.index[0]
                        valor_actual_planeado = df_modificado.loc[idx_siguiente_riego, 'Litros Planeados']
                        valor_base_numerico = pd.to_numeric(valor_actual_planeado, errors='coerce')
                        if pd.isna(valor_base_numerico): valor_base_numerico = 0
                        df_modificado.loc[idx_siguiente_riego, 'Litros Planeados'] = valor_base_numerico + diferencia
        except (ValueError, TypeError): continue
    df_modificado['Fecha Estimada'] = df_modificado['Fecha Estimada'].dt.strftime('%Y-%m-%d')
    df_modificado.to_csv(APLIC_REALES_FILE, index=False)
    return html.P("¡Datos guardados y plan auto-ajustado con éxito!", style={'color': '#1E8E3E', 'fontWeight': 'bold'})

@app.callback(Output("download-orden-pdf", "data"), Input("btn-generar-orden-pdf", "n_clicks"), [State('tabla-aplicaciones-reales', 'data'), State('filtro-fecha-orden', 'date'), State('filtro-sector-orden', 'value'), State('filtro-anio-orden', 'value')], prevent_initial_call=True)
def generar_orden_trabajo_pdf(n_clicks, data, fecha, sector, anio):
    if not n_clicks or not data: raise dash.exceptions.PreventUpdate
    df = pd.DataFrame(data).copy()
    df['Fecha Estimada'] = pd.to_datetime(df['Fecha Estimada'])
    df['Año Plantación'] = df['Año Plantación'].astype(int)
    df.sort_values(by=['Fecha Estimada', 'Válvula'], inplace=True)
    if fecha: df = df[df['Fecha Estimada'].dt.date == pd.to_datetime(fecha).date()]
    if sector and sector != 'todos': df = df[df['Sector'] == sector]
    if anio and anio != 'todos': df = df[df['Año Plantación'] == int(anio)]
    if df.empty: return None

    class PDF(FPDF):
        def header(self):
            self.image('assets/Logo Fortin Castre.jpg', 10, 8, 33)
            self.set_font('helvetica', 'B', 15)
            self.cell(0, 10, 'Orden de Trabajo de Fertilización', 0, 1, 'C')
            self.image('assets/Logo Rivera Grande.jpg', 170, 8, 33)
            self.ln(10)
        def footer(self):
            self.set_y(-15); self.set_font('helvetica', 'I', 8); self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font('helvetica', '', 10)
    pdf.cell(0, 10, f"Fecha de Emisión: {datetime.date.today().strftime('%d/%m/%Y')}", 0, 1)
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(45, 7, 'Sector', 1, 0, 'C'); pdf.cell(20, 7, 'Válvula', 1, 0, 'C'); pdf.cell(45, 7, 'Producto', 1, 0, 'C'); pdf.cell(30, 7, 'Litros a Aplicar', 1, 0, 'C'); pdf.cell(40, 7, 'Litros Reales', 1, 1, 'C')
    pdf.set_font('helvetica', '', 10)
    for _, row in df.iterrows():
        pdf.cell(45, 10, str(row['Sector']), 1, 0); pdf.cell(20, 10, str(row['Válvula']), 1, 0); pdf.cell(45, 10, str(row['Producto']), 1, 0)
        pdf.cell(30, 10, f"{pd.to_numeric(row['Litros Planeados'], errors='coerce'):.2f}", 1, 0, 'R'); pdf.cell(40, 10, '', 1, 1)
    pdf.ln(15); pdf.cell(0, 10, 'Observaciones:', 0, 1)
    pdf.multi_cell(w=0, h=10, text='', border=1, align='L')
    pdf.ln(25)
    pdf.cell(90, 10, '_________________________', 0, 0, 'C'); pdf.cell(90, 10, '_________________________', 0, 1, 'C')
    pdf.cell(90, 5, 'Firma Responsable Finca', 0, 0, 'C'); pdf.cell(90, 5, 'Firma Operario', 0, 1, 'C')
    
    return dcc.send_bytes(lambda f: f.write(pdf.output(encoding='latin-1')), f"orden_trabajo_{datetime.date.today()}.pdf")

if __name__ == '__main__':
    app.run(debug=True)
