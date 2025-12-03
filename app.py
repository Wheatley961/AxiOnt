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

    # Поиск сущностей по типам
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


def draw_graph(g, filter_type=None, filter_value=None, graph_mode="all"):
    classes, obj_props, dt_props, individuals = get_entities(g)

    net = Network(height="700px", width="100%", directed=True)
    net.barnes_hut()

    for s, p, o in g:
        # Фильтрация по типу графа
        if graph_mode == "object" and p not in obj_props:
            continue
        if graph_mode == "datatype" and p not in dt_props:
            continue
        if graph_mode == "taxonomy" and p != OWL.subClassOf:
            continue

        # Фильтрация по выбранному фильтру
        if filter_type == "class" and str(s) != filter_value and str(o) != filter_value:
            continue
        if filter_type == "property" and str(p) != filter_value:
            continue
        if filter_type == "individual" and str(s) != filter_value and str(o) != filter_value:
            continue

        net.add_node(str(s), label=str(s), color=node_color(s, classes, obj_props, dt_props, individuals))
        net.add_node(str(o), label=str(o), color=node_color(o, classes, obj_props, dt_props, individuals))
        net.add_edge(str(s), str(o), label=str(p))

    # Запись в временный файл
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    # Вместо net.show() — используем net.write_html() с notebook=False
    net.write_html(tmp.name, notebook=False)
    return tmp.name


def export_graph_image(g, fmt="png", graph_mode="all"):
    G = nx.DiGraph()
    classes, obj_props, dt_props, individuals = get_entities(g)

    for s, p, o in g:
        if graph_mode == "object" and p not in obj_props:
            continue
        if graph_mode == "datatype" and p not in dt_props:
            continue
        if graph_mode == "taxonomy" and p != OWL.subClassOf:
            continue
        G.add_edge(str(s), str(o), label=str(p))

    plt.figure(figsize=(12, 12))
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    nx.draw(G, pos, with_labels=True, font_size=6, node_color="skyblue", edge_color="gray", arrowsize=10)
    img_path = f"graph_export.{fmt}"
    plt.savefig(img_path, format=fmt, dpi=300)
    plt.close()
    return img_path


def main():
    st.set_page_config(layout="wide")
    st.title("Онтология государственной ценностной политики (Указ № 809)")

    with st.expander("Описание проекта и назначение онтологии", expanded=True):
        st.markdown("""
        Цель создания онтологии

        Онтология предназначена для:

        - формального представления положений государственной ценностной политики;
        - семантической интеграции данных органов власти, научных центров и экспертных систем;
        - поддержки анализа угроз традиционным ценностям;
        - моделирования взаимосвязей между ценностями, целями, задачами, инструментами и участниками реализации политики;
        - создания основы для автоматизированного мониторинга, прогнозирования и принятия управленческих решений.

        Концептуальная основа

        Онтология построена на базе:

        - официально закреплённого перечня традиционных российских духовно-нравственных ценностей;
        - положений о вызовах и угрозах ценностному суверенитету;
        - принципов системной государственной политики в гуманитарной сфере;
        - сценарного подхода к оценке последствий воздействия угроз;
        - программно-целевого подхода к управлению.

        Формально онтология реализована в логике OWL 2, с поддержкой:

        - таксономий (классы и подклассы),
        - реляционных связей (объектные свойства),
        - атрибутивных характеристик (datatype properties),
        - индивидуальных сущностей (экземпляров).

        Структура онтологии (основные классы)

        (Далее - как в твоём тексте...)

        """)

    g = load_graph()

    st.sidebar.title("Параметры визуализации")

    graph_mode = st.sidebar.selectbox(
        "Тип графа",
        ["all", "object", "datatype", "taxonomy"],
        format_func=lambda x: {
            "all": "Все связи",
            "object": "Только объектные свойства",
            "datatype": "Только datatype-свойства",
            "taxonomy": "Классовая таксономия",
        }[x]
    )

    classes, obj_props, dt_props, individuals = get_entities(g)

    mode = st.sidebar.selectbox(
        "Фильтр по типу сущности",
        ["Нет", "Класс", "Свойство", "Индивид"]
    )

    value = None
    if mode != "Нет":
        options = []
        if mode == "Класс":
            options = sorted(str(c) for c in classes)
        elif mode == "Свойство":
            options = sorted(str(p) for p in obj_props.union(dt_props))
        elif mode == "Индивид":
            options = sorted(str(i) for i in individuals)
        value = st.sidebar.selectbox("Выберите значение", options)

    if st.sidebar.button("Применить фильтр"):
        html_file = draw_graph(
            g,
            filter_type=mode.lower() if mode != "Нет" else None,
            filter_value=value,
            graph_mode=graph_mode
        )
        html_content = open(html_file, "r", encoding="utf-8").read()
        st.components.v1.html(html_content, height=750)
        os.unlink(html_file)  # удаляем временный файл

    else:
        st.subheader("Полный граф онтологии")
        html_file = draw_graph(g, graph_mode=graph_mode)
        html_content = open(html_file, "r", encoding="utf-8").read()
        st.components.v1.html(html_content, height=750)
        os.unlink(html_file)

    st.subheader("Экспорт графа в изображение")

    export_fmt = st.selectbox("Выберите формат изображения", ["png", "svg"])

    if st.button("Экспортировать граф"):
        img_path = export_graph_image(g, fmt=export_fmt, graph_mode=graph_mode)
        with open(img_path, "rb") as f:
            st.download_button(
                label=f"Скачать граф в формате {export_fmt.upper()}",
                data=f,
                file_name=img_path,
                mime=f"image/" + export_fmt
            )
        os.remove(img_path)


if __name__ == "__main__":
    main()
