import pandas as pd
import re
import os
import requests
from urllib.parse import urlparse
import time
import unicodedata

# === НАСТРОЙКИ ===
INPUT_FILE = "products_export_1(1).csv"
OUTPUT_FILE = "products_normalized.csv"
IMAGES_DIR = "product_images"
DOWNLOAD_IMAGES = False  # Установите True для скачивания изображений

# === РЕЖИМ ОБРАБОТКИ ПУСТЫХ КОЛОНОК ===
# 'show' — только показать список колонок с <= порога значений
# 'remove' — удалить такие колонки
EMPTY_COLS_MODE = 'remove'  # <-- 'show' или 'remove'

# === ПОРОГ УДАЛЕНИЯ КОЛОНОК ===
# Колонка удаляется, если непустых значений <= этого числа
EMPTY_COL_THRESHOLD = 2  # например: 0 — только полностью пустые; 3 — почти пустые

# Создаём папку для изображений
if DOWNLOAD_IMAGES and not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)


def to_snake_case(name: str) -> str:
    """
    Конвертирует строку в snake_case.
    Поддерживает CamelCase, пробелы, знаки препинания.
    """
    # Удаляем диакритику (accents)
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')

    # Заменяем любые не-буквы/не-цифры на пробелы
    name = re.sub(r'[^a-zA-Z0-9]+', ' ', name)

    # Разбиваем на слова, приводим к нижнему регистру
    words = name.strip().split()
    return '_'.join(words).lower()


def process_metafield_column(original_name: str) -> str:
    """
    Обрабатывает колонки вида:
      "Grapes (product.metafields.filter.grapes)"
    Возвращает:
      "grapes_filter_grapes"
    Если скобок нет — возвращает обычный snake_case.
    """
    match = re.search(r'^(.*?)\s*\(product\.metafields\.([^\)]+)\)$', original_name.strip())
    if match:
        display_name = match.group(1).strip()
        meta_path = match.group(2).strip()  # например: "filter.grapes"

        # Преобразуем display_name в snake_case
        display_snake = to_snake_case(display_name)

        # Преобразуем путь: заменяем точки на подчёркивания
        path_snake = meta_path.replace('.', '_')

        # Формируем: {display}_{path}
        return f"{display_snake}_{path_snake}"
    else:
        # Обычная колонка — просто snake_case
        return to_snake_case(original_name)


# === ЗАГРУЗКА ===
df = pd.read_csv(INPUT_FILE, dtype=str)

# === 1. Добавляем ID ===
df.insert(0, 'id', range(1, len(df) + 1))

# === 2. Переименовываем ВСЕ колонки ===
new_columns = {}
for col in df.columns:
    if col == 'id':
        new_columns[col] = 'old_id'
    else:
        new_name = process_metafield_column(col)
        # Гарантируем уникальность имён (на случай дубликатов)
        counter = 1
        final_name = new_name
        while final_name in new_columns.values():
            final_name = f"{new_name}_{counter}"
            counter += 1
        new_columns[col] = final_name

df.rename(columns=new_columns, inplace=True)

# === 3. Функция нормализации строки ===
def normalize_row(row):
    # Получаем значения по новым именам колонок (в snake_case)
    cat = str(row.get("product_category", "")).strip()
    title = str(row.get("title", "")).strip()

    # Извлекаем опции (после переименования они в snake_case)
    opt1_name = str(row.get("option1_name", "")).strip()
    opt1_val = str(row.get("option1_value", "")).strip()
    opt2_name = str(row.get("option2_name", "")).strip()
    opt2_val = str(row.get("option2_value", "")).strip()
    opt3_name = str(row.get("option3_name", "")).strip()
    opt3_val = str(row.get("option3_value", "")).strip()

    def clean(val):
        return "" if val.lower() in ("nan", "none", "") else val

    opt1_val = clean(opt1_val)
    opt2_val = clean(opt2_val)
    opt3_val = clean(opt3_val)

    # --- Вина ---
    if "Alcoholic Beverages > Wine" in cat or "Wine" in title or "vin" in title.lower():
        vintage = ""  # <-- по умолчанию пусто
        size = "0.75 L"

        for name, val in [(opt1_name, opt1_val), (opt2_name, opt2_val), (opt3_name, opt3_val)]:
            name_lower = name.lower()
            if re.fullmatch(r"\d{4}", val):
                vintage = val
            elif any(kw in name_lower for kw in ["vint", "añad", "añada", "cosecha", "vintage"]):
                vintage = val
            elif any(kw in name_lower for kw in ["size", "tamaño", "formato", "capacidad"]):
                size = normalize_size(val)
            elif val and any(kw in val.lower() for kw in ["l", "ml", "gr", "kg"]) and not re.fullmatch(r"\d{4}", val):
                size = normalize_size(val)

        row["option1_name"] = "Vintage"
        row["option1_value"] = vintage
        row["option2_name"] = "Size"
        row["option2_value"] = size
        row["option3_name"] = ""
        row["option3_value"] = ""

    # --- Пиво / Безалкогольные напитки ---
    elif any(x in cat for x in ["> Beer", "> Low Alcohol", "> Water"]) or "beer" in title.lower() or "agua" in title.lower():
        exp_date = ""
        for val in [opt1_val, opt2_val, opt3_val]:
            if val:
                exp_date = val
                break
        row["option1_name"] = "Expiration Date"
        row["option1_value"] = exp_date
        row["option2_name"] = ""
        row["option2_value"] = ""
        row["option3_name"] = ""
        row["option3_value"] = ""

    # --- Крепкий алкоголь / Ликёры ---
    elif any(x in cat for x in ["> Liquor", "> Orujo", "> Brandy", "> Whiskey", "> Gin"]) or "whisky" in title.lower() or "gin" in title.lower():
        size = "0.7 L"
        for val in [opt1_val, opt2_val, opt3_val]:
            if val and any(kw in val.lower() for kw in ["l", "lit"]):
                size = normalize_size(val)
                break
        row["option1_name"] = "Size"
        row["option1_value"] = size
        row["option2_name"] = ""
        row["option2_value"] = ""
        row["option3_name"] = ""
        row["option3_value"] = ""

    # --- Еда: оливки, закуски, масло ---
    elif "Food Items >" in cat or "Cooking Oils" in cat or "olive" in title.lower() or "aceituna" in title.lower():
        size = ""
        for val in [opt1_val, opt2_val, opt3_val]:
            if val and any(kw in val.lower() for kw in ["gr", "kg", "g", "ml"]):
                size = normalize_size(val)
                break
        row["option1_name"] = "Size"
        row["option1_value"] = size if size else "Default"
        row["option2_name"] = ""
        row["option2_value"] = ""
        row["option3_name"] = ""
        row["option3_value"] = ""

    # --- Упаковка: коробки, мешки ---
    elif "Gift Boxes & Tins" in cat or "Shopping Bags" in cat:
        if "kraft" in title.lower() or "tiffany" in title.lower():
            color = "kraft"
            if "tiffany" in title.lower():
                color = "tiffany"
            row["option1_name"] = "Color"
            row["option1_value"] = color
        else:
            row["option1_name"] = "Title"
            row["option1_value"] = "Default Title"
        row["option2_name"] = ""
        row["option2_value"] = ""
        row["option3_name"] = ""
        row["option3_value"] = ""

    # --- События ---
    elif "Event Tickets" in cat:
        row["option1_name"] = "Date"
        row["option2_name"] = "Location"
        row["option3_name"] = ""
        row["option3_value"] = ""

    # --- Товары без категории или неизвестные ---
    else:
        # Просто унифицируем: если есть год → Vintage, если объём → Size
        vintage = ""
        size = ""

        for name, val in [(opt1_name, opt1_val), (opt2_name, opt2_val), (opt3_name, opt3_val)]:
            if re.fullmatch(r"\d{4}", val):
                vintage = val
            elif val and any(kw in val.lower() for kw in ["l", "ml", "gr", "kg"]):
                size = normalize_size(val)

        if size:
            row["option1_name"] = "Vintage"
            row["option1_value"] = vintage
            row["option2_name"] = "Size"
            row["option2_value"] = size
        else:
            # Оставляем как есть, но приводим названия к английскому
            name_map = {
                "Título": "Title",
                "Talla": "Size",
                "F. Caducidad": "Expiration Date",
                "Fecha de caducidad": "Expiration Date",
                "Color": "Color",
            }
            row["option1_name"] = name_map.get(opt1_name, opt1_name)
            row["option2_name"] = name_map.get(opt2_name, opt2_name)
            row["option3_name"] = name_map.get(opt3_name, opt3_name)

        row["option3_name"] = ""
        row["option3_value"] = ""

    return row


def normalize_size(s):
    if not s:
        return "0.75 L"
    s = s.replace(",", ".").strip()
    if re.match(r"^\d+\.?\d*$", s):
        s += " L"
    elif not re.search(r'[LlGgKkMm]$', s):
        s += " L"
    return s


# === 4. Применяем нормализацию ===
print("🔄 Нормализация данных...")
df = df.apply(normalize_row, axis=1)


# === 5. Определяем "почти пустые" колонки ===
def count_non_empty(series):
    """
    Считает количество значений, которые НЕ являются:
      - NaN
      - пустой строкой ''
      - строкой 'nan' или 'None' (в любом регистре после strip)
    """
    s = series.astype(str).str.strip()
    mask = ~s.isin(['', 'nan', 'none'])
    return mask.sum()


sparse_cols = [
    col for col in df.columns
    if count_non_empty(df[col]) <= EMPTY_COL_THRESHOLD
]

print(f"🔍 Колонки с ≤ {EMPTY_COL_THRESHOLD} непустыми значениями:")
if sparse_cols:
    for col in sparse_cols:
        cnt = count_non_empty(df[col])
        print(f"  - {col} ({cnt} знач.)")
else:
    print("  Нет таких колонок.")

if EMPTY_COLS_MODE == 'remove':
    df = df.drop(columns=sparse_cols)
    print(f"🗑️ Удалено {len(sparse_cols)} колонок.")
elif EMPTY_COLS_MODE == 'show':
    print("ℹ️ Колонки оставлены (режим 'show').")


# === 6. Генерация имён файлов и (опционально) скачивание изображений ===
image_filenames = []

print("🖼️ Генерация имён файлов изображений...")
for _, row in df.iterrows():
    img_url = str(row.get("image_src", "")).strip()
    item_id = row["old_id"]
    filename = ""

    if img_url and img_url.lower() not in ("nan", "none", ""):
        # Определяем расширение из URL
        ext = os.path.splitext(urlparse(img_url).path)[-1]
        if not ext or len(ext) > 5 or '.' not in ext:
            ext = ".jpg"
        filename = f"{item_id}{ext}"

        # Скачиваем ТОЛЬКО если включено
        if DOWNLOAD_IMAGES:
            try:
                filepath = os.path.join(IMAGES_DIR, filename)
                if not os.path.exists(filepath):
                    resp = requests.get(img_url, timeout=10)
                    resp.raise_for_status()
                    with open(filepath, "wb") as f:
                        f.write(resp.content)
                time.sleep(0.1)
            except Exception as e:
                print(f"⚠️ Ошибка при скачивании {img_url}: {e}")
                # Имя файла всё равно сохраняем — даже при ошибке
    # Если URL пустой — filename остаётся ""
    image_filenames.append(filename)

df["downloaded_image"] = image_filenames

if DOWNLOAD_IMAGES:
    print(f"📁 Изображения сохранены в: {IMAGES_DIR}/")


# === 7. Генерация отчёта по категориям ===
print("\n📊 Отчёт по категориям после нормализации:")
category_report = {}

for _, row in df.iterrows():
    cat = str(row.get("product_category", "NO_CATEGORY")).strip()
    opt1 = str(row.get("option1_name", "")).strip()
    opt2 = str(row.get("option2_name", "")).strip()

    if cat not in category_report:
        category_report[cat] = {"count": 0, "options": set()}
    category_report[cat]["count"] += 1
    if opt1:
        category_report[cat]["options"].add(opt1)
    if opt2:
        category_report[cat]["options"].add(opt2)

# Выводим отчёт
for cat, info in sorted(category_report.items(), key=lambda x: -x[1]["count"]):
    opts = ", ".join(sorted(info["options"])) if info["options"] else "—"
    print(f"  • {cat} → {info['count']} товаров | Опции: [{opts}]")


# === 8. Сохранение ===
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
print(f"\n✅ Готово! Результат: {OUTPUT_FILE}")
if DOWNLOAD_IMAGES:
    print(f"📁 Изображения сохранены в: {IMAGES_DIR}/")