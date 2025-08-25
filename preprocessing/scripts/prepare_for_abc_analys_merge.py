import pandas as pd
import numpy as np

def merge_and_select(dish_df, article_df):
    """Объединяет данные и оставляет нужные колонки."""
    result = pd.merge(dish_df, article_df, on='article', how='right')
    result = result[['open_time', 'article_name', 'price', 'quantity', 'final_sum', 
                     'article_category', 'only_glass_cat', 'article_price', 'article_profit']]
    result['open_time'] = pd.to_datetime(result['open_time'], errors='coerce')

    cols = ['article_name', 'price', 'quantity', 'final_sum', 
        'article_category', 'only_glass_cat', 'article_price', 'article_profit']
    
    result[cols] = result[cols].fillna(0)
    return result #.fillna(0)

def add_glass_column(df):
    """Добавляет признак 'glass' (бокал или бутылка)."""
    df['glass'] = np.where(
        (df['article_category'] == 'вина по бокалам 150 мл') |
        ((df['quantity'] % 1 != 0) & (df['quantity'] != 0)),
        'бокал', 'бутылка'
    )
    return df

def normalize_quantity(df):
    """Переводит количество в формат 'кол-во бокалов'."""
    df['quantity'] = np.where(
        df['quantity'] % 1 != 0,
        df['quantity'] / 0.2,
        df['quantity']
    )
    return df

def add_glass_prices(df):
    """Рассчитывает цену и себестоимость одного бокала."""
    df['glass_price'] = np.where(
        (df['glass'] == 'бокал') & (df['article_category'] != 'вина по бокалам 150 мл'),
        df['article_price'] / 5,
        df['article_price']
    )
    df['glass_profit'] = np.where(
        (df['glass'] == 'бокал') & (df['article_category'] != 'вина по бокалам 150 мл'),
        df['article_profit'] / 5,
        df['article_profit']
    )
    return df

# def group_glass_sales(df):
#     """Группирует продажи только бокальных позиций."""
#     only_glass = df[df['glass'] == 'бокал']
#     grouped = only_glass.groupby('article_name').agg(
#         glasses_sold=('quantity', 'sum'),
#         cost_per_glass=('glass_profit', 'first'),
#         price_per_glass=('glass_price', 'first'),
#         category=('article_category', 'first'),
#         category_cat=('only_glass_cat', 'first')
#     ).reset_index()
#     return grouped


def process_wine_sales(dish_df, article_df):
    """Главная функция: объединяет все шаги анализа."""
    df = merge_and_select(dish_df, article_df)
    df = add_glass_column(df)
    df = normalize_quantity(df)
    return add_glass_prices(df)
    # return group_glass_sales(df)
