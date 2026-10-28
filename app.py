import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

st.set_page_config(page_title="Laboratorio Sink Tree", layout="wide")
st.title("Laboratorio: Optimalidad y Sink Tree")

# -----------------------------
# 1. Datos iniciales de la red
# -----------------------------

@st.cache_data
def datos_iniciales():
    enlaces = [
        {"origen": "H", "destino": "D", "retardo": 8,  "banda": 100, "disponible": True},
        {"origen": "D", "destino": "A", "retardo": 9,  "banda": 100, "disponible": True},
        {"origen": "A", "destino": "B", "retardo": 7,  "banda": 100, "disponible": True},

        {"origen": "H", "destino": "E", "retardo": 5,  "banda": 50,  "disponible": True},
        {"origen": "E", "destino": "J", "retardo": 10, "banda": 50,  "disponible": True},
        {"origen": "J", "destino": "C", "retardo": 8,  "banda": 100, "disponible": True},
        {"origen": "C", "destino": "B", "retardo": 6,  "banda": 100, "disponible": True},

        {"origen": "H", "destino": "O", "retardo": 7,  "banda": 50,  "disponible": True},
        {"origen": "O", "destino": "N", "retardo": 9,  "banda": 50,  "disponible": True},
        {"origen": "N", "destino": "J", "retardo": 9,  "banda": 50,  "disponible": True},
    ]
    return pd.DataFrame(enlaces)

if "df" not in st.session_state:
    st.session_state.df = datos_iniciales()

df = st.session_state.df.copy()

ORIGEN = "H"
DESTINO = "B"

# -----------------------------
# 2. Tabla editable
# -----------------------------

st.header("1. Parámetros de los enlaces")

df_editado = st.data_editor(
    df,
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "retardo": st.column_config.NumberColumn("Retardo_ms", min_value=0.1),
        "banda": st.column_config.NumberColumn("Banda_Mbps", min_value=0.1),
        "disponible": st.column_config.CheckboxColumn("Disponible"),
    },
    key="tabla_enlaces"
)

# -----------------------------
# 3. Función objetivo
# -----------------------------

st.sidebar.header("Función objetivo")

modo = st.sidebar.radio(
    "Selecciona el criterio:",
    ["Johal: mínimo de saltos", "Mínimo retardo", "Multicriterio"]
)

if modo == "Multicriterio":
    alfa = st.sidebar.slider("Alpha - saltos", 0.0, 1.0, 0.5)
    beta = st.sidebar.slider("Beta - retardo", 0.0, 1.0, 0.35)
    gamma = st.sidebar.slider("Gamma - baja capacidad", 0.0, 1.0, 0.15)

    total = alfa + beta + gamma
    if total == 0:
        st.sidebar.warning("La suma de los pesos debe ser mayor que cero.")
        st.stop()

    alfa /= total
    beta /= total
    gamma /= total

# -----------------------------
# 4. Crear el grafo
# -----------------------------

def crear_grafo(dataframe):
    G = nx.Graph()

    for _, fila in dataframe.iterrows():
        u = fila["origen"]
        v = fila["destino"]

        if not fila["disponible"]:
            continue

        G.add_edge(
            u, v,
            retardo=float(fila["retardo"]),
            banda=float(fila["banda"])
        )

    return G

G = crear_grafo(df_editado)

# -----------------------------
# 5. Cálculo de costos
# -----------------------------

def costo_salto(G, u, v, modo):
    datos = G[u][v]

    if modo == "Johal: mínimo de saltos":
        return 1

    if modo == "Mínimo retardo":
        return datos["retardo"]

    # Multicriterio
    d_ref = max(d["retardo"] for _, _, d in G.edges(data=True))
    b_ref = max(d["banda"] for _, _, d in G.edges(data=True))

    return (
        alfa
        + beta * (datos["retardo"] / d_ref)
        + gamma * (b_ref / datos["banda"])
    )

def calcular_mejor_ruta(G, origen, destino, modo):
    if origen not in G or destino not in G:
        return None, None

    try:
        ruta = nx.dijkstra_path(
            G,
            source=origen,
            target=destino,
            weight=lambda u, v, d: costo_salto(G, u, v, modo)
        )
        costo = nx.dijkstra_path_length(
            G,
            source=origen,
            target=destino,
            weight=lambda u, v, d: costo_salto(G, u, v, modo)
        )
        return ruta, costo
    except nx.NetworkXNoPath:
        return None, None

ruta_optima, costo_optimo = calcular_mejor_ruta(G, ORIGEN, DESTINO, modo)

# -----------------------------
# 6. Rutas estáticas del artículo
# -----------------------------

rutas_articulo = {
    "PSRC": ["H", "D", "A", "B"],
    "SSRC": ["H", "E", "J", "C", "B"],
    "TSRC": ["H", "O", "N", "J", "C", "B"]
}

def metricas_ruta(G, ruta):
    if ruta is None:
        return None

    saltos = len(ruta) - 1
    retardo = 0
    banda = []

    for u, v in zip(ruta[:-1], ruta[1:]):
        if not G.has_edge(u, v):
            return None

        datos = G[u][v]
        retardo += datos["retardo"]
        banda.append(datos["banda"])

    return {
        "Ruta": " - ".join(ruta),
        "Saltos": saltos,
        "Retardo_ms": retardo,
        "Banda_minima_Mbps": min(banda) if banda else None,
        "Disponible": True
    }

st.header("2. Comparación de rutas")

resultados = []

for nombre, ruta in rutas_articulo.items():
    m = metricas_ruta(G, ruta)

    if m is None:
        resultados.append({
            "Ruta": nombre,
            "Saltos": None,
            "Retardo_ms": None,
            "Banda_minima_Mbps": None,
            "Disponible": False
        })
    else:
        m["Ruta"] = f"{nombre}: {m['Ruta']}"
        resultados.append(m)

if ruta_optima:
    m_optima = metricas_ruta(G, ruta_optima)
    m_optima["Ruta"] = f"Óptima: {' - '.join(ruta_optima)}"
    resultados.append(m_optima)

df_resultados = pd.DataFrame(resultados)
st.dataframe(df_resultados, use_container_width=True)

st.subheader("Ruta óptima calculada")

if ruta_optima:
    st.success(f"Mejor ruta: {' → '.join(ruta_optima)}")
    st.write(f"Costo según el criterio seleccionado: **{costo_optimo:.4f}**")
else:
    st.error("No existe una ruta disponible desde H hasta B.")

# -----------------------------
# 7. Sink Tree hacia B
# -----------------------------

st.header("3. Sink Tree hacia B")

def construir_sink_tree(G, destino, modo):
    # Dijkstra desde B hacia todos los nodos
    dist, prev = nx.single_source_dijkstra(
        G,
        source=destino,
        weight=lambda u, v, d: costo_salto(G, u, v, modo)
    )

    siguiente_salto = {}

    for nodo in G.nodes:
        if nodo == destino:
            siguiente_salto[nodo] = "Destino"
            continue

        if nodo in prev and prev[nodo]:
            siguiente_salto[nodo] = prev[nodo]
        else:
            siguiente_salto[nodo] = "No alcanzable"

    return siguiente_salto

sink_tree = construir_sink_tree(G, DESTINO, modo)

df_sink = pd.DataFrame(
    [{"Router": nodo, "Siguiente salto hacia B": salto}
     for nodo, salto in sink_tree.items()]
).sort_values("Router")

st.dataframe(df_sink, use_container_width=True)

# -----------------------------
# 8. Grafo visual
# -----------------------------

st.header("4. Visualización de la red")

pos = nx.spring_layout(G, seed=42)

edge_x = []
edge_y = []

for u, v in G.edges:
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    edge_x += [x0, x1, None]
    edge_y += [y0, y1, None]

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=edge_x,
    y=edge_y,
    mode="lines",
    line=dict(width=2, color="gray"),
    hoverinfo="none"
))

node_x = []
node_y = []
node_text = []

for nodo in G.nodes:
    x, y = pos[nodo]
    node_x.append(x)
    node_y.append(y)
    node_text.append(nodo)

fig.add_trace(go.Scatter(
    x=node_x,
    y=node_y,
    mode="markers+text",
    text=node_text,
    textposition="top center",
    marker=dict(size=25, color="lightblue"),
    hoverinfo="text"
))

fig.update_layout(
    showlegend=False,
    height=550,
    margin=dict(l=20, r=20, t=20, b=20)
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 9. Exportar CSV
# -----------------------------

st.header("5. Exportar resultados")

csv = df_resultados.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Descargar resultados en CSV",
    data=csv,
    file_name="resultados_laboratorio.csv",
    mime="text/csv"
)