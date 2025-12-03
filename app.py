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

def get_entities_and_labels_ru(g):
    classes = set()
    object_props = set()
    datatype_props = set()
    individuals = set()

    labels = {}  # URIRef -> rdfs:label str (только с языком ru)
    uris_with_ru_label = set()

    # Собираем все rdfs:label с языком ru
    for s, p, o in g.triples((None, RDFS.label, None)):
        if isinstance(o, Literal) and o.language == 'ru':
            labels[s] = str(o)
            uris_with_ru_label.add(s)

    # Теперь фильтруем сущности по наличию русской метки
    for s, p, o in g.triples((None, RDF.type, None)):
        if s not in uris_with_ru_label:
            continue
        if o == OWL.Class:
            classes.add(s)
        elif o == OWL.ObjectProperty:
            object_props.add(s)
        elif o == OWL.DatatypeProperty:
            datatype_props.add(s)
        elif (o == OWL.NamedIndividual) or (o not in [OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty]):
            individuals.add(s)

    # Иногда в онтологиях классы или индивиды могут не иметь rdf:type, но иметь метки — добавим их по умолчанию в индивиды
    for uri in uris_with_ru_label:
        if uri not in classes and uri not in object_props and uri not in datatype_props and uri not in individuals:
            individuals.add(uri)

    return classes, object_props, datatype_props, individuals, labels, uris_with_ru_label

def node_color(node, classes, obj_props, dt_props, individuals):
    if node in classes:
        return "#1f77b4"  # синий
    if node in obj_props or node in dt_props:
        return "#ff7f0e"  # оранжевый
    if node in individuals:
        return "#2ca02c"  # зелёный
    return "#7f7f7f"

def draw_graph(g, classes_filter, props_filter, indiv_filter, classes, obj_props, dt_props, individuals, labels, ru_uris):
    net = Network(height="700px", width="100%", directed=True)
    net.barnes_hut()

    def label_for(node):
        return labels.get(node, str(node))

    # Добавляем ребра и узлы, но только если у узлов есть русская метка (ru_uris)
    for s, p, o in g:
        if not (s in ru_uris and o in ru_uris):
            continue  # Показываем только узлы с русскими метками

        # Проверяем фильтры
        if classes_filter and not (s in classes_filter or o in classes_filter):
            continue
        if props_filter and p not in props_filter:
            continue
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
    classes, obj_props, dt_props, individuals, labels, ru_uris = get_entities_and_labels_ru(g)

    def create_options(uri_set):
        options = []
        for uri in uri_set:
            lab = labels.get(uri, str(uri))
            options.append((lab, uri))
        options.sort(key=lambda x: x[0].lower())
        return options

    classes_options = create_options(classes)
    props_options = create_options(obj_props.union(dt_props))
    indiv_options = create_options(individuals)

    classes_selected = st.multiselect("Фильтр по классам", [lab for lab, _ in classes_options])
    props_selected = st.multiselect("Фильтр по свойствам", [lab for lab, _ in props_options])
    indiv_selected = st.multiselect("Фильтр по экземплярам", [lab for lab, _ in indiv_options])

    def selected_to_uri(selected_labels, options):
        label_to_uri = {lab: uri for lab, uri in options}
        return set(label_to_uri[lab] for lab in selected_labels if lab in label_to_uri)

    classes_filter = selected_to_uri(classes_selected, classes_options) if classes_selected else None
    props_filter = selected_to_uri(props_selected, props_options) if props_selected else None
    indiv_filter = selected_to_uri(indiv_selected, indiv_options) if indiv_selected else None

    html_file = draw_graph(g, classes_filter, props_filter, indiv_filter, classes, obj_props, dt_props, individuals, labels, ru_uris)

    html_content = open(html_file, "r", encoding="utf-8").read()
    st.components.v1.html(html_content, height=750)
    os.unlink(html_file)

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
    <div class="legend-item"><span class="legend-color" style="background:#1f77b4"></span> Класс</div>
    <div class="legend-item"><span class="legend-color" style="background:#2ca02c"></span> Экземпляр</div>
    <div class="legend-item"><span class="legend-color" style="background:#7f7f7f"></span> Прочее</div>
    """, unsafe_allow_html=True)

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
