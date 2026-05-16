#!/usr/bin/env python3
"""
qa_check.py — Автоматический QA-контроль obshestvo_graph.html
Запускать после каждого изменения файла.
Использование: python3 qa_check.py [путь_к_файлу]
"""
import re, sys, json
from collections import Counter
from datetime import datetime

# ── Конфигурация ──────────────────────────────────────────────────
HTML_PATH = sys.argv[1] if len(sys.argv) > 1 else 'obshestvo_graph.html'
TDATA_CATS = ['terms','defs','feats','princs','osoben','types','forms']

# Ожидаемые межраздельные рёбра (минимум)
REQUIRED_CROSS = [
    ('t1_6','t2_1'),('t1_6','t3_1'),('t1_6','t4_1'),('t1_6','t5_1'),
    ('t1_7','t3_5'),('t1_7','t4_3'),('t1_11','t5_1'),
    ('t2_7','t5_10'),('t2_9','t5_8'),('t2_15','t5_11'),('t2_7','t3_1'),
    ('t3_5','t5_9'),('t3_7','t5_5'),
    ('t4_3','t5_3'),('t4_4','t5_6'),('t4_6','t5_6'),('t3_1','t4_1'),
]

# Ожидаемое число тем по разделам
EXPECTED_COUNTS = {'s1':15,'s2':18,'s3':10,'s4':12,'s5':20}

# Минимальная длина desc и ege
MIN_DESC = 80
MIN_EGE  = 50

# ── Загрузка файла ────────────────────────────────────────────────
try:
    with open(HTML_PATH, encoding='utf-8') as f:
        html = f.read()
except FileNotFoundError:
    print(f'❌ Файл не найден: {HTML_PATH}')
    sys.exit(1)

# ── Счётчики ──────────────────────────────────────────────────────
errors   = []
warnings = []
ok       = []

def ERR(msg): errors.append(msg)
def WARN(msg): warnings.append(msg)
def OK(msg):  ok.append(msg)

# ══════════════════════════════════════════════════════════════════
print('='*60)
print(f'🔍 QA-ПРОВЕРКА: {HTML_PATH}')
print(f'   {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print('='*60)

# ── 1. СТРУКТУРА ФАЙЛА ────────────────────────────────────────────
print('\n[1] Структура файла')

for section_name, marker in [
    ('NODES', "const NODES=["),
    ('EDGES', "const EDGES=["),
    ('TDATA', "const TDATA={"),
    ('MATS',  "const MATS={"),
    ('hierHtml', "function hierHtml"),
]:
    if marker in html:
        OK(f'  ✓ {section_name} найден')
    else:
        ERR(f'  ✗ {section_name} ОТСУТСТВУЕТ — критическая ошибка!')

# ── 2. КОЛИЧЕСТВО ТЕМ ─────────────────────────────────────────────
print('\n[2] Количество тем по разделам')

topic_sections = re.findall(r"type:'topic',sec:'(s\d)'", html)
counts = Counter(topic_sections)
for s, exp in EXPECTED_COUNTS.items():
    actual = counts.get(s, 0)
    if actual == exp:
        OK(f'  ✓ {s}: {actual} тем')
    else:
        ERR(f'  ✗ {s}: {actual} тем (ожидалось {exp})')

total = sum(counts.values())
if total == 75:
    OK(f'  ✓ Итого: {total} тем')
else:
    ERR(f'  ✗ Итого: {total} тем (ожидалось 75)')

# ── 3. РЁБРА ──────────────────────────────────────────────────────
print('\n[3] Анализ рёбер')

edges = re.findall(r"\{from:'([^']+)',\s*to:'([^']+)',\s*label:'([^']*)'\}", html)
edge_set = set((f,t) for f,t,l in edges)
total_edges = len(edges)
OK(f'  ✓ Всего рёбер: {total_edges}')

# Дубликаты
seen_e = set()
dups_e = []
for f,t,l in edges:
    if (f,t) in seen_e: dups_e.append((f,t))
    seen_e.add((f,t))
if dups_e:
    ERR(f'  ✗ Дублирующиеся рёбра ({len(dups_e)}): {dups_e}')
else:
    OK('  ✓ Дублей рёбер нет')

# Самоссылки
self_r = [(f,t) for f,t,l in edges if f==t]
if self_r:
    ERR(f'  ✗ Самоссылки: {self_r}')
else:
    OK('  ✓ Самоссылок нет')

# Изолированные темы
mats_pos = html.find('const MATS{')
if mats_pos < 0: mats_pos = html.find('const MATS =')
if mats_pos < 0: mats_pos = len(html)
all_topic_ids = re.findall(r"\{id:'(t\d+_\d+)'", html[:mats_pos])
edge_froms = [f for f,t,l in edges]
edge_tos   = [t for f,t,l in edges]
isolated = [tid for tid in all_topic_ids if tid not in edge_froms and tid not in edge_tos]
if isolated:
    WARN(f'  ⚠ Изолированных тем ({len(isolated)}): {isolated}')
else:
    OK('  ✓ Изолированных тем нет')

# Темы без исходящих рёбер
no_out = [tid for tid in all_topic_ids if tid not in edge_froms]
if len(no_out) > 15:
    WARN(f'  ⚠ Тем без исходящих рёбер: {len(no_out)} (норма < 15)')
elif no_out:
    OK(f'  ✓ Тем без исходящих рёбер: {len(no_out)} (в норме)')

# Межраздельные связи
cross = [(f,t,l) for f,t,l in edges if f[0]=='t' and t[0]=='t' and f[1]!=t[1]]
OK(f'  ✓ Межраздельных рёбер: {len(cross)}')

missing_cross = [(f,t) for f,t in REQUIRED_CROSS
                 if (f,t) not in edge_set and (t,f) not in edge_set]
if missing_cross:
    for f,t in missing_cross:
        WARN(f'  ⚠ Отсутствует обязательное ребро: {f} ↔ {t}')
else:
    OK(f'  ✓ Все {len(REQUIRED_CROSS)} обязательных межраздельных рёбер присутствуют')

# ── 4. ТDATA — ПОЛНОТА ────────────────────────────────────────────
print('\n[4] TDATA — полнота контента')

tdata_start = html.find('const TDATA={')
tdata_end   = html.find('\n};\n', tdata_start) + 4
tdata_block = html[tdata_start:tdata_end] if tdata_start > 0 else ''

tdata_ids = re.findall(r"'(t\d+_\d+)':\{", tdata_block)
OK(f'  ✓ Тем в TDATA: {len(tdata_ids)}')

missing_from_tdata = [tid for tid in all_topic_ids if tid not in tdata_ids]
if missing_from_tdata:
    ERR(f'  ✗ Тем без TDATA ({len(missing_from_tdata)}): {missing_from_tdata}')
else:
    OK('  ✓ Все темы имеют TDATA')

# Проверка категорий
missing_cats_report = []
empty_cats_report   = []
for tid in tdata_ids:
    pat = f"'{tid}'" + r":\{(.*?)\},"
    m = re.search(pat, tdata_block, re.DOTALL)
    if not m: continue
    block = m.group(1)
    for cat in TDATA_CATS:
        cm = re.search(cat + r':(\[.*?\])', block)
        if not cm:
            missing_cats_report.append(f'{tid}.{cat}')
        else:
            items = re.findall(r'"([^"]+)"', cm.group(1))
            if not items:
                empty_cats_report.append(f'{tid}.{cat}')

if missing_cats_report:
    ERR(f'  ✗ Отсутствуют категории ({len(missing_cats_report)}): {missing_cats_report[:5]}...')
else:
    OK(f'  ✓ Все 7 категорий присутствуют у каждой темы')

if empty_cats_report:
    WARN(f'  ⚠ Пустые категории ({len(empty_cats_report)}): {empty_cats_report[:5]}')
else:
    OK('  ✓ Нет пустых категорий')

# ── 5. КОНТЕНТ — ДЛИНА ПОЛЕЙ ──────────────────────────────────────
print('\n[5] Длина контентных полей')

descs = re.findall(r"num:'([^']+)'.*?desc:'([^']+)'", html, re.DOTALL)
short_descs = [(num, len(d), d[:40]) for num, d in descs if len(d) < MIN_DESC]
if short_descs:
    for num, ln, preview in short_descs:
        WARN(f'  ⚠ Короткий desc у {num} ({ln} симв.): {preview}...')
else:
    OK(f'  ✓ Все desc длиннее {MIN_DESC} символов')

eges_data = re.findall(r"num:'([^']+)'.*?ege:'([^']+)'", html, re.DOTALL)
short_eges = [(num, len(e)) for num, e in eges_data if len(e) < MIN_EGE]
if short_eges:
    for num, ln in short_eges:
        WARN(f'  ⚠ Короткий ege у {num} ({ln} симв.)')
else:
    OK(f'  ✓ Все ege длиннее {MIN_EGE} символов')

# ── 6. ЦВЕТА И ЛЕГЕНДА ────────────────────────────────────────────
print('\n[6] Цвета разделов')

sec_colors = dict(re.findall(r"(s\d):\{c:'(#[0-9a-fA-F]+)'", html))
legend_pairs = re.findall(r'background:(#[0-9a-fA-F]+).*?(\d Человек|\d Экономика|\d Социум|\d Политика|\d Право)', html[:3000], re.DOTALL)
if sec_colors:
    OK(f'  ✓ Палитра SEC определена: {list(sec_colors.keys())}')
else:
    WARN('  ⚠ Палитра SEC не найдена')

# ── 7. JS СИНТАКСИС (базовая проверка) ───────────────────────────
print('\n[7] Базовый JS-синтаксис')

# Парность скобок в NODES/EDGES
nodes_block = re.search(r'const NODES=\[(.*?)\];', html, re.DOTALL)
if nodes_block:
    nb = nodes_block.group(1)
    open_b  = nb.count('{')
    close_b = nb.count('}')
    if open_b == close_b:
        OK(f'  ✓ NODES: скобки сбалансированы ({open_b} пар)')
    else:
        ERR(f'  ✗ NODES: несбаланс. скобки ({open_b} открыто, {close_b} закрыто)')

edges_block = re.search(r'const EDGES=\[(.*?)\];', html, re.DOTALL)
if edges_block:
    eb = edges_block.group(1)
    open_b  = eb.count('{')
    close_b = eb.count('}')
    if open_b == close_b:
        OK(f'  ✓ EDGES: скобки сбалансированы ({open_b} пар)')
    else:
        ERR(f'  ✗ EDGES: несбаланс. скобки ({open_b} открыто, {close_b} закрыто)')

# ── ИТОГ ──────────────────────────────────────────────────────────
print('\n' + '='*60)
print('📊 ИТОГ')
print('='*60)
print(f'  ✅ Пройдено:    {len(ok)}')
print(f'  ⚠  Предупреждения: {len(warnings)}')
print(f'  ❌ Ошибки:     {len(errors)}')

if errors:
    print('\n❌ ОШИБКИ (требуют исправления):')
    for e in errors:
        print(f'  {e}')

if warnings:
    print('\n⚠  ПРЕДУПРЕЖДЕНИЯ (рекомендуется исправить):')
    for w in warnings:
        print(f'  {w}')

score = round(100 * len(ok) / max(len(ok)+len(warnings)+len(errors), 1))
print(f'\n🏆 Качество базы: {score}%')

if len(errors) == 0:
    print('✅ Критических ошибок нет — граф готов к использованию!')
else:
    print('\u274c \u0415\u0441\u0442\u044c \u043a\u0440\u0438\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u043e\u0448\u0438\u0431\u043a\u0438 \u2014 \u0438\u0441\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u043f\u0435\u0440\u0435\u0434 \u043f\u0443\u0431\u043b\u0438\u043a\u0430\u0446\u0438\u0435\u0439.')

print('='*60)
import sys as _sys; _sys.exit(0 if len(errors) == 0 else 1)
