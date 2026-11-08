"""Data-driven facade styles for walls without a hand annotation (city-wide baseline).

    import facade_styles as S
    ann = S.layout(wall)          # -> annotation wall dict (data/annotations/market_square/SCHEMA.md)
    P = facade_parts.wall_facade(wall["length"], wall["eave_z"] - wall["ground_z"], ann)

`wall` is a walls.json-like dict: id, osm_id, tags (OSM building tags), length, ground_z, eave_z, height, optional
colour_hint ("#rrggbb" measured mean wall colour) and dist_centre (m from Market Square).

The style is inferred per building (deterministic: md5 of osm_id), the layout per wall:
  1. classify(tags, wall) -> style key from building / amenity / operator (college) / name / start_date /
     historic / listed_status / addr:street (calibrated on the Cambridge OSM extract: 5.1k buildings, mostly
     house/yes/university/terrace with few dates; ~1.2k carry a college or university operator).
  2. palette(style) -> material, wall and trim colour; colour_hint (if present) snaps the material
     (reddish -> red brick, pale yellow-grey -> gault brick or ashlar, white -> render, dark grey -> glass/render)
     and drives the wall colour.
  3. per-style generator: storeys from building:levels or height/3.1, bays 2.8-3.2 m (window count like
     facade_parts.default_layout), shopfront ground floor with the OSM name on the fascia for shops/amenities.
All elements stay inside 0..length and below the eave; no dormers (the roof is not known per wall).
"""
import hashlib
import re

STYLES = ("chapel", "college_gothic", "college_tudor", "college_classical", "college_modern", "institutional",
          "georgian", "victorian", "terrace", "villa", "interwar", "modern", "glass", "vernacular", "outbuilding",
          "canopy")

# ------------------------------------------------------------------ colours (Cambridge, cf. the Market Square annotations)
KETTON = "#cdbd96"       # Ketton / Clipsham / Weldon buff limestone ashlar
ASHLAR_PALE = "#d8d0bd"  # weathered Portland-ish ashlar (Senate House, Market Square annotations)
CLUNCH = "#c4b99c"       # church rubble / clunch
GAULT = "#d8ceb0"        # Cambridge "white" gault brick
GAULT_DIRTY = "#bdb08f"  # sooted gault (common in the centre)
RED_BRICK = "#9a4a35"
RED_DARK = "#8a4a33"
TUDOR_BRICK = "#94513b"
RENDER_WHITE = "#eeeae0"
RENDER_CREAM = "#ebe3cf"
STUCCO = "#f1ede2"

PAL = {   # style -> list of (material, wall, trim) options; picked by hash
    "chapel": [("stone", CLUNCH, "#d6ccb2"), ("stone", KETTON, "#ddd0ad"), ("stone", ASHLAR_PALE, "#e4ddcb")],
    "college_gothic": [("stone", KETTON, "#ddd0ad"), ("stone", ASHLAR_PALE, "#e4ddcb"), ("stone", "#c9b58e", "#d9c9a3"),
                       ("brick", GAULT, "#d9cfb2")],
    "college_tudor": [("brick", TUDOR_BRICK, "#d8c8a2"), ("brick", RED_BRICK, "#d8d0bd"), ("brick", "#a5553a", "#d9c49a")],
    "college_classical": [("stone", KETTON, "#e0d4b4"), ("stone", ASHLAR_PALE, "#ece6d8"), ("brick", GAULT, "#e4dcc6")],
    "college_modern": [("brick", "#a8754f", "#d0cdc6"), ("brick", "#b9a27a", "#d0cdc6"), ("render", RENDER_WHITE, "#8a8d90"),
                       ("stone", "#d9cba7", "#c8c4bc"), ("brick", "#8f5a44", "#3a3d40")],
    "institutional": [("brick", RED_BRICK, "#d8c8a2"), ("brick", RED_DARK, "#d9c49a"), ("stone", "#d4c7a6", "#e2d8bf"),
                      ("brick", GAULT_DIRTY, "#ece6d8")],
    "georgian": [("brick", GAULT, "#efe9dc"), ("brick", GAULT_DIRTY, "#ece8dd"), ("stucco", STUCCO, "#ffffff"),
                 ("brick", RED_BRICK, "#efeae0"), ("render", RENDER_CREAM, "#f7f5ef"), ("brick", "#b8a27a", "#efe9dc")],
    "victorian": [("brick", GAULT, "#ece6d8"), ("brick", GAULT_DIRTY, "#ece6d8"), ("brick", RED_BRICK, "#e6dcc6"),
                  ("brick", "#a2513a", "#e6dcc8"), ("render", RENDER_WHITE, "#f7f5ef")],
    "terrace": [("brick", GAULT, "#ece6d8"), ("brick", GAULT, "#ece6d8"), ("brick", "#cfc3a0", "#efe9dc"),
                ("brick", GAULT_DIRTY, "#ece6d8"), ("brick", RED_BRICK, "#e6dcc6"), ("render", RENDER_WHITE, "#f7f5ef")],
    "villa": [("brick", RED_BRICK, "#efe9dc"), ("brick", "#a5553a", "#efe9dc"), ("brick", GAULT, "#efe9dc"),
              ("render", RENDER_CREAM, "#ffffff")],
    "interwar": [("brick", "#9c5f45", "#efe9dc"), ("brick", "#8f5a44", "#efe9dc"), ("render", RENDER_CREAM, "#ffffff")],
    "modern": [("render", RENDER_WHITE, "#8a8d90"), ("brick", "#b9a27a", "#4a4d50"), ("brick", "#8f5a44", "#4a4d50"),
               ("render", "#d9d6cf", "#5a5d60"), ("stone", "#d9cba7", "#8a8d90")],
    "glass": [("glass", "#56606a", "#3a3d40"), ("render", "#e4e2dc", "#3a3d40")],
    "vernacular": [("render", RENDER_CREAM, "#f7f5ef"), ("render", "#e8dcc0", "#f7f5ef"), ("render", "#dcc8a0", "#f2efe8"),
                   ("render", "#e2c9bd", "#f2efe8"), ("timber", "#e9e2cf", "#4a3a2c")],
    "outbuilding": [("brick", "#8f6a50", "#d8d2c4"), ("brick", GAULT_DIRTY, "#d8d2c4"), ("render", "#d9d6cf", "#d8d2c4")],
    "canopy": [("render", "#d9d6cf", "#d8d2c4")],
}

# ------------------------------------------------------------------ calibration tables
COLLEGE = {   # operator / name key -> college style family
    "downing": "college_classical", "emmanuel": "college_classical", "clare college": "college_classical",
    "christ's": "college_classical", "trinity hall": "college_gothic", "king's": "college_gothic",
    "peterhouse": "college_gothic", "corpus christi": "college_gothic", "gonville": "college_gothic",
    "caius": "college_gothic", "pembroke": "college_gothic", "trinity college": "college_gothic",
    "st john's": "college_tudor", "queens'": "college_tudor", "jesus": "college_tudor", "magdalene": "college_tudor",
    "st catharine's": "college_tudor", "selwyn": "college_tudor", "newnham": "college_tudor", "sidney sussex": "college_gothic",
    "hughes hall": "victorian", "westcott house": "college_tudor", "ridley hall": "college_tudor", "wesley house": "college_tudor",
    "darwin": "college_modern", "churchill": "college_modern", "robinson": "college_modern", "fitzwilliam college": "college_modern",
    "murray edwards": "college_modern", "lucy cavendish": "college_modern", "clare hall": "college_modern",
    "st edmund's": "college_modern", "wolfson": "college_modern", "anglia ruskin": "modern",
}
# named courts and university sites (OSM amenity=university grounds), checked before COLLEGE: modern courts of old
# colleges, and the central university sites (session 36)
COURT = {"blue boar court": "college_modern", "burrell's field": "college_modern", "cripps court": "college_modern",
         "harvey court": "college_modern", "wolfson court": "college_modern", "cosin court": "college_modern",
         "castle court": "college_modern", "the old schools": "college_classical", "cambridge union": "institutional",
         "new museums site": "institutional", "downing site": "institutional", "scroope terrace": "georgian",
         "silver street & mill lane": "institutional", "centre for mathematical": "college_modern",
         "department of engineering": "institutional", "sidgwick site": "college_modern", "cambridge west": "modern"}
_GROUNDS = None


def grounds_name(wall):
    """Name of the OSM college / university grounds (amenity=college|university way) containing the wall's midpoint,
    '' if none (the smallest containing polygon wins: courts lie inside their college)."""
    global _GROUNDS
    if not wall or "p0" not in wall:
        return ""
    if _GROUNDS is None:
        import json
        import os
        from pyproj import Transformer
        from shapely.geometry import Point, Polygon
        from shapely.strtree import STRtree
        import build as B
        els = json.load(open(B.RAW))["elements"]
        tr = Transformer.from_crs(4326, 27700, always_xy=True)
        nd = {e["id"]: (e["lon"], e["lat"]) for e in els if e["type"] == "node"}
        polys, names = [], []
        for e in els:
            t = e.get("tags", {})
            if e["type"] == "way" and t.get("amenity") in ("college", "university") and len(e["nodes"]) >= 4:
                ll = [nd[n] for n in e["nodes"] if n in nd]
                E, N = tr.transform([q[0] for q in ll], [q[1] for q in ll])
                pg = Polygon([(x - B.E0, y - B.N0) for x, y in zip(E, N)]).buffer(0)
                if pg.area > 50:
                    polys.append(pg)
                    names.append(t.get("name", ""))
        _GROUNDS = (STRtree(polys), polys, names, Point)
    tree, polys, names, Point = _GROUNDS
    q = Point((wall["p0"][0] + wall["p1"][0]) / 2, (wall["p0"][1] + wall["p1"][1]) / 2)
    hits = [i for i in tree.query(q.buffer(1.0)) if polys[i].distance(q) < 1.0]
    return names[min(hits, key=lambda i: polys[i].area)] if hits else ""
# streets: historic core (Georgian/older fronts, mixed with shops), Georgian/Regency gault terraces,
# Victorian/Edwardian terrace suburbs (Mill Road, Romsey, De Freville, Chesterton), Edwardian villas (west Cambridge),
# post-war estates. Matched case-insensitively against addr:street.
CORE = {"trumpington street", "king's parade", "trinity street", "st john's street", "bridge street", "sidney street",
        "st andrew's street", "market hill", "market square", "peas hill", "bene't street", "petty cury", "green street",
        "magdalene street", "rose crescent", "market street", "hobson street", "jesus lane", "thompson's lane",
        "portugal place", "quayside", "silver street", "mill lane", "pembroke street", "free school lane",
        "botolph lane", "corn exchange street", "wheeler street", "regent street", "castle street", "northampton street",
        "all saints passage", "round church street", "park street", "king street", "fair street", "emmanuel street",
        "downing street", "st edward's passage", "trinity lane", "senate house passage", "post office terrace"}
GEORGIAN_ST = {"fitzwilliam street", "park terrace", "parker's piece", "regent terrace", "maids causeway",
               "new square", "brookside", "malcolm street", "park parade", "portugal place", "park side", "parkside",
               "lensfield road", "trumpington road", "bateman street", "panton street", "emmanuel road", "willow walk",
               "orchard street", "warkworth terrace", "warkworth street", "fitzroy street", "clarendon street",
               "earl street", "victoria street", "short street", "melbourne place", "city road", "brunswick walk"}
TERRACE_ST = {"kimberley road", "humberstone road", "de freville avenue", "searle street", "mill road", "pretoria road",
              "lyndewode road", "victoria road", "alpha road", "belvoir road", "chedworth street", "edward street",
              "young street", "glisson road", "tenison road", "tenison avenue", "aylestone road", "chesterton road",
              "abbey road", "ferry path", "hertford street", "carlyle road", "st luke's street", "mawson road",
              "gwydir street", "devonshire road", "harvey road", "st barnabas road", "sturton street", "norfolk street",
              "great eastern street", "lichfield road", "argyle street", "thoday street", "catharine street",
              "mackenzie road", "hooper street", "ainsworth street", "kingston street", "eden street",
              "new street", "petersfield", "york street", "milford street", "cavendish road", "coleridge road",
              "hills road", "station road", "bateman street", "norwich street", "union road", "russell street",
              "newnham road", "newnham walk", "grantchester street", "derby street", "chesterton lane",
              "beche road", "alpha terrace", "garden walk", "pound hill", "shelly row", "magrath street"}
VILLA_ST = {"grange road", "millington road", "barton road", "selwyn gardens", "sylvester road", "herschel road",
            "adams road", "madingley road", "west road", "storey's way", "huntingdon road", "chaucer road",
            "latham road", "brooklands avenue", "bentley road", "luard road", "clarkson road", "wilberforce road",
            "conduit head road", "grange gardens", "cranmer road", "newnham terrace", "fulbrooke road", "barrow road"}
MODERN_ST = {"acrefield drive", "ravensworth gardens", "manhattan drive", "montague lodge", "longworth avenue",
             "elizabeth way", "magrath avenue", "eden street backway", "cutlers court", "lion yard", "grand arcade",
             "christ's lane", "the grafton", "fitzroy lane", "salmon lane", "james street", "hanover court",
             "elm court", "dover street", "auckland road", "cam road"}
INTERWAR_ST = {"elizabeth way", "milton road", "highworth avenue", "hawthorn way", "gilbert road", "chesterton hall crescent"}

FASCIA = {   # brand/name fragment -> (fascia, text)
    "boots": ("#05357b", "#ffffff"), "sainsbury": ("#f06c00", "#ffffff"), "tesco": ("#ffffff", "#00539f"),
    "co-op": ("#00b1e7", "#ffffff"), "pret": ("#862633", "#ffffff"), "costa": ("#7b1d2e", "#ffffff"),
    "starbucks": ("#00704a", "#ffffff"), "greggs": ("#00548f", "#fcb715"), "waterstones": ("#1b1b1b", "#ffffff"),
    "marks & spencer": ("#e9e5da", "#1b1b1b"), "barclays": ("#00aeef", "#ffffff"), "hsbc": ("#ffffff", "#db0011"),
    "lloyds": ("#006a4d", "#ffffff"), "natwest": ("#5a287d", "#ffffff"), "santander": ("#ec0000", "#ffffff"),
    "nationwide": ("#1f2a5c", "#ffffff"), "halifax": ("#1d3f8f", "#ffffff"), "mcdonald": ("#da291c", "#ffc72c"),
    "superdrug": ("#e5007e", "#ffffff"), "whsmith": ("#1d3c8f", "#ffffff"), "timpson": ("#c8102e", "#ffffff"),
    "oxfam": ("#61a534", "#ffffff"), "fitzbillies": ("#1b1b1b", "#e6c35a"), "heffers": ("#14325c", "#ffffff"),
    "ryman": ("#d7182a", "#ffffff"), "post office": ("#e60000", "#ffd400"), "subway": ("#008c15", "#ffc20e"),
    "wagamama": ("#1b1b1b", "#ffffff"), "nando": ("#1b1b1b", "#ffffff"), "zizzi": ("#2b2b2b", "#e6dcc8"),
    "pizza express": ("#1b1b1b", "#ffffff"), "caffe nero": ("#1b1b1b", "#ffffff"), "the body shop": ("#14503a", "#ffffff"),
}
FASCIA_PUB = [("#1f3a30", "#e6d6a8"), ("#5a1f22", "#e6d6a8"), ("#1b1b1b", "#d9c27a"), ("#22324a", "#e6d6a8")]
FASCIA_SHOP = [("#1f3a30", "#e8d9a0"), ("#2b2f3a", "#ffffff"), ("#5a1f22", "#e9e4d6"), ("#30302e", "#e6dcc8"),
               ("#f2f0ea", "#2b3a55"), ("#e6e0d2", "#3a3a3a"), ("#14325c", "#ffffff"), ("#1b1b1b", "#c9a85a"),
               ("#6a7a5a", "#ffffff"), ("#8a2a2a", "#ffffff")]
SHOP_AMENITY = {"restaurant", "cafe", "pub", "bar", "fast_food", "pharmacy", "bank", "bureau_de_change", "ice_cream",
                "post_office", "dentist", "doctors", "veterinary", "theatre", "cinema", "library", "nightclub",
                "estate_agent", "betting", "community_centre"}
OUTBUILDING = {"garage", "garages", "shed", "service", "industrial", "construction", "parking", "carport", "hut",
               "greenhouse", "transformer_tower", "warehouse", "storage_tank", "boathouse", "kiosk", "toilets"}


def _h(osm_id, salt=""):
    return int(hashlib.md5((str(osm_id) + salt).encode()).hexdigest()[:8], 16)


def _pick(seq, osm_id, salt):
    return seq[_h(osm_id, salt) % len(seq)]


def _year(tags):
    for k in ("start_date", "building:start_date", "construction_date"):
        m = re.search(r"(\d{4})", str(tags.get(k, "")))
        if m:
            return int(m.group(1))
        m = re.search(r"C(\d{2})", str(tags.get(k, "")))   # "C18" / "early C19"
        if m:
            return (int(m.group(1)) - 1) * 100 + 50
    return None


def _num(v, default=None):
    try:
        return float(str(v).split(";")[0])
    except (TypeError, ValueError):
        return default


def _hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _rgb2hex(c):
    return "#%02x%02x%02x" % tuple(int(round(max(0.0, min(1.0, v)) * 255)) for v in c)


def _mix(a, b, t):
    """t of a + (1 - t) of b (hex colours)."""
    A, Bc = _hex2rgb(a), _hex2rgb(b)
    return _rgb2hex([t * x + (1 - t) * y for x, y in zip(A, Bc)])


def _street(tags):
    return str(tags.get("addr:street", "")).strip().lower()


def _is_college(tags):
    b, a = tags.get("building"), tags.get("amenity")
    op = str(tags.get("operator", "")).lower()
    name = str(tags.get("name", ""))
    return (b in ("college", "university", "dormitory") or a in ("college", "university")
            or "College" in name or "college" in op or "hall (university" in op or op.startswith("peterhouse")
            or "university of cambridge" in op)


def _college_family(tags):
    s = (str(tags.get("operator", "")) + " | " + str(tags.get("name", ""))).lower()
    for k, v in COURT.items():
        if k in s:
            return v
    for k, v in COLLEGE.items():
        if k in s:
            return v
    return None


def classify(tags, wall=None):
    """Style key (see STYLES) for a building's OSM tags."""
    wall = wall or {}
    b = tags.get("building", "yes")
    a = tags.get("amenity", "")
    name = str(tags.get("name", ""))
    lname = name.lower()
    oid = wall.get("osm_id", tags.get("name", ""))
    yr = _year(tags)
    lv = _num(tags.get("building:levels"))
    st = _street(tags)
    dist = wall.get("dist_centre")
    listed = bool(tags.get("listed_status") or tags.get("heritage") or tags.get("historic") or tags.get("HE_ref"))
    r = _h(oid, "cls") % 100

    if b == "roof":
        return "canopy"
    if b in OUTBUILDING:
        return "outbuilding"
    if (b in ("church", "chapel", "cathedral", "chapel;yes") or a == "place_of_worship"
            or re.search(r"\bchapel\b|\bchurch\b|\bst\.? \w+'?s? church\b", lname)) and "lane" not in lname:
        if yr and yr >= 1950:
            return "modern"
        return "chapel"
    if yr is not None:   # an explicit date wins
        if yr < 1550 and (_is_college(tags) or listed):
            return "college_gothic"
        if yr < 1700:
            return "college_tudor" if _is_college(tags) else "vernacular"
        if yr < 1840:
            return "college_classical" if _is_college(tags) and r < 60 else "georgian"
        if yr < 1914:
            if _is_college(tags):
                return _college_family(tags) or "college_gothic"
            return "terrace" if b in ("terrace", "house") and tags.get("house") == "terraced" else "victorian"
        if yr < 1950:
            return "interwar"
        return "glass" if b in ("office", "commercial") and r < 40 else ("college_modern" if _is_college(tags) else "modern")

    if st in MODERN_ST:
        return "modern"
    gname = grounds_name(wall) if _college_family(tags) is None else ""
    if gname and b in ("yes", "university", "college", "dormitory", "residential", "house", "apartments", "school"):
        tags = dict(tags, operator=(str(tags.get("operator", "")) + " | " + gname).strip(" |"))
    if _is_college(tags):
        fam = _college_family(tags)
        op = str(tags.get("operator", "")).lower()
        if fam is None and ("university of cambridge" == op or b == "university"):
            # departments: Edwardian Downing-site / New Museums labs, or post-war (Sidgwick, West Cambridge)
            if (lv or 0) >= 5 or (dist is not None and dist > 1500):
                return "modern"
            return "institutional" if r < 55 else "modern"
        fam = fam or "college_gothic"
        if fam in ("college_gothic", "college_tudor", "college_classical") and r < 18 and (dist is None or dist > 300):
            fam = "college_modern" if r < 9 else "institutional"   # every old college has some 19th/20th c. ranges
        return fam

    if b in ("office", "commercial", "retail", "supermarket", "hotel") and (lv or 0) >= 5:
        return "glass" if r < 50 else "modern"
    if b in ("public", "civic", "government", "courthouse", "museum", "townhall", "bank"):
        return "college_classical" if r < 50 else "institutional"
    in_core = st in CORE or (dist is not None and dist < 350)
    if in_core:
        if b in ("retail", "commercial", "office") and r < 25:
            return "modern"
        return "vernacular" if r < 15 else ("georgian" if r < 70 else "victorian")
    if st in GEORGIAN_ST or listed:
        return "georgian" if r < 80 else "victorian"
    if b in ("public", "civic", "government", "courthouse", "museum", "townhall", "bank"):
        return "college_classical" if r < 50 else "institutional"
    if b in ("school", "hospital", "kindergarten", "train_station", "transportation"):
        return "institutional" if r < 60 else "modern"
    if b in ("terrace",) or tags.get("house") in ("terraced", "back-to-back") or st in TERRACE_ST:
        if b in ("apartments", "retail", "commercial", "office") and r < 50:
            return "modern"
        return "terrace" if b in ("terrace", "house", "residential", "yes") else "victorian"
    if st in VILLA_ST or b in ("detached", "semidetached_house", "villa"):
        return "villa" if r < 75 else "interwar"
    if st in INTERWAR_ST:
        return "interwar"
    if b in ("apartments", "dormitory"):
        return "modern" if (lv or 0) >= 4 or r < 45 else "victorian"
    if b in ("retail", "commercial", "office", "supermarket", "hotel"):
        return "modern" if r < 55 or wall.get("length", 0) > 25 else "victorian"
    if b == "house":
        return "terrace" if r < 45 else ("villa" if r < 75 else "interwar")
    # building=yes / residential / other
    return "victorian" if r < 55 else ("terrace" if r < 70 else ("modern" if r < 88 else "interwar"))


def _snap(hint, mat, wall_c, style):
    """Material + wall colour from a measured mean wall colour."""
    try:
        r, g, b = _hex2rgb(hint)
    except Exception:
        return mat, wall_c
    mean, sat = (r + g + b) / 3, max(r, g, b) - min(r, g, b)
    stoneish = style in ("chapel", "college_gothic", "college_classical") or mat == "stone"
    if mean > 0.80 and sat < 0.12:
        m, canon = ("stucco" if style == "georgian" else "render"), RENDER_WHITE
    elif r - b > 0.17 and mean < 0.72 and r > g:
        m, canon = "brick", RED_BRICK
    elif mean < 0.36 and sat < 0.08 and style in ("modern", "glass", "college_modern"):
        m, canon = "glass", "#56606a"
    elif mean < 0.36:   # shadowed photos: keep the style material, darken towards it
        return mat, _mix(hint, wall_c, 0.35)
    elif r >= b - 0.02:   # pale yellow-grey / buff
        m, canon = ("stone", KETTON) if stoneish else ("brick", GAULT)
    else:   # bluish grey: render / concrete
        m, canon = ("render" if mat not in ("stone", "glass") else mat), "#d9d6cf"
    return m, _mix(hint, canon, 0.7)


def _storeys(H, tags, style):
    lv = _num(tags.get("building:levels"))
    if style in ("chapel", "canopy"):
        return 1
    if style == "outbuilding":
        return max(1, min(2, int(H / 2.6)))
    lo = 2.6 if style not in ("georgian", "college_classical", "institutional", "glass") else 2.9
    if lv and lv >= 1 and lo <= H / round(lv) <= 5.0:
        n = int(round(lv))
    else:   # old college ranges and public buildings have taller storeys than houses (session 36)
        n = max(1, round(H / (3.9 if style in ("college_gothic", "college_tudor", "college_classical", "institutional")
                              else 3.1)))
    return max(1, min(n, int(H / 2.5) or 1))


def _floors(H, n, tall_ground):
    if n == 1:
        return [0.0]
    g = min(4.4, max(3.4, H / n * 1.2)) if tall_ground else H / n
    g = min(g, H - (n - 1) * 2.5)
    rest = (H - g) / (n - 1)
    return [0.0] + [round(g + rest * k, 2) for k in range(n - 1)]


def _bays(L, bay, margin=0.3):
    nb = max(1, int(round((L - 2 * margin) / bay)))
    bw = (L - 2 * margin) / nb
    return [margin + bw * (i + 0.5) for i in range(nb)], bw


def _shop_info(tags, oid):
    name = tags.get("name") or tags.get("brand") or ""
    a = tags.get("amenity", "")
    lname = str(name).lower()
    for k, (f, t) in FASCIA.items():
        if k in lname or k in str(tags.get("brand", "")).lower():
            return name, f, t
    if a in ("pub", "bar") or tags.get("building") == "pub":
        f, t = _pick(FASCIA_PUB, oid, "fascia")
    else:
        f, t = _pick(FASCIA_SHOP, oid, "fascia")
    return name, f, t


def _has_shop(tags, L, style):
    if L < 3.0 or style in ("chapel", "outbuilding", "canopy"):
        return False
    b, a = tags.get("building"), tags.get("amenity", "")
    if "shop" in tags and tags.get("shop") != "no":
        return True
    if a in SHOP_AMENITY and a not in ("library", "theatre", "community_centre", "doctors", "dentist"):
        return True
    if b in ("retail", "pub", "kiosk"):
        return True
    return b in ("commercial",) and style in ("georgian", "victorian", "vernacular", "modern")


def layout(wall):
    """Annotation wall dict (SCHEMA.md) for an un-annotated wall."""
    L = float(wall["length"])
    H = float(wall.get("eave_z", 0) - wall.get("ground_z", 0)) if "eave_z" in wall else float(wall.get("height", 6))
    tags = wall.get("tags", {}) or {}
    oid = wall.get("osm_id", wall.get("id", ""))
    wid = wall.get("id", oid)
    style = classify(tags, wall)
    mat, wc, tc = _pick(PAL[style], oid, "pal")
    if tags.get("building:material") in ("brick", "stone", "render", "stucco", "timber", "glass", "flint", "concrete"):
        mat = {"concrete": "render"}.get(tags["building:material"], tags["building:material"])
    if re.fullmatch(r"#[0-9a-fA-F]{6}", str(tags.get("building:colour", ""))):
        wc = tags["building:colour"]
    if wall.get("colour_hint"):
        mat, wc = _snap(wall["colour_hint"], mat, wc, style)
    hw = _h(wid, "wall")
    ann = {"id": wid, "style": style, "material": mat, "wall_colour": wc, "trim_colour": tc, "cornice": "none",
           "parapet": False, "string_courses": [], "quoins": False, "pilasters": [], "elements": [],
           "confidence": "low", "notes": "facade_styles.layout: inferred from OSM tags (%s)" % style}
    if L < 2.0 or H < 2.5 or style == "canopy":
        ann["storeys"], ann["floor_z"] = 1, [0.0]
        return ann

    shop = _has_shop(tags, L, style)
    n = _storeys(H, tags, style)
    fz = _floors(H, n, shop or style in ("georgian", "institutional", "college_classical"))
    ann["storeys"], ann["floor_z"] = n, fz
    tops = fz[1:] + [H]
    E = ann["elements"]

    def add_win(x, w, z, h, st, panes, head="flat", sill=True, **kw):
        if h < 0.7 or z + h > H - 0.25 or x - w / 2 < 0.2 or x + w / 2 > L - 0.2:
            return
        if head == "pointed" and h < w * 0.87 + 0.25:
            head = "flat"
        if head == "arched" and h < w / 2 + 0.25:
            head = "flat"
        E.append(dict({"type": "window", "style": st, "x": round(x, 2), "w": round(w, 2), "z": round(z, 2),
                       "h": round(h, 2), "panes": panes, "head": head, "sill": sill}, **kw))

    def add_door(x, w, h, st="panelled", surround="none", colour=None):
        if x - w / 2 < 0.25 or x + w / 2 > L - 0.25 or h > min(fz[1] if n > 1 else H, H) - 0.5:
            return False
        d = {"type": "door", "style": st, "x": round(x, 2), "w": w, "h": round(h, 2), "surround": surround}
        if colour:
            d["colour"] = colour
        E.append(d)
        return True

    # ---------------------------------------------------------- shopfront ground floor
    door_done = False
    if shop:
        name, fcol, tcol = _shop_info(tags, oid)
        z1 = min(fz[1] - 0.2 if n > 1 else H - 0.4, 4.2)
        units = max(1, round(L / 7.0))
        uw = L / units
        for u in range(units):
            a, b = u * uw + 0.2, (u + 1) * uw - 0.2
            if b - a < 1.6:
                continue
            sf = {"type": "shopfront", "x0": round(a, 2), "x1": round(b, 2), "z1": round(z1, 2),
                  "door_x": round(a + 0.9 if (hw + u) % 2 == 0 else b - 0.9, 2), "stallriser": 0.45 if style != "glass" else 0.1,
                  "fascia_colour": fcol, "text_colour": tcol, "awning": False}
            if name and u == 0:
                sf["fascia_text"] = name
            E.append(sf)
        door_done = True

    # ---------------------------------------------------------- per style
    if style == "chapel":
        ann.update(cornice="simple", parapet=True)
        xs, bw = _bays(L, 3.6, 0.6)
        w = min(1.8, bw * 0.5)
        z0 = min(2.2, H * 0.25)
        h = min(H - z0 - 1.0, 8.0)
        for x in xs:
            add_win(x, w, z0, h, "gothic", [3 if w > 1.4 else 2, max(2, min(6, int(h / 1.3)))], "pointed")
        ann["pilasters"] = [round(xs[0] - bw / 2 + bw * i, 2) for i in range(1, len(xs))]   # buttresses
        if L > 6 and hw % 3 == 0 and len(xs) % 2 == 0:   # door between the two middle bays, under no window
            add_door(L / 2, 1.4, min(3.0, H - 1.5), "gothic")
        return ann

    if style == "outbuilding":
        ann.update(cornice="none")
        if L > 3.5 and tags.get("building") in ("garage", "garages"):
            k = max(1, int(L / 3.0))
            for i in range(k):
                add_door(L * (i + 0.5) / k, 2.3, min(2.1, H - 0.4), "panelled", colour="#6b6f72")
        elif L > 3.0:
            add_door(L * (0.25 if hw % 2 else 0.75), 0.9, min(2.1, H - 0.4), "panelled")
            if L > 5:
                add_win(L * (0.7 if hw % 2 else 0.3), 1.0, 1.0, min(1.0, H - 1.4), "casement", [2, 1])
        return ann

    # window vocabulary per style
    S = {
        "college_gothic": dict(bay=3.4, st="gothic", head="pointed", w=1.25, h=1.8, panes=[2, 3], top_h=1.4),
        "college_tudor": dict(bay=3.0, st="casement", head="flat", w=1.35, h=1.5, panes=[2, 2], top_h=1.2),
        "college_classical": dict(bay=3.0, st="sash_georgian", head="flat", w=1.1, h=1.9, panes=[3, 3], top_h=1.4),
        "college_modern": dict(bay=3.0, st="modern", head="flat", w=1.9, h=1.7, panes=[2, 1], top_h=1.7),
        "institutional": dict(bay=3.0, st="casement", head="flat", w=1.45, h=2.0, panes=[3, 3], top_h=1.6),
        "georgian": dict(bay=2.9, st="sash_georgian", head="flat", w=1.05, h=1.8, panes=[3, 3], top_h=1.3),
        "victorian": dict(bay=2.9, st="sash_victorian", head="flat", w=1.0, h=1.7, panes=[1, 2], top_h=1.4),
        "terrace": dict(bay=2.8, st="sash_victorian", head="flat", w=0.95, h=1.6, panes=[1, 2], top_h=1.3),
        "villa": dict(bay=3.0, st="casement", head="flat", w=1.3, h=1.45, panes=[3, 2], top_h=1.2),
        "interwar": dict(bay=3.0, st="casement", head="flat", w=1.4, h=1.3, panes=[3, 2], top_h=1.2),
        "modern": dict(bay=3.0, st="modern", head="flat", w=1.9, h=1.6, panes=[2, 1], top_h=1.6),
        "glass": dict(bay=3.0, st="modern", head="flat", w=2.5, h=2.3, panes=[2, 1], top_h=2.3),
        "vernacular": dict(bay=2.8, st="casement", head="flat", w=1.2, h=1.15, panes=[3, 2], top_h=1.0),
    }[style]
    if style == "victorian" and mat == "brick" and hw % 3 == 0:
        S["head"] = "arched"
    if style == "terrace" and _h(oid, "arch") % 3 == 0:
        S["head"] = "arched"
    if style == "victorian" and _h(oid, "panes") % 3 == 0:
        S["panes"] = [2, 2]
    if style == "college_gothic" and _h(oid, "tudor") % 3 == 0:   # Tudor/Perpendicular square-headed mullions
        S.update(st="casement", head="flat", w=1.45, h=1.5, panes=[3, 2])

    # facade trim per style
    if style in ("college_gothic", "college_tudor"):
        ann.update(cornice="simple", parapet=_h(oid, "par") % 5 != 0)   # battlemented parapets on most ranges
        if n > 1 and style == "college_gothic":
            ann["string_courses"] = [fz[1]]
    elif style == "college_classical":
        ann.update(cornice="classical", parapet=True, string_courses=[fz[1]] if n > 1 else [],
                   quoins=mat == "stone" and _h(oid, "q") % 4 == 0)
    elif style == "georgian":
        brick = mat == "brick"
        ann.update(cornice="simple" if brick else "classical", parapet=_h(oid, "par") % 2 == 0,
                   string_courses=[fz[1]] if n > 1 and _h(oid, "sc") % 2 == 0 else [])
    elif style == "victorian":
        ann.update(cornice="bracketed" if _h(oid, "cor") % 4 == 0 and L < 14 else "simple",
                   string_courses=[fz[1]] if n > 1 else [])
    elif style == "terrace":
        ann.update(cornice="simple" if _h(oid, "cor") % 2 else "none",
                   string_courses=[round(fz[1] - 0.05, 2)] if n > 1 and _h(oid, "sc") % 2 == 0 else [])
    elif style == "institutional":
        ann.update(cornice="simple", parapet=_h(oid, "par") % 2 == 0, string_courses=fz[1:3])
    elif style in ("modern", "glass", "college_modern"):
        ann.update(cornice="none", parapet=True)
    elif style == "villa":
        ann.update(cornice="simple" if _h(oid, "cor") % 3 == 0 else "none",
                   string_courses=[fz[1]] if n > 1 and _h(oid, "sc") % 3 == 0 else [])
    else:   # interwar, vernacular
        ann.update(cornice="none")

    modern = style in ("modern", "glass", "college_modern")
    extra = {"lintel": False} if modern else {}
    sill = not (style == "glass")

    if style == "terrace" and L >= 4.0:
        # house modules ~5.4 m: door + window below, two windows above (door bay mirrored by hash)
        units = max(1, int(round(L / 5.4)))
        uw = L / units
        for u in range(units):
            a = u * uw
            left_door = (_h(oid, "mir") + u) % 2 == 0
            xd, xw = (a + uw * 0.27, a + uw * 0.70) if left_door else (a + uw * 0.73, a + uw * 0.30)
            for k in range(n):
                fh = tops[k] - fz[k]
                top = k == n - 1 and n > 2
                h = min(S["top_h"] if top else S["h"], fh - 1.2)
                z = fz[k] + (0.75 if k == 0 else 0.85)
                if k == 0:
                    if shop:
                        continue
                    add_win(xw, min(1.2, uw * 0.3), z, h, S["st"], S["panes"], S["head"])
                    add_door(xd, 0.95, min(2.25, fh - 0.5), "panelled", "none",
                             colour=_pick(["#2e3b33", "#1f2a44", "#5a1f22", "#1b1b1b", "#3f5a4a"], oid, "door%d" % u))
                else:
                    add_win(xd, S["w"] * 0.85, z, h, S["st"], S["panes"])   # arched heads on the ground floor only
                    add_win(xw, S["w"], z, h, S["st"], S["panes"])
        return ann

    xs, bw = _bays(L, S["bay"])
    door_bay = None
    if not door_done and L > 5.0 and hw % 5 < 3:
        door_bay = len(xs) // 2
    for k in range(n):
        if k == 0 and shop:
            continue
        fh = tops[k] - fz[k]
        top = k == n - 1 and n > 2
        h = S["top_h"] if top else S["h"]
        if style in ("georgian", "college_classical") and k == 1:
            h += 0.25   # piano nobile
        z = fz[k] + (0.8 if k == 0 else 0.85)
        if modern:
            z = fz[k] + (0.6 if style == "glass" else 0.8)
            h = fh - (0.9 if style == "glass" else 1.25)
        h = min(h, fh - 1.15 + (0.35 if style == "glass" else 0))
        w = min(S["w"], bw * (0.85 if style == "glass" else 0.62 if modern else 0.5))
        for i, x in enumerate(xs):
            if k == 0 and i == door_bay:
                st = {"georgian": "panelled", "college_classical": "panelled", "college_gothic": "gothic",
                      "college_tudor": "arched", "victorian": "panelled", "villa": "panelled"}.get(style, "glazed")
                sur = "fanlight" if style in ("georgian",) and fh > 3.3 else (
                    "pilastered" if style == "college_classical" else "none")
                if add_door(x, 1.0 if not modern else 1.6, min(2.3 if not modern else 2.4, fh - 0.5), st, sur):
                    continue
            st, head, panes = S["st"], S["head"], S["panes"]
            if head in ("arched", "pointed") and k > 0:   # keep curved heads (3x the triangles) to the ground floor
                if style == "college_gothic":             # upper floors: square-headed Perpendicular mullion lights
                    st, panes = "casement", [2, 2]
                head = "flat"
            add_win(x, w, z, h, st, panes, head, sill=sill, **extra)
    return ann


if __name__ == "__main__":
    import json
    import sys
    for line in sys.argv[1:]:
        print(json.dumps(layout(json.loads(line)), indent=1))
