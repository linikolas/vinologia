# pages/01_final_sum_report.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

st.set_page_config(page_title="Отчёт по продажам", layout="wide")

# ==== 1. Загружаем данные ====
@st.cache_data
def load_data():
    df = pd.read_excel("/Users/nl/streamlit_test/data/all_sales.xlsx")

    # Приводим дату к формату open_timetime
    df["open_time"] = pd.to_datetime(df["open_time"])
    df["month"] = df["open_time"].dt.to_period("M")
    return df

df = load_data()

# ==== 2. Определяем последний и предыдущий месяц ====
last_month = df["month"].max()
prev_month = last_month - 1

# ==== 3. Считаем суммы ====
# Сумма за последний месяц
last_month_final_sum = (
    df[df["month"] == last_month]
    .groupby("article_name")["final_sum"]
    .sum()
    .rename("last_month")
)

# Сумма за предыдущий месяц
prev_month_final_sum = (
    df[df["month"] == prev_month]
    .groupby("article_name")["final_sum"]
    .sum()
    .rename("prev_month")
)

# ==== 4. Собираем таблицу ====
summary = pd.DataFrame(last_month_final_sum).join(prev_month_final_sum, how="left").fillna(0)
summary["diff_abs"] = summary["last_month"] - summary["prev_month"]
summary["diff_pct"] = summary.apply(
    lambda row: (row["diff_abs"] / row["prev_month"] * 100) if row["prev_month"] != 0 else None,
    axis=1,
)

# ==== 5. Функция для спарклайна ====
def make_sparkline(article_name_sales):
    fig, ax = plt.subplots(figsize=(2, 0.5))
    ax.plot(article_name_sales["open_time"], article_name_sales["final_sum"], color="tab:blue", linewidth=1)
    ax.axis("off")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f'<img src="data:image/png;base64,{b64}" width="120"/>'

# ==== 6. Добавляем спарклайны ====
sparklines = {}
for article_name in df["article_name"].unique():
    article_name_sales = df[df["article_name"] == article_name].groupby("open_time")["final_sum"].sum().reset_index()
    sparklines[article_name] = make_sparkline(article_name_sales)

summary["sparkline"] = summary.index.map(sparklines)

# ==== 7. Финальная таблица ====
st.title("📊 Отчёт по продажам")
st.write(f"Период: {last_month} (сравнение с {prev_month})")

# Форматируем таблицу для отображения
table = summary.reset_index()[["article_name", "last_month", "prev_month", "diff_abs", "diff_pct", "sparkline"]]
table["diff_pct"] = table["diff_pct"].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "-")

st.write(table.to_html(escape=False), unsafe_allow_html=True)
