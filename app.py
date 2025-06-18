import json
import io

import streamlit as st
import pandas as pd
import os
from PIL import Image
from io import BytesIO
import requests
import tempfile


# Cache helper
def get_cache_path(url):
    import hashlib
    cache_dir = os.path.join(tempfile.gettempdir(), "image_cache")
    os.makedirs(cache_dir, exist_ok=True)
    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(cache_dir, f"{url_hash}.png")


# === Load query params ===
params = st.query_params

# Load Excel
df = pd.read_excel("BDD.xlsx", engine="openpyxl")

df_links = pd.read_excel("uploaded_image_links.xlsx")
df = df.merge(df_links, on="id", how="left")


# === Load saved deck from file ===
DECK_SAVE_FILE = "saved_deck.json"
if "deck" not in st.session_state:
    if os.path.exists(DECK_SAVE_FILE):
        with open(DECK_SAVE_FILE, "r", encoding="utf-8") as f:
            try:
                st.session_state.deck = json.load(f)
            except Exception:
                st.session_state.deck = []
    else:
        st.session_state.deck = []



# Rename columns for consistency
df = df.rename(columns={
    'id': 'card_id',
    'nombre': 'name',
    'era': 'era',
    'subera': 'subera',
    'numero': 'number',
    'clase': 'class',
    'tipos': 'type',
    'categoria': 'category',
    'nivel': 'lvl',
    'fuerza': 'strength',
    'coste': 'cost',
    'coste especial': 'special cost'
})
 
CLASS_MAP = {
    "B": "Bosquemago",
    "D": "Disrupción",
    "G": "Guerrero",
    "P": "Pesadilla"
}


# === Sidebar Controls ===
sets_title = st.sidebar.checkbox("Sets Titles", value=True)

deck_build = st.sidebar.checkbox("Deck builder", value=False)

show_only_deck = False

if deck_build:
    show_only_deck = st.sidebar.checkbox("Only show deck", value=False)

#search_name = st.sidebar.text_input("Search by Name")
search_name = st.sidebar.text_input("Search by Name", value=params.get("search", ""))
st.query_params.search = search_name

# Sidebar Filters
#st.sidebar.title("Filter Cards")

era_default = params.get("era", "1")
era = st.sidebar.selectbox("Era", ["Any"] + sorted(df["era"].unique()), index=0 if era_default == "1" else sorted(df["era"].unique()).index(int(era_default)) + 1)
st.query_params.era = era

subera_options = sorted(df["subera"].unique())
subera = st.sidebar.selectbox("Subera", ["Any"] + list(subera_options))

# Extract and flatten all unique classes
# Reverse mapping for decoding later
REVERSE_CLASS_MAP = {v: k for k, v in CLASS_MAP.items()}

class_series = df["class"].dropna().apply(lambda x: x.split("-"))
all_clase_letters = sorted(set(t for sublist in class_series for t in sublist))
all_clases_readable = [CLASS_MAP.get(cl, cl) for cl in all_clase_letters]

selected_readable_classes = st.sidebar.multiselect("Filter by class(es)", options=all_clases_readable)
selected_classes = [REVERSE_CLASS_MAP.get(c, c) for c in selected_readable_classes]

# Extract and flatten all unique types
type_series = df["type"].dropna().apply(lambda x: x.split("-"))
all_types = sorted(set(t for sublist in type_series for t in sublist))

#selected_types = st.sidebar.multiselect("Filter by type(s)", options=all_types)

# Load from URL
types_param = params.get("types", "")
selected_types_default = types_param.split(",") if types_param else []

# Multiselect input
selected_types = st.sidebar.multiselect("Filter by type(s)", options=all_types, default=selected_types_default)

# Update URL
st.query_params.types = ",".join(selected_types)


# === Show/Hide Names ===
#show_names = st.sidebar.checkbox("Show card names", value=False)
show_names=False

if df["lvl"].dropna().empty:
    lvl = (0, 0)
else:
    lvl = st.sidebar.slider("Level",
        int(df["lvl"].min(skipna=True)),
        int(df["lvl"].max(skipna=True)),
        (int(df["lvl"].min(skipna=True)), int(df["lvl"].max(skipna=True)))
    )

strength = st.sidebar.slider("Strength",
    int(df["strength"].min(skipna=True)),
    int(df["strength"].max(skipna=True)),
    (int(df["strength"].min(skipna=True)), int(df["strength"].max(skipna=True)))
)

cost = st.sidebar.slider("Cost",
    int(df["cost"].min(skipna=True)),
    int(df["cost"].max(skipna=True)),
    (int(df["cost"].min(skipna=True)), int(df["cost"].max(skipna=True)))
)

special_cost = st.sidebar.slider("Special Cost",
    int(df["special cost"].min(skipna=True)),
    int(df["special cost"].max(skipna=True)),
    (int(df["special cost"].min(skipna=True)), int(df["special cost"].max(skipna=True)))
)


# === Zoom Slider ===
#zoom = st.sidebar.slider("Zoom", min_value=50, max_value=550, value=150, step=50)
#card_width_px = zoom  # width of each card in pixels

zoom = int(params.get("zoom", "150"))
zoom = st.sidebar.slider("Zoom", 50, 550, value=zoom, step=50)
st.query_params.zoom = str(zoom)
card_width_px = zoom  # width of each card in pixels


# === Show Deployable info ===
deploy_info = st.sidebar.checkbox("Deployable info", value=False)

# === Show Slots Of Nacs ===
show_empty = st.sidebar.checkbox("Show empty slots", value=False)

# Apply filters

filtered=df.copy()
if era != "Any":
    if subera !="Any":
        filtered = filtered[(df["era"] == era) & (df["subera"] == subera)]
    else:
        filtered = filtered[(df["era"] == era)]


def has_all_classes(card_classes_str, required_classes):
    if not isinstance(card_classes_str, str):
        return False
    card_classes = card_classes_str.split("-")
    return all(t in card_classes for t in required_classes)

# Apply filter
if selected_classes:
    filtered = filtered[filtered["class"].apply(lambda x: has_all_classes(x, selected_classes))]

def has_all_types(card_types_str, required_types):
    if not isinstance(card_types_str, str):
        return False
    card_types = card_types_str.split("-")
    return all(t in card_types for t in required_types)

#################################### Apply filter

if selected_types:
    filtered = filtered[filtered["type"].apply(lambda x: has_all_types(x, selected_types))]

lvl_min = int(df["lvl"].min(skipna=True))
lvl_max = int(df["lvl"].max(skipna=True))

# If user adjusted the slider (i.e. not full range)
if lvl != (lvl_min, lvl_max):
    filtered = filtered[
        (filtered["lvl"].notna()) &
        (filtered["lvl"] >= lvl[0]) &
        (filtered["lvl"] <= lvl[1])
    ]
else:
    # Only filter cards *with levels outside the range*, but keep NaNs
    filtered = filtered[
        (filtered["lvl"].isna()) | (
            (filtered["lvl"] >= lvl[0]) &
            (filtered["lvl"] <= lvl[1])
        )
    ]

# Strength filter (only apply if value is not full range)
strength_min = int(df["strength"].min(skipna=True))
strength_max = int(df["strength"].max(skipna=True))
if strength != (strength_min, strength_max):
    filtered = filtered[
        (filtered["strength"].notna()) &
        (filtered["strength"] >= strength[0]) &
        (filtered["strength"] <= strength[1])
    ]

# Cost filter
cost_min = int(df["cost"].min(skipna=True))
cost_max = int(df["cost"].max(skipna=True))
if cost != (cost_min, cost_max):
    filtered = filtered[
        (filtered["cost"].notna()) &
        (filtered["cost"] >= cost[0]) &
        (filtered["cost"] <= cost[1])
    ]

# Special cost filter
sc_min = int(df["special cost"].min(skipna=True))
sc_max = int(df["special cost"].max(skipna=True))
if special_cost != (sc_min, sc_max):
    filtered = filtered[
        (filtered["special cost"].notna()) &
        (filtered["special cost"] >= special_cost[0]) &
        (filtered["special cost"] <= special_cost[1])
    ]

# Name filter
if search_name:
    filtered = filtered[filtered["name"].str.contains(search_name, case=False, na=False)]


from collections import Counter

# === Setup deck state and functions ===
if "deck" not in st.session_state:
    st.session_state.deck = []


def save_deck():
    with open(DECK_SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.deck, f)

def add_to_deck(card_id):
    count = st.session_state.deck.count(card_id)
    if count < 4:
        st.session_state.deck.append(card_id)
        save_deck()

def remove_from_deck(card_id):
    if card_id in st.session_state.deck:
        st.session_state.deck.remove(card_id)
        save_deck()

def clear_deck():
    st.session_state.deck = []
    save_deck()

def upload_deck(uploaded_deck):
    try:
        imported_deck = json.load(uploaded_deck)
        if isinstance(imported_deck, list) and all(isinstance(x, (int, str)) for x in imported_deck):
            st.session_state.deck = imported_deck
            save_deck()
    except Exception as e:
        st.error(f"Failed to load deck: {e}")

# === Apply deck filter now that checkbox is known ===
if show_only_deck:
    filtered = filtered[filtered["card_id"].isin(st.session_state.deck)]

# === CSS Layout Stretch ===
st.markdown("""
    <style>
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)




# === Centered Header ===
st.markdown(
    f"<h2 style='text-align: center;'>Eras Card Viewer: {len(filtered[filtered['name'] != 'Nac'])} Cards</h2>",
    unsafe_allow_html=True
)



# === Deck Display (Under Header) in Columns ===
if deck_build:
    counts = Counter(st.session_state.deck)

    deck_items = [
        f"×{count} {df[df['card_id'] == card_id].iloc[0]['name']}"
        for card_id, count in counts.items()
        if not df[df["card_id"] == card_id].empty
    ]

    st.markdown(f"### 🧙 Your Deck: {sum(counts.values())} Cards")

    if deck_items:
        # Set number of columns (adjustable)
        n_cols = 8
        cols = st.columns(n_cols)

        for i, item in enumerate(deck_items):
            with cols[i % n_cols]:
                st.markdown(f"- {item}")
    else:
        st.info("Your deck is empty.")


    # === Deck Management Buttons in 2 Columns ===
    col_1, col_2 = st.columns(2)

    with col_1:
        st.button("🗑 Clear Deck", on_click=clear_deck)

        st.download_button(
            label="💾 Export Deck",
            data=json.dumps(st.session_state.deck),
            file_name="my_deck.json",
            mime="application/json"
        )

    with col_2:
        uploaded_deck = st.file_uploader("📥 Import Deck", type=["json"], label_visibility="collapsed")
        if uploaded_deck is not None:
            upload_deck(uploaded_deck)
            


# === Grid Layout Configuration ===
page_width_px = 1000
cards_per_row = max(1, page_width_px // card_width_px)

# === Display Cards with Per-Card Container ===
visible_index = 0
last_era, last_subera, last_class = None, None, None

for _, row in filtered.iterrows():
    if not show_empty and row["name"] == "Nac":
        continue

    current_era = row["era"]
    current_subera = row["subera"]
    current_class = row['class'][0]

    if sets_title and (last_era != current_era or last_subera != current_subera or last_class != current_class):
        subera_label = f".{current_subera}" if current_subera > 0 else ""
        class_label = f" - {CLASS_MAP[current_class]}" if current_class != last_class else ""
        st.markdown(
            f"<h3 style='margin-top: 2rem; border-top: 2px solid #444; padding-top: 0.5rem;'>"
            f"○ Era {current_era}{subera_label}{class_label}</h3>",
            unsafe_allow_html=True
        )
        last_era, last_subera, last_class = current_era, current_subera, current_class
        visible_index = 0

    if visible_index % cards_per_row == 0:
        card_columns = st.columns(cards_per_row)

    with card_columns[visible_index % cards_per_row]:
        with st.container():
            try:
                if row["name"] == "Nac":
                    img_url = "https://res.cloudinary.com/dtwiayh6c/image/upload/v1750276123/cartas/BACKCARD/BACKCARD.png"
                else:
                    img_url = row["url"]

                if pd.notna(img_url):
                    cache_path = get_cache_path(img_url)
                    if os.path.exists(cache_path):
                        img = Image.open(cache_path)
                    else:
                        response = requests.get(img_url)
                        img = Image.open(BytesIO(response.content))
                        img.save(cache_path)

                    st.image(img, use_container_width=True)

                    if show_names:
                        st.markdown(
                            f"<div style='text-align: center; font-weight: bold; height: 80px; overflow: hidden;'>{row['name']}</div>",
                            unsafe_allow_html=True
                        )

                    if deck_build:
                        count = st.session_state.deck.count(row['card_id'])
                        unique_id = f"{row['card_id']}_{visible_index}"

                        col1, col2, col3, col4, col5 = st.columns([0.5, 1, 1, 1, 0.5])

                        with col2:
                            st.button("➖", key=f"remove_{unique_id}",
                                    on_click=remove_from_deck,
                                    args=(row['card_id'],))

                        with col3:
                            st.markdown(
                                f"<div style='text-align: center; font-weight: bold;'>{count}</div>",
                                unsafe_allow_html=True
                            )

                        with col4:
                            st.button("➕", key=f"add_{unique_id}",
                                    on_click=add_to_deck,
                                    args=(row['card_id'],),
                                    disabled=(count >= 4))

                    if deploy_info:
                        with st.expander("📖 Card Details"):
                            st.markdown(f"""
                                **Name**: {row['name']}  
                                **Era**: {int(row['era'])}  
                                **Subera**: {int(row['subera'])}  
                                **Class**: {" - ".join(CLASS_MAP.get(cl, cl) for cl in row['class'].split("-")) if pd.notna(row["class"]) else "-"}  
                                **Type**: {(f"[{row['type'].replace('-', ' | ')}]" if pd.notna(row["type"]) else "[|]") if pd.notna(row["type"]) else "-"}  
                                **Category**: {row['category'] if pd.notna(row["category"]) else "-"}  
                                **Level**: {int(row['lvl']) if pd.notna(row["lvl"]) else "-"}  
                                **Strength**: {int(row['strength']) if pd.notna(row["strength"]) else "-"}  
                                **Cost**: {int(row['cost']) if pd.notna(row["cost"]) else "-"}  
                                **Special Cost**: {int(row['special cost']) if pd.notna(row['special cost']) else "-"}
                            """)
                else:
                    # Fallback for missing image
                    if row['subera'] > 0:
                        card_code = f"E{row['era']}.{row['subera']}-{row['class']}{int(row['number']):02d}"
                    else:
                        card_code = f"E{row['era']}-{row['class']}{int(row['number']):02d}"

                    st.markdown(f"""
                        <div style="
                            width: 100%;
                            aspect-ratio: 189 / 264;
                            background-color: #000;
                            color: red;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            text-align: center;
                            font-weight: bold;
                            border-radius: 8px;
                        ">
                            Missing card:<br>{card_code} {row['name']}
                        </div>
                    """, unsafe_allow_html=True)

                    if show_names:
                        st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
            except Exception as e:
                st.markdown(
                    f"<div style='height: 460px; text-align: center; color: orange;'>Error:<br><b>{row['name']}</b></div>",
                    unsafe_allow_html=True
                )
                print(f"Error showing card {row['card_id']} - {e}")

    visible_index += 1