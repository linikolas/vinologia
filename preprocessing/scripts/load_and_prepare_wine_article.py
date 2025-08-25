import pandas as pd
import numpy as np

def load_and_prepare_wine_articles(filepath: str) -> pd.DataFrame:
    """
    Загружает Excel с артикулами, оставляет только категории вина,
    создаёт отдельный столбец для вин по бокалам,
    очищает лишние колонки и возвращает DataFrame.
    """

    # Колонки, которые берём из Excel
    columns_to_keep = [
        'Unnamed: 3', 'Unnamed: 4', 'Unnamed: 5',
        'Артикул', 'Цена, р.', 'Себестоимость, р.', 'Себестоимость, %'
    ]

    # Читаем файл
    df = pd.read_excel(filepath, skiprows=1, header=0)

    # Заполняем пропуски в категориях
    for col in ['Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3']:
        if col in df.columns:
            df[col] = df[col].ffill()

    # Категории вина
    wine_categories = ['Белые вина', 'Белые вина России', 'Вина вне карты', 'ВИНА ПО БОКАЛАМ 150 МЛ',
       'Дижестивы/Сладкие вина', 'Игристые вина Россия', 'Игристые Вина со всего Мира',
       'Красные вина', 'Красные вина России', 'Оранжевые и розовые вина', 'Пино де Шарант',
       'Шампань Франция']

    # Оставляем только нужные колонки
    df = df[columns_to_keep]

    # Фильтруем только категории вина
    df_wine = df[df['Unnamed: 3'].isin(wine_categories)].copy()

    # Протягиваем названия для вин по бокалам
    mask_glass = df_wine['Unnamed: 3'] == 'ВИНА ПО БОКАЛАМ 150 МЛ'
    df_wine.loc[mask_glass, 'Unnamed: 4'] = df_wine.loc[mask_glass, 'Unnamed: 4'].ffill()

    # Новый столбец с категориями бокалов
    categories = ['Белые 150 мл', 'Дижестивы и розовые 75-150 мл',
                  'Игристые 150 мл', 'Красные 150 мл']
    df_wine['only_glass_cat'] = np.where(df_wine['Unnamed: 4'].isin(categories),
                                         df_wine['Unnamed: 4'], 'другое')

    # ✅ Создаём article_name из Unnamed: 4 и заполняем пропуски значениями из Unnamed: 5
    df_wine['article_name'] = df_wine['Unnamed: 5'].fillna(df_wine['Unnamed: 4'])

    # Удаляем временные колонки
    df_wine.drop(['Unnamed: 4', 'Unnamed: 5'], axis=1, inplace=True)

    # Автоматическое переименование
    rename_map = {
        'Unnamed: 3': 'article_category',
        'Артикул': 'article',
        'Цена, р.': 'article_price',
        'Себестоимость, р.': 'article_profit',
        'Себестоимость, %': 'article_profit_percent'
    }
    df_wine.rename(columns=rename_map, inplace=True)

    # Переставляем колонки в нужном порядке
    df_wine = df_wine[
        ['article_category', 'only_glass_cat', 'article_name', 'article', 'article_price',
         'article_profit', 'article_profit_percent']
    ]

    # Округляем проценты
    df_wine['article_profit_percent'] = pd.to_numeric(
        df_wine['article_profit_percent'], errors='coerce'
    ).round(2)

    # Удаляем строки, где цена <= 1
    df_wine = df_wine[df_wine['article_price'] > 1]

    # Исправляем формат прибыли
    df_wine['article_profit'] = df_wine['article_profit'].astype(str).str.replace(',', '.', regex=False)
    df_wine['article_profit'] = pd.to_numeric(df_wine['article_profit'], errors='coerce')

    # Убираем строки с NaN
    df_wine.dropna(inplace=True)


    df_wine = df_wine.map(lambda x: x.lower() if isinstance(x, str) else x)

    return df_wine
