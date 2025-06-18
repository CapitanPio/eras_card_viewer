import os
import json
from PIL import Image
import pandas as pd
import cloudinary
import cloudinary.uploader

# === Cloudinary Config ===
cloudinary.config(
    cloud_name="dtwiayh6c",
    api_key="328677753374153",
    api_secret="1szVEYgAdHN2UIABoqcXd6q3rqs"
)

# === Configuration ===
BASE_DIR = "H:/Mi unidad/Eras"
OUTPUT_BASE = os.path.join(BASE_DIR, "cartas_LOWRES")
TIMESTAMP_DB = "lowres_timestamps.json"
LINKS_DB = "uploaded_image_links.xlsx"

# === Load Excel ===
df = pd.read_excel("BDD.xlsx", engine="openpyxl")

# === Load timestamp database ===
if os.path.exists(TIMESTAMP_DB):
    with open(TIMESTAMP_DB, "r", encoding="utf-8") as f:
        timestamp_data = json.load(f)
else:
    timestamp_data = {}

# === Load previous image links ===
if os.path.exists(LINKS_DB):
    previous_links = pd.read_excel(LINKS_DB)
    id_to_url = dict(zip(previous_links["id"], previous_links["url"]))
else:
    id_to_url = {}

# === Path builder ===
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
upload_log = []

# === Upload Cards ===
for _, row in df.iterrows():
    try:
        card_id = int(row["id"])
        original_path, relative_folder, filename = build_original_path(row)
        output_folder = os.path.join(OUTPUT_BASE, relative_folder)
        output_path = os.path.join(output_folder, filename)

        if not os.path.exists(original_path):
            print(f"(missing) {original_path}")
            upload_log.append({"id": card_id, "url": id_to_url.get(card_id, None)})
            continue

        mtime = os.path.getmtime(original_path)
        mtime_str = str(mtime)

        if timestamp_data.get(original_path) == mtime_str and os.path.exists(output_path):
            # Image unchanged — reuse old URL
            skipped += 1
            print(f"(unchanged) {original_path}")
            upload_log.append({"id": card_id, "url": id_to_url.get(card_id, None)})
            continue

        os.makedirs(output_folder, exist_ok=True)

        img = Image.open(original_path)
        new_size = tuple(int(x * 0.15) for x in img.size)
        img = img.resize(new_size, Image.LANCZOS)
        img.save(output_path, optimize=True)

        cloudinary_folder = relative_folder.replace("\\", "/")
        public_id = f"{cloudinary_folder}/{filename[:-4]}"

        upload_result = cloudinary.uploader.upload(
            output_path,
            public_id=public_id,
            overwrite=True,
            folder=None
        )

        cloud_url = upload_result["secure_url"]
        print(f"Uploaded: {cloud_url}")

        upload_log.append({"id": card_id, "url": cloud_url})
        timestamp_data[original_path] = mtime_str
        updated += 1

    except Exception as e:
        print(f"Error: {e}")
        upload_log.append({"id": card_id, "url": id_to_url.get(card_id, None)})

# === Upload BACKCARD ===
try:
    backcard_path = os.path.join(BASE_DIR, "cartas", "BACKCARD", "BACKCARD.png")
    backcard_lowres = os.path.join(OUTPUT_BASE, "BACKCARD", "BACKCARD.png")

    if os.path.exists(backcard_path):
        os.makedirs(os.path.dirname(backcard_lowres), exist_ok=True)

        mtime = os.path.getmtime(backcard_path)
        mtime_str = str(mtime)

        if timestamp_data.get(backcard_path) != mtime_str or not os.path.exists(backcard_lowres):
            img = Image.open(backcard_path)
            new_size = tuple(int(x * 0.25) for x in img.size)
            img = img.resize(new_size, Image.LANCZOS)
            img.save(backcard_lowres, optimize=True)

            upload_result = cloudinary.uploader.upload(
                backcard_lowres,
                public_id="cartas/BACKCARD/BACKCARD",
                overwrite=True,
                folder=None
            )
            print(f"Uploaded BACKCARD to: {upload_result['secure_url']}")
            timestamp_data[backcard_path] = mtime_str
        else:
            print("(unchanged) BACKCARD")
    else:
        print("❌ BACKCARD not found")

except Exception as e:
    print(f"Error uploading BACKCARD: {e}")

# === Save Results ===
with open(TIMESTAMP_DB, "w", encoding="utf-8") as f:
    json.dump(timestamp_data, f, indent=2)

pd.DataFrame(upload_log).to_excel(LINKS_DB, index=False)
print(f"\n📝 Updated: {updated}, Skipped: {skipped}")
print(f"📄 Saved: {LINKS_DB}")
