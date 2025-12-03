import streamlit as st
import requests
from rdflib import Graph, OWL, RDFS, RDF, URIRef, Literal
from pyvis.network import Network
import tempfile
import os

ONTOLOGY_URL = "https://raw.githubusercontent.com/Wheatley961/AxiOnt/main/axiology_ontology_ru.ttl"

@st.cache_resource
def load_graph():
    g = Graph()
    response = requests.get(ONTOLOGY_URL)
    response.raise_for_status()
    g.parse(data=response.text, format="turtle")
    return g

def get_entities_and_labels(g):
    classes = set()
    object_props = set()
    datatype_props = set()
    individuals = set()

    labels = {}  # URIRef -> rdfs:label (str) на русском (если есть), иначе URI как str

    # Сначала считаем все labels для узлов
    for s, p, o in g.triples((None, RDFS.label, None)):
        if isinstance(o, Literal):
            # Ищем метку на русском
            if o.language == 'ru' or o.language is None:
                labels[s] = str(o)

    # Заполним множества по типам
    for s, p, o in g.triples((None, RDF.type, None)):
        if o == OWL.Class:
            classes.add(s)
        elif o == OWL.ObjectProperty:
            object_props.add(s)
        elif o == OWL.DatatypeProperty:
            datatype_props.add(s)
        elif (o == OWL.NamedIndividual) or (o not in [OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty]):
            # В онтологии иногда индивидуум не строго owl:NamedIndividual, берём всё прочее как индивидов
            individuals.add(s)

    return classes, object_props, datatype_props, individuals, labels

def node_color(node, classes, obj_props, dt_props, individuals):
    if node in classes:
        return "#1f77b4"  # синий
    if node in obj_props or node in dt_props:
        return "#ff7f0e"  # оранжевый
    if node in individuals:
        return "#2ca02c"  # зелёный
    return "#7f7f7f"

def draw_graph(g, classes_filter, props_filter, indiv_filter, classes, obj_props, dt_props, individuals, labels):
    net = Network(height="700px", width="100%", directed=True)
    net.barnes_hut()

    def label_for(node):
        return labels.get(node, str(node))

    # Добавляем ребра и узлы с фильтрами (комбинация AND)
    for s, p, o in g:
        # Проверка типов узлов для корректного цвета
        # Фильтруем по выбранным фильтрам:
        # Если задан класс — пропускаем, если ни s, ни o не в выбранных классах
        if classes_filter and not (s in classes_filter or o in classes_filter):
            continue
        # Если задано свойство — p должно быть в выбранных свойствах
        if props_filter and p not in props_filter:
            continue
        # Если задан индивид — s или o должны быть в выбранных индивидах
        if indiv_filter and not (s in indiv_filter or o in indiv_filter):
            continue

        net.add_node(str(s), label=label_for(s), color=node_color(s, classes, obj_props, dt_props, individuals))
        net.add_node(str(o), label=label_for(o), color=node_color(o, classes, obj_props, dt_props, individuals))
        net.add_edge(str(s), str(o), label=label_for(p))

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
    classes, obj_props, dt_props, individuals, labels = get_entities_and_labels(g)

    # Формируем отображаемые опции фильтров в удобочитаемом виде с обратным словарём
    def create_options(uri_set):
        options = []
        for uri in uri_set:
            lab = labels.get(uri, str(uri))
            options.append((lab, uri))
        # Сортируем по метке
        options.sort(key=lambda x: x[0].lower())
        return options

    classes_options = create_options(classes)
    props_options = create_options(obj_props.union(dt_props))
    indiv_options = create_options(individuals)

    # Мультиселекты для фильтрации с возможностью мультивыбора
    classes_selected = st.multiselect("Фильтр по классам", [lab for lab, _ in classes_options])
    props_selected = st.multiselect("Фильтр по свойствам", [lab for lab, _ in props_options])
    indiv_selected = st.multiselect("Фильтр по индивидуумам", [lab for lab, _ in indiv_options])

    # Переводим выбранные метки обратно в URI для фильтрации
    def selected_to_uri(selected_labels, options):
        label_to_uri = {lab: uri for lab, uri in options}
        return set(label_to_uri[lab] for lab in selected_labels if lab in label_to_uri)

    classes_filter = selected_to_uri(classes_selected, classes_options) if classes_selected else None
    props_filter = selected_to_uri(props_selected, props_options) if props_selected else None
    indiv_filter = selected_to_uri(indiv_selected, indiv_options) if indiv_selected else None

    html_file = draw_graph(g, classes_filter, props_filter, indiv_filter, classes, obj_props, dt_props, individuals, labels)

    html_content = open(html_file, "r", encoding="utf-8").read()
    st.components.v1.html(html_content, height=750)
    os.unlink(html_file)

    # Легенда с цветами
    st.markdown("""
    <style>
    .legend-item {
        display: flex; 
        align-items: center; 
        margin-bottom: 4px;
    }
    .legend-color {
        width: 18px; 
        height: 18px; 
        margin-right: 8px; 
        border-radius: 4px;
        display: inline-block;
    }
    </style>
    <div class="legend-item"><span class="legend-color" style="background:#1f77b4"></span> Класс (Class)</div>
    <div class="legend-item"><span class="legend-color" style="background:#ff7f0e"></span> Свойство (Property)</div>
    <div class="legend-item"><span class="legend-color" style="background:#2ca02c"></span> Индивид (Individual)</div>
    <div class="legend-item"><span class="legend-color" style="background:#7f7f7f"></span> Прочее</div>
    """, unsafe_allow_html=True)

    # Подписи разработчиков с корректной вёрсткой
    st.caption("""
    Разработчики ресурса: <b>И.Д. Мамаев</b> 
    <a href="mailto:mamaev_id@voenmeh.ru" style="text-decoration: none; margin-left: 5px;">
        <span style="font-size: 1.2em; background: transparent;">📧</span>
    </a>, 
    <b>А.В. Лаптева</b> 
    <a href="mailto:lapteva_av@voenmeh.ru" style="text-decoration: none; margin-left: 5px;">
        <span style="font-size: 1.2em; background: transparent;">📧</span>
    </a>
    """ , unsafe_allow_html=True)

if __name__ == "__main__":
    main()
