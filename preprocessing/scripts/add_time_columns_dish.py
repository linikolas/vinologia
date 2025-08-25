import pandas as pd

def add_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавляет в DataFrame колонки:
    - month_name: название месяца (на русском)
    - day_name: название дня недели (на русском)
    - hour: час открытия заказа

    Аргументы:
        df (pd.DataFrame): DataFrame с колонкой 'open_time' в формате datetime.

    Возвращает:
        pd.DataFrame: DataFrame с новыми колонками.
    """

    df['open_time'] = pd.to_datetime(df['open_time'], errors='coerce')

    # Проверяем, что колонка open_time есть и она в datetime
    if 'open_time' not in df.columns:
        raise ValueError("В DataFrame нет колонки 'open_time'")
    if not pd.api.types.is_datetime64_any_dtype(df['open_time']):
        raise TypeError("Колонка 'open_time' должна быть в формате datetime")

    # Добавляем название месяца
    df['month'] = df['open_time'].dt.month_name()

    # Добавляем название дня недели
    df['day'] = df['open_time'].dt.day_name()

    # Добавляем час
    df['hour'] = df['open_time'].dt.hour

    df['month_year'] = df['open_time'].dt.to_period('M').astype(str)


    return df
