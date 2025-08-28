import pandas as pd
import numpy as np
from preprocessing.scripts.load_and_prepare_all_dish import load_and_prepare_dish
from preprocessing.scripts.load_and_prepare_wine_article import load_and_prepare_wine_articles, change_article_category
from preprocessing.scripts.prepare_for_abc_analys_merge import process_wine_sales
from preprocessing.scripts.abc_analys import perform_abc_analysis
import streamlit as st


st.set_page_config(page_title="ABC тест вин по бокалам", layout="wide")

# ==== 7. Финальная таблица ====
st.title("ABC тест вин по бокалам")

dish = load_and_prepare_dish('/Users/nl/streamlit_test/data/Отчет по блюдам новое меню.xlsx')
article = load_and_prepare_wine_articles('/Users/nl/streamlit_test/data/Блюда артикулы.xlsx')
article = change_article_category(article)

data = process_wine_sales(dish, article)

data = perform_abc_analysis(data)


data = data[['article_name', 'glasses_sold', 'cost_per_glass', 'price_per_glass', 
      'revenue', 'profit', 'value_percentage', 'ABC_category']]

st.dataframe(
    data,
    use_container_width=True,  # растянуть на всю ширину страницы
    height=500                 # регулируй под себя
)

