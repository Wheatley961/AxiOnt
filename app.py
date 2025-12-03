import streamlit as st
from rdflib import Graph, URIRef, RDF, RDFS, OWL, Literal
from pyvis.network import Network
import tempfile

# URL онтологии
ONTOLOGY_URL = "https://raw.githubusercontent.com/Wheatley961/AxiOnt/main/axiology_ontology_ru.ttl"

st.set_page_config(page_title="Аксиологическая онтология", layout="wide")

# Заголовок и описание
st.title("Аксиологическая онтология государственной ценностной политики РФ (Указ № 809)")
st.markdown(
    """
    Онтология создана для формального представления государственной ценностной политики и моделирования взаимосвязей между ценностями, целями, задачами, инструментами и участниками, а также для формирования основы автоматизированного мониторинга, прогнозирования и поддержки управленческих решений.  
    Её концептуальная база включает официальный перечень традиционных ценностей, принципы государственной гуманитарной политики, анализ угроз ценностному суверенитету, а также сценарный и программно-целевой подходы. Формально реализована в логике OWL.
    """
)

# Загрузка графа
@st.cache_data(ttl=3600)
def load_graph():
    g = Graph()
    g.parse(ONTOLOGY_URL, format="turtle")
    return g

g = load_graph()

# Все классы, свойства и индивиды в графе (на URI)
all_classes = set()
all_object_properties = set()
all_datatype_properties = set()
all_properties = set()
all_individuals = set()

for s, p, o in g:
    # Классы
    if (p == RDF.type and o == OWL.Class) or (p == RDF.type and o == RDFS.Class):
        all_classes.add(s)
    # Индивиды
    if p == RDF.type and (o in all_classes or o == OWL.NamedIndividual or o == OWL.Thing):
        all_individuals.add(s)

# Более надёжный способ получить все классы, используя rdfs:subClassOf и rdf:type owl:Class
for s in g.subjects(RDF.type, OWL.Class):
    all_classes.add(s)
for s in g.subjects(RDF.type, RDFS.Class):
    all_classes.add(s)

# Свойства
for s in g.subjects(RDF.type, OWL.ObjectProperty):
    all_object_properties.add(s)
    all_properties.add(s)
for s in g.subjects(RDF.type, OWL.DatatypeProperty):
    all_datatype_properties.add(s)
    all_properties.add(s)

# Добавим всех индивидов: все, у которых rdf:type не класс и не property
for s, p, o in g.triples((None, RDF.type, None)):
    if o not in all_classes and o not in all_object_properties and o not in all_datatype_properties:
        all_individuals.add(s)

# Упрощаем: фильтры для выбора
def uri_label(g, uri):
    label = g.label(uri)
    if label:
        return str(label)
    else:
        return str(uri).split("#")[-1] if "#" in str(uri) else str(uri).split("/")[-1]

# Цвета для типов узлов
NODE_COLOR = {
    'class': '#1f78b4',          # синий
    'object_property': '#ff7f00',# оранжевый
    'datatype_property': '#33a02c', # зелёный
    'individual': '#6a3d9a'      # фиолетовый
}

# Добавление узла с метками и подсказкой всех свойств
def add_node_with_label(net, g, node, node_type):
    label = uri_label(g, node)
    # Получаем комментарий, если есть
    comment = g.value(node, RDFS.comment)
    comment_text = str(comment) if comment else ""

    # Собираем все свойства узла (predicate → object), чтобы показать при наведении
    properties = []
    for pred, obj in g.predicate_objects(subject=node):
        plabel = uri_label(g, pred)
        # Подставим значение объекта
        if isinstance(obj, Literal):
            val = str(obj)
        else:
            val = uri_label(g, obj)
        properties.append(f"{plabel}: {val}")

    title = f"<b>{label}</b><br>{comment_text}<br><br>" + "<br>".join(properties)
    net.add_node(str(node), label=label, title=title, color=NODE_COLOR[node_type])

# Получить подпись (label) и комментарий по URI (с учётом языка ru)
def get_label_comment(g, uri):
    label = ""
    comment = ""
    for l in g.objects(uri, RDFS.label):
        if hasattr(l, 'language') and l.language == 'ru':
            label = str(l)
            break
    if not label:
        for l in g.objects(uri, RDFS.label):
            label = str(l)
            break
    for c in g.objects(uri, RDFS.comment):
        if hasattr(c, 'language') and c.language == 'ru':
            comment = str(c)
            break
    if not comment:
        for c in g.objects(uri, RDFS.comment):
            comment = str(c)
            break
    return label, comment

def build_network_graph(g, filter_classes, filter_properties, filter_individuals):
    net = Network(height='700px', width='100%', directed=True)
    net.toggle_physics(True)

    added_nodes = set()

    def safe_add_node(node, node_type):
        if node not in added_nodes:
            add_node_with_label(net, g, node, node_type)
            added_nodes.add(node)

    show_all_classes = len(filter_classes) == 0
    show_all_properties = len(filter_properties) == 0
    show_all_individuals = len(filter_individuals) == 0

    # Добавляем классы
    for cls in all_classes:
        if show_all_classes or cls in filter_classes:
            safe_add_node(cls, 'class')

    # Добавляем свойства
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

    # Добавляем ребра
    for s, p, o in g:
        if (s in added_nodes) and (o in added_nodes) and (p in added_nodes):
            label_p, _ = get_label_comment(g, p)
            net.add_edge(str(s), str(o), label=label_p)

    return net


# Сортируем для удобства и отображения только русские метки
def filter_by_ru_label(items):
    res = []
    for item in sorted(items, key=lambda x: uri_label(g, x).lower()):
        label = uri_label(g, item)
        # Отображаем только кириллицу + цифры, пробелы и знаки препинания в названии
        if any('\u0400' <= c <= '\u04FF' for c in label):  
            res.append(item)
    return res


# Фильтры в боковой панели
st.sidebar.header("Фильтры для визуализации")

classes_list = filter_by_ru_label(all_classes)
selected_classes = st.sidebar.multiselect("Классы", options=classes_list, format_func=lambda x: uri_label(g, x))

properties_list = filter_by_ru_label(all_properties)
selected_properties = st.sidebar.multiselect("Свойства", options=properties_list, format_func=lambda x: uri_label(g, x))

individuals_list = filter_by_ru_label(all_individuals)
selected_individuals = st.sidebar.multiselect("Индивиды", options=individuals_list, format_func=lambda x: uri_label(g, x))

# Строим граф с выбранными фильтрами
net = build_network_graph(g, selected_classes, selected_properties, selected_individuals)

# Рендерим граф в HTML-файл во временном файле и показываем через компоненты Streamlit
with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
    net.show(tmp_file.name)
    html_path = tmp_file.name

# Отображаем граф в Streamlit
st.components.v1.html(open(html_path, "r", encoding="utf-8").read(), height=750, scrolling=True)

# Легенда (цвета узлов)
st.markdown("""
<style>
.legend-item {
    display: inline-block;
    margin-right: 15px;
    font-weight: 600;
    font-size: 14px;
}
.legend-color {
    display: inline-block;
    width: 18px;
    height: 18px;
    margin-right: 6px;
    vertical-align: middle;
    border-radius: 4px;
}
</style>
<div>
    <div class="legend-item"><span class="legend-color" style="background:#1f78b4"></span>Класс</div>
    <div class="legend-item"><span class="legend-color" style="background:#ff7f00"></span>Объектное свойство</div>
    <div class="legend-item"><span class="legend-color" style="background:#33a02c"></span>Дата-свойство</div>
    <div class="legend-item"><span class="legend-color" style="background:#6a3d9a"></span>Индивид</div>
</div>
""", unsafe_allow_html=True)

# Подвал с авторами
st.caption("""
Разработчики ресурса: И.Д. Мамаев
<a href="mailto:mamaev_id@voenmeh.ru" style="text-decoration: none; margin-left: 5px; background: none; border: none; padding: 0;">
    <span style="font-size: 1.2em; background: transparent;">📧</span>
</a>,
А.В. Лаптева
<a href="mailto:lapteva_av@voenmeh.ru" style="text-decoration: none; margin-left: 5px; background: none; border: none; padding: 0;">
    <span style="font-size: 1.2em; background: transparent;">📧</span>
</a>
""", unsafe_allow_html=True)
