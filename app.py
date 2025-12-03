import streamlit as st
from rdflib import Graph
from pyvis.network import Network

# Вспомогательные функции для извлечения классов, свойств, индивидов
from rdflib.namespace import OWL

def get_entities(g):
    classes = set()
    object_props = set()
    datatype_props = set()
    individuals = set()
    for s, p, o in g:
        if o == OWL.Class:
            classes.add(s)
        if o == OWL.ObjectProperty:
            object_props.add(s)
        if o == OWL.DatatypeProperty:
            datatype_props.add(s)
        if o == OWL.NamedIndividual:
            individuals.add(s)
    return classes, object_props, datatype_props, individuals

# Экспорт графа в PNG/SVG
import networkx as nx
import matplotlib.pyplot as plt

def export_graph_image(g, fmt="png"):
    G = nx.DiGraph()
    for s, p, o in g:
        G.add_edge(str(s), str(o))
    plt.figure(figsize=(12, 12))
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, font_size=6)
    img_path = f"graph_export.{fmt}"
    plt.savefig(img_path, format=fmt, dpi=300)
    plt.close()
    return img_path
import tempfile

ONTOLOGY_URL = "https://github.com/Wheatley961/AxiOnt/blob/main/axiology_ontology_ru.ttl?raw=1"

def load_graph():
    g = Graph()
    g.parse(ONTOLOGY_URL, format="turtle")
    return g

def draw_graph(g, filter_type=None, filter_value=None, graph_mode="all"):
    net = Network(height="700px", width="100%", directed=True)
    classes, obj_props, dt_props, individuals = get_entities(g)

    for s, p, o in g:
        # Фильтрация по типу графа
        if graph_mode == "object" and o not in obj_props:
            continue
        if graph_mode == "datatype" and o not in dt_props:
            continue
        if graph_mode == "taxonomy" and o != OWL.Class:
            continue

        # Цветовая дифференциация
        def node_color(node):
            if node in classes:
                return "#1f77b4"  # синий — классы
            if node in obj_props or node in dt_props:
                return "#ff7f0e"  # оранжевый — свойства
            if node in individuals:
                return "#2ca02c"  # зелёный — индивиды
            return "#7f7f7f"      # серый — неизвестное

        if filter_type == "class" and str(s) != filter_value and str(o) != filter_value:
            continue

        net.add_node(str(s), label=str(s), color=node_color(s))
        net.add_node(str(o), label=str(o), color=node_color(o))
        net.add_edge(str(s), str(o), label=str(p))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    net.show(tmp.name)
    return tmp.name(g, filter_type=None, filter_value=None):
    net = Network(height="700px", width="100%", directed=True)
    for s, p, o in g:
        if filter_type == "class" and str(s) != filter_value and str(o) != filter_value:
            continue
        net.add_node(str(s), label=str(s))
        net.add_node(str(o), label=str(o))
        net.add_edge(str(s), str(o), label=str(p))
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    net.show(tmp.name)
    return tmp.name

st.title("Аксиологическая онтология государственной ценностной политики РФ")

with st.expander("Описание проекта"):
    st.write("""
Онтология предназначена для: формального представления положений государственной ценностной политики; ... (вставьте текст)
""")

g = load_graph()
st.subheader("Полный граф онтологии")
html_file = draw_graph(g)
st.components.v1.html(open(html_file).read(), height=750)

st.subheader("Фильтрация визуализации")

# Новый переключатель типа графа
graph_mode = st.selectbox(
    "Тип графа",
    ["all", "object", "datatype", "taxonomy"],
    format_func=lambda x: {
        "all": "Все связи",
        "object": "Только объектные свойства",
        "datatype": "Только datatype-свойства",
        "taxonomy": "Классовая таксономия",
    }[x]
)

mode = st.selectbox("Тип фильтра", ["Нет", "Класс", "Свойство", "Экземпляр"])
value = st.text_input("Введите URI или локальное имя для фильтрации")
if st.button("Применить"):
    html_file_filtered = draw_graph(g, filter_type=mode.lower() if mode != "Нет" else None, filter_value=value, graph_mode=graph_mode)
    st.components.v1.html(open(html_file_filtered).read(), height=750)
("Применить") and mode != "Нет" and value:
    html_file_filtered = draw_graph(g, filter_type=mode.lower(), filter_value=value)
    st.components.v1.html(open(html_file_filtered).read(), height=750)
