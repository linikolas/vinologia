import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt 
from preprocessing.scripts.load_and_prepare_all_dish import load_and_prepare_dish
from preprocessing.scripts.load_and_prepare_wine_article import load_and_prepare_wine_articles, change_article_category
from preprocessing.scripts.prepare_for_abc_analys_merge import process_wine_sales
from preprocessing.scripts.add_time_columns_dish import add_time_columns
import matplotlib.pyplot as plt
from calendar import month_name
import streamlit as st


dish = load_and_prepare_dish('/Users/nl/streamlit_test/data/Отчет по блюдам новое меню.xlsx')
article = load_and_prepare_wine_articles('/Users/nl/streamlit_test/data/Блюда артикулы.xlsx')
article = change_article_category(article)

df = process_wine_sales(dish, article)

data = df[(df.glass == 'бокал')]

data = data[data.open_time.notna()]

data.groupby('only_glass_cat')['quantity'].agg('sum')

data = add_time_columns(data)

# 1) Готовим данные: сумма по категориям × месяцам
# Если у тебя уже есть такой groupby — можно начать с него.
grp = (
    data.groupby(['only_glass_cat', 'month'], as_index=False)['quantity']
        .sum()
)

# 2) Делаем порядок месяцев календарным
# (если 'month' у тебя уже datetime/Period — замени на .dt.month_name())
all_months = [m for m in month_name if m]  # ['January', 'February', ... 'December']
cat_type = pd.api.types.CategoricalDtype(categories=all_months, ordered=True)
grp['month'] = grp['month'].astype(cat_type)

# 3) Список нужных категорий (4 штуки)
cats = ['белые_вина', 'дижестивы_оранжи', 'игристые', 'красные_вина']

# 4) Рисуем 2×2 субплота
fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharey=True)
axes = axes.ravel()

for i, cat in enumerate(cats):
    ax = axes[i]
    # данные по категории; реиндекс по всем месяцам, чтобы отсутствующие были 0
    dfc = (
        grp.loc[grp['only_glass_cat'] == cat, ['month', 'quantity']]
           .set_index('month')
           .reindex(all_months)              # календарный порядок
           .fillna(0.0)
           .reset_index()
           .rename(columns={'index': 'month'})
    )

    # Линейный график (можно заменить на bar — закомментированный код ниже)
    ax.plot(dfc['month'].astype(str), dfc['quantity'], marker='o')
    # ax.bar(dfc['month'].astype(str), dfc['quantity'])  # <- если хочешь столбики

    ax.set_title(cat)
    ax.set_xlabel('Месяц')
    ax.set_ylabel('Сумма продаж')
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.tick_params(axis='x', rotation=45)

# Если категорий меньше 4 — уберём лишние оси
for j in range(len(cats), 4):
    fig.delaxes(axes[j])

fig.suptitle('Продажи по категориям бокалов (по месяцам)', fontsize=14, y=0.98)
fig.tight_layout()

st.pyplot(fig)
