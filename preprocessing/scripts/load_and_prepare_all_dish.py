import pandas as pd

def load_and_prepare_dish(filepath: str) -> pd.DataFrame:
    """
    Загружает Excel-файл с отчетом по блюдам,
    оставляет только нужные колонки, удаляет пропуски
    и переименовывает их в английские названия.

    Аргументы:
        filepath (str): Путь к Excel-файлу.

    Возвращает:
        pd.DataFrame: Очищенный и переименованный DataFrame.
    """
    # Словарь для переименования колонок
    col_map = {
        'Код блюда': 'article',
          # на случай, если название будет другим
        'Блюдо': 'dish',
        'Вр. открытия': 'open_time',
        '№ смены': 'session_id',
        '№ заказа': 'order_id',
        '№ стола': 'table_no',
        'Цена': 'price',
        'Кол-во': 'quantity',
        'Полн. сумма, р.': 'total_sum',
        'Скидка': 'discount',
        'Итог. сумма, р.': 'final_sum',
        'Типы оплаты': 'payment_type',
        '№ гостя': 'guest_no'
    }

    # Загружаем файл
    df = pd.read_excel(filepath, skiprows=3, header=0)

    # Переименовываем колонки по словарю
    df = df.rename(columns=col_map)

    # Оставляем только колонки, которые есть в col_map
    df = df[[v for v in col_map.values() if v in df.columns]]

    # Удаляем пропущенные строки
    df = df.dropna()

    df = df.map(lambda x: x.lower() if isinstance(x, str) else x)

    # Конвертируем open_time в datetime с явным форматом
    if 'open_time' in df.columns:
        df['open_time'] = pd.to_datetime(df['open_time'], format='%d.%m.%Y %H:%M')

    return df
