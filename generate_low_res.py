import os
import json
from PIL import Image
import pandas as pd

# === Configuration ===
BASE_DIR = "H:/Mi unidad/Eras"
OUTPUT_BASE = "H:/Mi unidad/Eras/cartas_LOWRES"
TIMESTAMP_DB = "lowres_timestamps.json"

# === Load Excel ===
df = pd.read_excel("BDD.xlsx", engine="openpyxl")

# === Load timestamp database ===
if os.path.exists(TIMESTAMP_DB):
    with open(TIMESTAMP_DB, "r", encoding="utf-8") as f:
        timestamp_data = json.load(f)
else:
    timestamp_data = {}

def build_original_path(row):
    base = f"{BASE_DIR}/cartas/E{row['era']}"
    class_letter = row['clase'][0] if pd.notna(row['clase']) else "Other"
    
    if class_letter == "B":
        class_folder = "BOSQUEMAGO"
    elif class_letter == "D":
        class_folder = "DISRUPCION"
    elif class_letter == "P":
        class_folder = "PESADILLA"
    elif class_letter == "G":
        class_folder = "GUERRERO"
    else:
        class_folder = "NONE"

    filename = f"E{row['era']}" + (f"_{row['subera']}" if row['subera'] > 0 else "")
    filename += f"-{class_letter}{row['numero']:02d} {row['nombre']}.png"

    original_path = os.path.join(base, class_folder, filename)
    relative_subfolder = os.path.join(f"E{row['era']}", class_folder)
    return original_path, relative_subfolder, filename

updated = 0
skipped = 0

for _, row in df.iterrows():
    try:
        original_path, relative_folder, filename = build_original_path(row)
        output_folder = os.path.join(OUTPUT_BASE, relative_folder)
        output_path = os.path.join(output_folder, filename)

        if not os.path.exists(original_path):
            if original_path[-7:]!='Nac.png':
                print(f'(missing card) {original_path}')
            continue  # skip missing originals

        # Check if image was modified
        mtime = os.path.getmtime(original_path)
        mtime_str = str(mtime)

        if timestamp_data.get(original_path) == mtime_str and os.path.exists(output_path):
            skipped += 1
            print(f'(unchanged) {original_path}')
            continue  # unchanged, skip it

        # Create folders if needed
        os.makedirs(output_folder, exist_ok=True)

        # Resize and save
        img = Image.open(original_path)
        new_size = tuple(int(x * 0.25) for x in img.size)
        img = img.resize(new_size, Image.LANCZOS)
        img.save(output_path, optimize=True)

        # Update timestamp
        timestamp_data[original_path] = mtime_str
        updated += 1
        print(f"Updated: {output_path}")

    except Exception as e:
        print(f"Error processing {filename}: {e}")

# === Save timestamp DB ===
with open(TIMESTAMP_DB, "w", encoding="utf-8") as f:
    json.dump(timestamp_data, f, indent=2)

print(f"\n✅ Done: {updated} updated, {skipped} skipped.")
