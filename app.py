# app.py
import streamlit as st
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL
import pandas as pd
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile
from io import BytesIO

# --- Утилиты для извлечения метаданных на русском ---
def get_label(g: Graph, node):
    # возвращает rdfs:label с приоритетом для языка 'ru', иначе любую метку, иначе QName/URI-ласть
    labels = list(g.objects(node, RDFS.label))
    if not labels:
        labels = list(g.objects(node, RDFS.label))  # повторно, но сохраним логику
    if labels:
        # ищем ru
        for lb in labels:
            if isinstance(lb, Literal) and lb.language == 'ru':
                return str(lb)
        # иначе первый
        return str(labels[0])
    # fallback: короткое представление
    if isinstance(node, URIRef):
        return node.split('#')[-1] if '#' in node else node.rsplit('/', 1)[-1]
    return str(node)

def get_comment(g: Graph, node):
    comments = list(g.objects(node, RDFS.comment))
    if not comments:
        # некоторые описания могут лежать в :hasDescription (user-defined) — попытаемся получить
        comments = list(g.objects(node, URIRef("http://example.org/axiology#hasDescription")))
    if comments:
        for c in comments:
            if isinstance(c, Literal) and c.language == 'ru':
                return str(c)
        return str(comments[0])
    return ""

def qname_safe(g: Graph, uri):
    try:
        return g.qname(uri)
    except Exception:
        return str(uri)

# --- Парсинг графа из текста/файла ---
def parse_turtle(ttl_text):
    g = Graph()
    # попытаться парсить как turtle
    g.parse(data=ttl_text, format='turtle')
    return g

# --- Подготовка таблицы триплетов ---
def graph_to_triples_df(g: Graph):
    rows = []
    for s, p, o in g:
        rows.append({
            'subject': qname_safe(g, s) if isinstance(s, URIRef) else str(s),
            'predicate': qname_safe(g, p) if isinstance(p, URIRef) else str(p),
            'object': qname_safe(g, o) if isinstance(o, URIRef) else str(o),
            's_term': s,
            'p_term': p,
            'o_term': o
        })
    return pd.DataFrame(rows)

# --- Собрать ноды и ребра для визуализации ---
def build_network(g: Graph, selected_node=None, max_nodes=1000):
    net = Network(height='750px', width='100%', directed=True)
    net.barnes_hut()
    added = set()

    # индекс меток (node -> label, type)
    node_info = {}

    # собираем сущности (классы, индивиды, свойства)
    for s in set(g.subjects()):
        if isinstance(s, URIRef):
            node_info[s] = {'label': get_label(g, s), 'type': infer_type(g, s)}

    for o in set(g.objects()):
        if isinstance(o, URIRef) and o not in node_info:
            node_info[o] = {'label': get_label(g, o), 'type': infer_type(g, o)}

    # ограничение по количеству нод для больших графов
    node_items = list(node_info.items())[:max_nodes]

    # добавить ноды
    for node, info in node_items:
        nid = str(node)
        label = info['label']
        ntype = info['type']
        color = type_color(ntype)
        size = 18 if nid == str(selected_node) else 12
        title = f"{label} ({ntype})<br>{get_comment(g, node)}"
        net.add_node(nid, label=label, title=title, color=color, size=size)

    # добавить ребра
    for s, p, o in g:
        if not (isinstance(s, URIRef) and isinstance(o, URIRef)):
            continue
        if s not in node_info or o not in node_info:
            continue
        # подпись ребра — метка предиката если есть
        pred_label = get_label(g, p) if isinstance(p, URIRef) else str(p)
        net.add_edge(str(s), str(o), title=pred_label, label=pred_label, arrows='to')

    return net

# --- Вспомогательные: определить тип ресурса (Class, Individual, ObjectProperty, DatatypeProperty, Other) ---
def infer_type(g: Graph, node):
    types = set(g.objects(node, RDF.type))
    if OWL.Class in types or URIRef("http://www.w3.org/2002/07/owl#Class") in types or RDFS.Class in types:
        return "Class"
    # Named individual: any triple where node rdf:type is not rdfs:Class and node appears as rdf:type for something? Simпле:
    if any(t for t in types if t not in (OWL.Class, RDFS.Class)):
        # если node сам является экземпляром чего-то
        return "NamedIndividual"
    # property?
    if (node, RDF.type, RDF.Property) in g or (node, RDF.type, OWL.ObjectProperty) in g or (node, RDF.type, OWL.DatatypeProperty) in g:
        # уточним
        if (node, RDF.type, OWL.ObjectProperty) in g:
            return "ObjectProperty"
        if (node, RDF.type, OWL.DatatypeProperty) in g:
            return "DatatypeProperty"
        return "Property"
    # fallback
    return "Other"

def type_color(ntype):
    palette = {
        "Class": "#2b8cbe",
        "NamedIndividual": "#7b3294",
        "ObjectProperty": "#d95f02",
        "DatatypeProperty": "#1b9e77",
        "Property": "#e7298a",
        "Other": "#999999"
    }
    return palette.get(ntype, "#999999")

# --- Сериализация подмножества и подготовка для скачивания ---
def serialize_subset(g: Graph, nodes_subset):
    subg = Graph()
    for s, p, o in g:
        if s in nodes_subset or o in nodes_subset:
            subg.add((s, p, o))
    return subg.serialize(format='turtle')

# --- UI ---
st.set_page_config(page_title="Анализ онтологии — визуализатор", layout="wide")
st.title("📚 Визуализатор аксиологической онтологии (OWL/Turtle)")
st.markdown("Загрузите файл `.ttl` или вставьте содержимое онтологии ниже. Интерфейс: поиск по меткам/комментариям/URI, интерактивный граф, таблица триплетов и экспорт.")

with st.sidebar:
    st.header("Загрузить онтологию")
    upload = st.file_uploader("Выберите файл .ttl", type=['ttl','ttl.txt','txt'])
    ttl_text_input = st.text_area("Или вставьте TTL прямо сюда (переопределяет файл)", height=200)
    st.markdown("---")
    st.header("Параметры визуализации")
    max_nodes = st.slider("Макс. число нод в графе", min_value=100, max_value=3000, value=1200, step=100)
    search_query = st.text_input("Поиск (label / comment / URI)", value="")
    st.markdown("Фильтр по типу ресурса:")
    typ_filters = st.multiselect("Типы", ["Class","NamedIndividual","ObjectProperty","DatatypeProperty","Property","Other"], default=["Class","NamedIndividual","ObjectProperty","DatatypeProperty","Property","Other"])
    st.markdown("---")
    st.write("Инструкции")
    st.write("1) Загрузите или вставьте TTL. 2) Подождите парсинга. 3) Используйте поиск и кликните по найденной сущности для подробностей.")
    st.markdown("Версия: 1.0 — интерфейс на русском (академический стиль)")

# чтение входных данных
ttl_text = None
if ttl_text_input and ttl_text_input.strip():
    ttl_text = ttl_text_input
elif upload is not None:
    try:
        ttl_text = upload.read().decode('utf-8')
    except:
        ttl_text = upload.read().decode('latin-1')

if not ttl_text:
    st.info("Пожалуйста, загрузите файл TTL или вставьте текст онтологии в левое меню.")
    st.stop()

# Парсим граф
try:
    g = parse_turtle(ttl_text)
except Exception as e:
    st.error("Ошибка парсинга TTL: " + str(e))
    st.stop()

st.success("Онтология успешно распознана. Триплетов: " + str(len(g)))

# Таблица триплетов
df_triples = graph_to_triples_df(g)

# Индекс нод
all_nodes = set()
for s, p, o in g:
    if isinstance(s, URIRef):
        all_nodes.add(s)
    if isinstance(o, URIRef):
        all_nodes.add(o)
# построим таблицу нод
nodes_rows = []
for n in all_nodes:
    nodes_rows.append({
        'uri': str(n),
        'qname': qname_safe(g, n),
        'label': get_label(g, n),
        'comment': get_comment(g, n),
        'type': infer_type(g, n)
    })
df_nodes = pd.DataFrame(nodes_rows)

# применение фильтрации
if search_query:
    mask = df_nodes['label'].str.contains(search_query, case=False, na=False) | \
           df_nodes['comment'].str.contains(search_query, case=False, na=False) | \
           df_nodes['uri'].str.contains(search_query, case=False, na=False) | \
           df_nodes['qname'].str.contains(search_query, case=False, na=False)
else:
    mask = pd.Series([True]*len(df_nodes))

mask = mask & df_nodes['type'].isin(typ_filters)
df_nodes_filtered = df_nodes[mask]

st.write(f"Найдено сущностей: {len(df_nodes_filtered)} (всего: {len(df_nodes)})")

# селектор сущности
selected_uri = None
if not df_nodes_filtered.empty:
    # показываем компактный список
    sel_option = st.selectbox("Выберите сущность для просмотра (или оставьте пустым)", options=[""] + df_nodes_filtered['label'].tolist())
    if sel_option:
        # найти uri по label
        row = df_nodes_filtered[df_nodes_filtered['label']==sel_option].iloc[0]
        selected_uri = URIRef(row['uri'])
else:
    st.info("Нет сущностей по текущему запросу/фильтру.")

# Визуализация графа (pyvis) — выделяем выбранную ноду
net = build_network(g, selected_node=selected_uri, max_nodes=max_nodes)
# Сохранить во временный файл и встроить
with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
    net.save_graph(tmp.name)
    html = open(tmp.name, 'r', encoding='utf-8').read()
components.html(html, height=750, scrolling=True)

# Показ информации о выбранной сущности
st.markdown("---")
st.h
