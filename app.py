import streamlit as st
import requests
from rdflib import Graph, OWL
from pyvis.network import Network
import tempfile
import networkx as nx
import matplotlib.pyplot as plt
import os

ONTOLOGY_URL = "https://raw.githubusercontent.com/Wheatley961/AxiOnt/main/axiology_ontology_ru.ttl"


@st.cache_resource
def load_graph():
    g = Graph()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; StreamlitApp/1.0)"
    }
    response = requests.get(ONTOLOGY_URL, headers=headers)
    response.raise_for_status()
    turtle_data = response.text
    g.parse(data=turtle_data, format="turtle")
    return g


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


def node_color(node, classes, obj_props, dt_props, individuals):
    if node in classes:
        return "#1f77b4"  # синий - классы
    if node in obj_props or node in dt_props:
        return "#ff7f0e"  # оранжевый - свойства
    if node in individuals:
        return "#2ca02c"  # зелёный - индивиды
    return "#7f7f7f"      # серый - остальные


def draw_graph(g, filter_type=None, filter_value=None):
    classes, obj_props, dt_props, individuals = get_entities(g)

    net = Network(height="700px", width="100%", directed=True)
    net.barnes_hut()

    for s, p, o in g:
        # Фильтр
        if filter_type == "class":
            if str(s) != filter_value and str(o) != filter_value:
                continue
        elif filter_type == "property":
            if str(p) != filter_value:
                continue
        elif filter_type == "individual":
            if str(s) != filter_value and str(o) != filter_value:
                continue

        net.add_node(str(s), label=str(s), color=node_color(s, classes, obj_props, dt_props, individuals))
        net.add_node(str(o), label=str(o), color=node_color(o, classes, obj_props, dt_props, individuals))
        net.add_edge(str(s), str(o), label=str(p))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    net.write_html(tmp.name, notebook=False)
    return tmp.name


def main():
    st.set_page_config(layout="wide")
    st.title("Аксиологическая онтология государственной ценностной политики РФ (Указ № 809)")

    st.markdown("""
    Онтология создана для формального представления государственной ценностной политики и моделирования взаимосвязей между ценностями, целями, задачами, инструментами и участниками, а также для формирования основы автоматизированного мониторинга, прогнозирования и поддержки управленческих решений.

    Её концептуальная база включает официальный перечень традиционных ценностей, принципы государственной гуманитарной политики, анализ угроз ценностному суверенитету, а также сценарный и программно-целевой подходы. Формально реализована в логике OWL.
    """)

    g = load_graph()

    # Сначала показываем весь граф без фильтра
    st.subheader("Весь граф онтологии")
    html_file = draw_graph(g)
    html_content = open(html_file, "r", encoding="utf-8").read()
    st.components.v1.html(html_content, height=750)
    os.unlink(html_file)

    # Получаем сущности для выпадающих списков
    classes, obj_props, dt_props, individuals = get_entities(g)

    st.sidebar.title("Фильтр графа")
    filter_type = st.sidebar.selectbox("Выберите тип для фильтрации", ["Нет", "Класс", "Свойство", "Индивид"])

    filter_value = None
    if filter_type != "Нет":
        options = []
        if filter_type == "Класс":
            options = sorted(str(c) for c in classes)
        elif filter_type == "Свойство":
            options = sorted(str(p) for p in obj_props.union(dt_props))
        elif filter_type == "Индивид":
            options = sorted(str(i) for i in individuals)
        filter_value = st.sidebar.selectbox(f"Выберите {filter_type.lower()}", options)

    if filter_type != "Нет" and filter_value:
        st.subheader(f"Граф, отфильтрованный по {filter_type.lower()} '{filter_value}'")
        html_file = draw_graph(g, filter_type=filter_type.lower(), filter_value=filter_value)
        html_content = open(html_file, "r", encoding="utf-8").read()
        st.components.v1.html(html_content, height=750)
        os.unlink(html_file)

    st.caption("""
    Разработчики ресурса: <b>И.Д. Мамаев</b> 
    <a href="mailto:mamaev_id@voenmeh.ru" style="text-decoration: none; margin-left: 5px;">
        <span style="font-size: 1.2em; background: transparent;">📧</span>
    </a>, 
    <b>А.В. Лаптева</b> 
    <a href="mailto:lapteva_av@voenmeh.ru" style="text-decoration: none; margin-left: 5px;">
        <span style="font-size: 1.2em; background: transparent;">📧</span>
    </a>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
