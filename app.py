import streamlit as st
from rdflib import Graph, RDF, RDFS, OWL, URIRef
from pyvis.network import Network
import tempfile

# URL онтологии
ONTOLOGY_URL = "https://raw.githubusercontent.com/Wheatley961/AxiOnt/main/axiology_ontology_ru.ttl"

st.set_page_config(page_title="Аксиологическая онтология РФ", layout="wide")

# --- Загрузка графа ---
@st.cache_data(show_spinner=True)
def load_graph():
    g = Graph()
    g.parse(ONTOLOGY_URL, format="ttl")
    return g

g = load_graph()

# --- Получение всех классов, свойств и индивидов с русскими метками и комментариями ---

def get_label_comment(g, node):
    label = None
    comment = None
    for _, _, o in g.triples((node, RDFS.label, None)):
        if hasattr(o, 'language') and o.language == 'ru':
            label = str(o)
            break
    if not label:
        label = node.split('#')[-1] if isinstance(node, str) else str(node)
    for _, _, o in g.triples((node, RDFS.comment, None)):
        if hasattr(o, 'language') and o.language == 'ru':
            comment = str(o)
            break
    return label, comment

def get_all_classes(g):
    classes = set(g.subjects(RDF.type, OWL.Class))
    # Иногда классы могут не иметь rdf:type OWL.Class, но есть rdfs:label и используются как классы
    # Можно добавить подклассы или что-то еще, если нужно
    return sorted(classes, key=lambda x: str(x))

def get_all_object_properties(g):
    return sorted(set(g.subjects(RDF.type, OWL.ObjectProperty)), key=lambda x: str(x))

def get_all_datatype_properties(g):
    return sorted(set(g.subjects(RDF.type, OWL.DatatypeProperty)), key=lambda x: str(x))

def get_all_properties(g):
    # Объединяем object и datatype свойства
    return sorted(set(get_all_object_properties(g)).union(set(get_all_datatype_properties(g))), key=lambda x: str(x))

def get_all_individuals(g):
    # Индивиды: те, у которых есть rdf:type, но не являются классами
    individuals = set()
    for s, p, o in g.triples((None, RDF.type, None)):
        if o in get_all_classes(g):
            individuals.add(s)
    return sorted(individuals, key=lambda x: str(x))

# Получаем списки для селектов
all_classes = get_all_classes(g)
all_object_properties = get_all_object_properties(g)
all_datatype_properties = get_all_datatype_properties(g)
all_properties = get_all_properties(g)
all_individuals = get_all_individuals(g)

# --- Функция для добавления узлов с цветами и подсказками ---

def add_node_with_label(net, g, node, node_type):
    label, comment = get_label_comment(g, node)
    tooltip = label if not comment else f"{label}\n{comment}"

    color_map = {
        'class': '#1f78b4',         # синий
        'object_property': '#ff7f00',  # оранжевый
        'datatype_property': '#ff7f00', # тоже оранжевый
        'individual': '#33a02c'     # зеленый
    }
    shape_map = {
        'class': 'ellipse',
        'object_property': 'box',
        'datatype_property': 'box',
        'individual': 'dot'
    }

    color = color_map.get(node_type, '#aaaaaa')
    shape = shape_map.get(node_type, 'ellipse')

    net.add_node(str(node), label=label, title=tooltip, color=color, shape=shape)

# --- Функция для построения графа с фильтрацией ---
def build_network_graph(g, filter_classes, filter_properties, filter_individuals):
    net = Network(height='700px', width='100%', directed=True)

    # Чтобы не дублировать, сохраним добавленные узлы
    added_nodes = set()

    def safe_add_node(node, node_type):
        if node not in added_nodes:
            add_node_with_label(net, g, node, node_type)
            added_nodes.add(node)

    # Фильтрация — если пустые списки, значит — показывать все
    show_all_classes = len(filter_classes) == 0
    show_all_properties = len(filter_properties) == 0
    show_all_individuals = len(filter_individuals) == 0

    # Добавляем классы
    for cls in all_classes:
        if show_all_classes or cls in filter_classes:
            safe_add_node(cls, 'class')

    # Добавляем свойства (объектные и датные)
    for prop in all_properties:
        if show_all_properties or prop in filter_properties:
            if prop in all_object_properties:
                safe_add_node(prop, 'object_property')
            else:
                safe_add_node(prop, 'datatype_property')

    # Добавляем индивидов
    for ind in all_individuals:
        if show_all_individuals or ind in filter_individuals:
            safe_add_node(ind, 'individual')

    # Добавляем ребра (отношения)
    for s, p, o in g:
        # Фильтруем по узлам — обе вершины должны быть в графе
        if s in added_nodes and o in added_nodes and p in added_nodes or p in all_properties:
            # Проверяем фильтрацию ребер по свойствам
            if (show_all_properties or p in filter_properties) and \
               (show_all_classes or (s in filter_classes or s in filter_individuals)) and \
               (show_all_classes or (o in filter_classes or o in filter_individuals)):
                # Метка ребра
                label_p, _ = get_label_comment(g, p)
                net.add_edge(str(s), str(o), label=label_p)

    net.toggle_physics(True)
    return net

# --- Streamlit UI ---

st.title("Аксиологическая онтология государственной ценностной политики РФ (Указ № 809)")

st.markdown(
    """
    Онтология создана для формального представления государственной ценностной политики и моделирования взаимосвязей между ценностями, целями, задачами, инструментами и участниками, а также для формирования основы автоматизированного мониторинга, прогнозирования и поддержки управленческих решений.  
    Её концептуальная база включает официальный перечень традиционных ценностей, принципы государственной гуманитарной политики, анализ угроз ценностному суверенитету, а также сценарный и программно-целевой подходы.  
    Формально реализована в логике OWL.
    """
)

col1, col2, col3 = st.columns(3)

with col1:
    selected_classes = st.multiselect(
        "Выберите классы для отображения",
        options=all_classes,
        format_func=lambda x: get_label_comment(g, x)[0]
    )
with col2:
    selected_properties = st.multiselect(
        "Выберите свойства для отображения",
        options=all_properties,
        format_func=lambda x: get_label_comment(g, x)[0]
    )
with col3:
    selected_individuals = st.multiselect(
        "Выберите индивидов для отображения",
        options=all_individuals,
        format_func=lambda x: get_label_comment(g, x)[0]
    )

# Построение графа по фильтрам
net = build_network_graph(g, selected_classes, selected_properties, selected_individuals)

# Рендерим в HTML файл и показываем в Streamlit
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
    path = tmp.name
    net.show(path)
    HtmlFile = open(path, 'r', encoding='utf-8')
    html_content = HtmlFile.read()
    HtmlFile.close()
    st.components.v1.html(html_content, height=720, scrolling=True)

# --- Caption ---
st.caption(
    """
    Разработчики ресурса: И.Д. Мамаев
    <a href="mailto:mamaev_id@voenmeh.ru" style="text-decoration:none; margin-left:5px;">
        <span style="font-size:1.2em;">📧</span>
    </a>,
    А.В. Лаптева
    <a href="mailto:lapteva_av@voenmeh.ru" style="text-decoration:none; margin-left:5px;">
        <span style="font-size:1.2em;">📧</span>
    </a>
    """,
    unsafe_allow_html=True,
)
