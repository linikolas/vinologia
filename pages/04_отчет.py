# -*- coding: utf-8 -*-
"""
Страница Streamlit: Сравнение продаж по месяцам (без «текущего/прошлого»)
Адаптировано под ТВОИ названия колонок из Excel:

  open_time        — дата/время продажи (используем для месячной агрегации)
  article_name     — наименование товара
  final_sum        — сумма/выручка (основная метрика для сравнения)
  article_category — категория (опциональный фильтр)
  only_glass_cat   — категория «по бокалам» (опциональный фильтр)
  article_price, article_profit, glass, glass_price, glass_profit — не обязательны для этой страницы, но не мешают

Что на странице:
  • Фильтры: период (месяц-от/месяц-до), категория, только по бокалам (если есть такие колонки)
  • Общая динамика по всем товарам (линейный график по месяцам)
  • ТОП‑N и Антилидеры‑N по сумме за период (bar chart)
  • Таблица по товарам: «Сумма за период», «Среднее в мес.», «Тренд в таблице» = мини‑график (столбики ИЛИ линия)

Как добавить в проект:
  1) Сохраните этот файл как pages/03_Сравнение_по_месяцам.py
  2) Положите all_sales.xlsx в корень проекта (рядом с app.py) или измените путь ниже.
  3) Запускайте: streamlit run app.py → вкладка «03 Сравнение по месяцам»
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Сравнение по месяцам", page_icon="🗓️", layout="wide")

st.title("🗓️ Сравнение продаж по месяцам")
st.caption("Фильтры внутри страницы. Никакого 'текущий/прошлый' — только выбранный период. Мини‑графики по умолчанию — столбики.")

# ------------------------------
# Загрузка и нормализация данных
# ------------------------------
@st.cache_data(show_spinner=False)
def load_sales(path: str = "/Users/nl/streamlit_test/data/all_sales.xlsx") -> pd.DataFrame:
    df = pd.read_excel(path)
    # Приведём имена колонок к нижнему регистру — так надёжнее
    df.columns = [str(c).strip().lower() for c in df.columns]

    need = {"open_time", "article_name", "final_sum"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"В файле отсутствуют колонки: {sorted(missing)}")

    # Типы
    df["open_time"] = pd.to_datetime(df["open_time"], errors="coerce")
    df = df.dropna(subset=["open_time"]).copy()
    df["final_sum"] = pd.to_numeric(df["final_sum"], errors="coerce").fillna(0)

    # Месяц из даты
    df["month"] = df["open_time"].dt.to_period("M")
    return df

try:
    df = load_sales()
except Exception as e:
    st.error("Не удалось загрузить all_sales.xlsx. Нужны колонки: open_time, article_name, final_sum")
    st.exception(e)
    st.stop()

# ------------------------------
# Фильтры (внутри контента, без сайдбара)
# ------------------------------
months_all = df["month"].dropna().sort_values().unique().tolist()
labels = [m.strftime("%Y-%m") for m in months_all]

with st.expander("Фильтры", expanded=True):
    left_i = st.selectbox(
        "От месяца",
        options=list(range(len(months_all))),
        index=max(0, len(months_all) - 12),
        format_func=lambda i: labels[i],
    )
    right_i = st.selectbox(
        "До месяца",
        options=list(range(len(months_all))),
        index=len(months_all) - 1,
        format_func=lambda i: labels[i],
    )
    start_m, end_m = sorted([months_all[left_i], months_all[right_i]])

    # Фильтр по категории, если колонка есть
    cat_col = "article_category" if "article_category" in df.columns else None
    glass_cat_col = "only_glass_cat" if "only_glass_cat" in df.columns else None
    glass_flag_col = "glass" if "glass" in df.columns else None

    if cat_col:
        cats = ["(все)"] + sorted(df[cat_col].dropna().astype(str).unique().tolist())
        sel_cat = st.selectbox("Категория", options=cats, index=0)
    else:
        sel_cat = "(все)"

    only_glass = False
    if glass_cat_col or glass_flag_col:
        only_glass = st.checkbox("Только по бокалам", value=False, help="Фильтровать по only_glass_cat/glass, если есть")

    top_n = st.slider("Размер ТОП‑N / Антилидеров‑N", min_value=3, max_value=30, value=5)

# Применяем фильтры к исходным данным
mask_period = (df["month"] >= start_m) & (df["month"] <= end_m)
cut = df.loc[mask_period].copy()

if sel_cat != "(все)" and cat_col:
    cut = cut[cut[cat_col].astype(str) == sel_cat]

if only_glass:
    if glass_cat_col and cut[glass_cat_col].notna().any():
        cut = cut[cut[glass_cat_col].astype(str).str.len() > 0]
    elif glass_flag_col and glass_flag_col in cut.columns:
        cut[glass_flag_col] = cut[glass_flag_col].astype(str).str.lower().isin(["true", "1", "да", "yes", "y"])  # приводим к bool
        cut = cut[cut[glass_flag_col] == True]

# ------------------------------
# Общая динамика по всем товарам (месячная)
# ------------------------------

total_monthly = cut.groupby("month")["final_sum"].sum().sort_index()
colA, colB = st.columns([2, 1])
with colA:
    st.subheader("Общая динамика (сумма по всем товарам)")
    tmp = total_monthly.copy()
    tmp.index = tmp.index.to_timestamp("M")
    st.line_chart(tmp)
with colB:
    st.metric("Период", f"{start_m.strftime('%Y-%m')} — {end_m.strftime('%Y-%m')}")
    st.metric("Товаров в выборке", f"{cut['article_name'].nunique():,}".replace(",", " "))
    st.metric("Сумма продаж", f"{int(total_monthly.sum()):,}".replace(",", " "))

st.divider()

# ------------------------------
# ТОП‑N / Антилидеры‑N по сумме за период
# ------------------------------
by_product_total = cut.groupby("article_name")["final_sum"].sum().sort_values(ascending=False)
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"ТОП‑{top_n} по сумме за период")
    st.bar_chart(by_product_total.head(top_n))
with col2:
    st.subheader(f"Антилидеры‑{top_n} (минимальная сумма за период)")
    st.bar_chart(by_product_total.tail(top_n))

st.divider()

# ------------------------------
# Таблица по товарам с мини‑графиком (месяц к месяцу) — АБСОЛЮТНЫЕ значения
# ------------------------------

# Подготовим список месяцев периода
period_months = pd.period_range(start=start_m, end=end_m, freq="M")

# product×month → сумма final_sum
pm = (
    cut.groupby(["article_name", "month"], dropna=False)["final_sum"]
      .sum().unstack(fill_value=0)
)

# Добавим недостающие месяцы, чтобы у всех был одинаковый диапазон
for m in period_months:
    if m not in pm.columns:
        pm[m] = 0
pm = pm[sorted(pm.columns)]

# Абсолютные месячные ряды по каждому товару
series_list = [pm.loc[idx, period_months].astype(float).tolist() for idx in pm.index]

# Сводка
summary = pd.DataFrame(index=pm.index)
summary["Сумма за период"] = [sum(vs) for vs in series_list]
summary["Среднее в мес."] = [round(sum(vs) / len(period_months), 2) for vs in series_list]
summary = (
    summary.sort_values("Сумма за период", ascending=False)
           .reset_index()
           .rename(columns={"article_name": "Товар"})
)

# Выбор вида микрографика: столбики (гистограмма) или линия
with st.expander("Настройка мини‑графика", expanded=False):
    chart_type = st.radio("Тип мини‑графика в таблице", ["Столбики", "Линия"], index=0, horizontal=True,
                          help="'Столбики' обычно читаются лучше при месячной детализации.")

# Добавляем колонку с данными тренда
trend_col = "Тренд (столбики)" if chart_type == "Столбики" else "Тренд (линия)"
summary[trend_col] = series_list

# Column config динамически под выбранный тип
help_txt = f"Месячные значения за период: {start_m.strftime('%Y-%m')} — {end_m.strftime('%Y-%m')}"
try:
    if chart_type == "Столбики":
        trend_cfg = st.column_config.BarChartColumn(trend_col, help=help_txt, y_min=0, width="large")
    else:
        trend_cfg = st.column_config.LineChartColumn(trend_col, help=help_txt, y_min=0, width="large")
except Exception:
    # Фолбэк на линию, если BarChartColumn недоступен в текущей версии Streamlit
    trend_cfg = st.column_config.LineChartColumn(trend_col, help=help_txt, y_min=0, width="large")

column_config = {
    "Товар": st.column_config.TextColumn("Товар", width="medium"),
    "Сумма за период": st.column_config.NumberColumn("Сумма за период", format="%d", width="small"),
    "Среднее в мес.": st.column_config.NumberColumn("Среднее в мес.", format="%.2f", width="small"),
    trend_col: trend_cfg,
}

visible_cols = ["Товар", "Сумма за период", "Среднее в мес.", trend_col]

st.subheader("Подробная таблица по товарам")
st.dataframe(
    summary[visible_cols],
    use_container_width=True,
    hide_index=True,
    column_config=column_config,
)

# Экспорт CSV
with st.expander("📥 Экспорт таблицы (CSV)"):
    csv = summary[visible_cols].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Скачать CSV",
        data=csv,
        file_name=f"products_monthly_{start_m.strftime('%Y-%m')}_{end_m.strftime('%Y-%m')}.csv",
        mime="text/csv",
    )
