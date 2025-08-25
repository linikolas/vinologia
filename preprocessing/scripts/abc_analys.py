import os

def perform_abc_analysis(df, mode='бокал', value_column='revenue', save_to_excel=False, filename=None):
    """
    Универсальный ABC-анализ для вина (по бокалам или по бутылкам).
    
    Parameters:
    df : DataFrame с данными о продажах (после обработки)
    mode : 'бокал' или 'бутылка' — что анализировать
    value_column : колонка для анализа ('revenue' или 'profit')
    save_to_excel : bool — сохранить ли результат в Excel (по умолчанию False)
    filename : str — имя файла (если None, то генерируется автоматически)

    Returns:
    DataFrame с результатами ABC-анализа
    """

    # фильтруем нужный тип продаж
    df_filtered = df[df['glass'] == mode].copy()

    if mode == 'бокал':
        grouped = df_filtered.groupby('article_name').agg(
            glasses_sold=('quantity', 'sum'),
            cost_per_glass=('glass_profit', 'first'),
            price_per_glass=('glass_price', 'first'),
            category=('article_category', 'first'),
            category_cat=('only_glass_cat', 'first')
        ).reset_index()

        grouped['revenue'] = grouped['glasses_sold'] * grouped['price_per_glass']
        grouped['profit'] = (grouped['price_per_glass'] - grouped['cost_per_glass']) * grouped['glasses_sold']

    elif mode == 'бутылка':
        grouped = df_filtered.groupby('article_name').agg(
            bottles_sold=('quantity', 'sum'),
            cost_per_bottle=('article_profit', 'first'),
            price_per_bottle=('article_price', 'first'),
            category=('article_category', 'first'),
        ).reset_index()

        grouped['revenue'] = grouped['bottles_sold'] * grouped['price_per_bottle']
        grouped['profit'] = (grouped['price_per_bottle'] - grouped['cost_per_bottle']) * grouped['bottles_sold']

    else:
        raise ValueError("mode должен быть 'бокал' или 'бутылка'")

    # сортировка
    df_sorted = grouped.sort_values(by=value_column, ascending=False).reset_index(drop=True)

    # накопленные значения
    df_sorted['cumulative_value'] = df_sorted[value_column].cumsum()
    df_sorted['cumulative_percentage'] = (df_sorted['cumulative_value'] /
                                          df_sorted[value_column].sum()) * 100
    df_sorted['value_percentage'] = (df_sorted[value_column] /
                                     df_sorted[value_column].sum()) * 100

    # классификация
    def classify_abc(cumulative_percentage):
        if cumulative_percentage <= 80:
            return 'A'
        elif cumulative_percentage <= 95:
            return 'B'
        else:
            return 'C'

    df_sorted['ABC_category'] = df_sorted['cumulative_percentage'].apply(classify_abc)

    # если нужно сохранить
    if save_to_excel:
        # создаём папку processed если её нет
        os.makedirs("processed", exist_ok=True)

        if filename is None:
            filename = f"ABC_{mode}_{value_column}.xlsx"

        filepath = os.path.join("processed", filename)
        df_sorted.to_excel(filepath, index=False)
        print(f"✅ Файл сохранён: {filepath}")

    return df_sorted
