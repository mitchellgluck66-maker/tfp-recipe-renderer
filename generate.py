"""Orchestration: client selections -> Claude recipes -> USDA macros -> Pexels photos -> branded PDF."""
import os, json, re, requests
from render import render_guide

MODEL = os.environ.get("MODEL", "claude-sonnet-4-6")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
USDA_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")

SECTION_CFG = [
    ("breakfast", "SECTION 1: BANG FOR YOUR BUCK BREAKFASTS", ["BANG FOR YOUR BUCK"], "BREAKFASTS",
     "Bang For Your Buck Breakfasts",
     ["A high-protein start keeps you full and sets the tone for the day.",
      "Five go-to breakfasts built from the foods you love."]),
    ("lunch", "SECTION 2: GO-TO LUNCHES", ["GO-TO"], "LUNCHES", "Go-To Lunches",
     ["Lunches that meal-prep well and keep you satisfied.",
      "High protein, high fibre, built from your favourites."]),
    ("dinner", "SECTION 3: DELICIOUS DINNERS", ["DELICIOUS"], "DINNERS", "Delicious Dinners",
     ["Simple dinners, 30 minutes or less of active time.",
      "High protein and fibre, and family-friendly where it helps."]),
    ("snacks", "SECTION 4: SIMPLE HIGH-PROTEIN SNACKS", ["SIMPLE HIGH-PROTEIN"], "SNACKS",
     "Simple High-Protein Snacks",
     ["Portable, protein-forward bites to hold you over between meals.",
      "Keep a couple on hand for the days that get away from you."]),
]

def _lst(v):
    if isinstance(v, list): return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str): return [x.strip() for x in v.split(",") if x.strip()]
    return []

def build_prompt(d):
    enjoyed = _lst(d.get("proteins")) + _lst(d.get("dairy")) + _lst(d.get("cheese")) + _lst(d.get("carbs")) + \
              _lst(d.get("veg")) + _lst(d.get("fruits")) + _lst(d.get("sauces")) + _lst(d.get("dressings"))
    return (
      "You are a nutrition coach for The Fit Physician. Create a personalized recipe guide.\n"
      "RULES:\n"
      "- Return EXACTLY 5 breakfasts, 5 lunches, 5 dinners, 5 snacks.\n"
      "- Use ONLY these foods the client enjoys, plus everyday staples (oil, salt, pepper, dried herbs/spices, "
      "water, stock): " + (", ".join(enjoyed) or "(none selected: use simple high-protein staples)") + ".\n"
      "- Preferred meal styles: " + (", ".join(_lst(d.get("meals"))) or "any simple style") +
      ". Tools available: " + (", ".join(_lst(d.get("tools"))) or "basic stovetop/oven") + ".\n"
      "- HARD EXCLUDES, never include anything conflicting with these restrictions: " +
      (", ".join(_lst(d.get("restrictions"))) or "none") + ". Allergies/avoid: " + (d.get("allergies") or "none") + ".\n"
      "- NEVER use regular bacon; always use turkey bacon instead.\n"
      "- For any protein shake, use 1 cup Fairlife lactose-free skim milk plus 1 scoop protein powder, and in the "
      "directions say to mix it with an electric frother (not water).\n"
      "- If the client chose a bread, prefer Silver Hills or Carbonaut and briefly note in that recipe that these "
      "higher-protein, higher-fibre breads beat regular bread. If they chose a wrap, prefer Oro Wheat.\n"
      "- For deli meats, specify Maple Leaf Natural Selections.\n"
      "- If a recipe uses a dressing the client selected, suggest a lower-calorie version (e.g., light Caesar, "
      "balsamic vinaigrette).\n"
      "- Keep directions COMPREHENSIVE: clear numbered steps a beginner could follow (temperatures, times, cues).\n"
      "- High protein AND high fibre. Do NOT mention calories anywhere.\n"
      "Return ONLY valid JSON (no prose, no markdown):\n"
      '{"breakfast":[{"name":"","makes":"Serves 1","time":"12 minutes",'
      '"utensils":"Non-stick skillet, spatula, bowl",'
      '"protein":0,"fibre":0,'
      '"photoQueries":["specific dish","simpler","generic real dish"],'
      '"ingredients":[{"display":"150g chicken breast","grams":150,"fdcQuery":"chicken breast, cooked"}],'
      '"steps":["..."]}],"lunch":[...],"dinner":[...],"snacks":[...]}\n'
      "grams = weight per one serving; fdcQuery = plain USDA food name; photoQueries ordered specific->generic; "
      "protein/fibre = integer grams per serving (used only as a fallback estimate)."
    )

def call_claude(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 16000, "messages": [{"role": "user", "content": prompt}]}, timeout=120)
    r.raise_for_status()
    text = r.json()["content"][0]["text"]
    return json.loads(text[text.index("{"): text.rindex("}")+1])

_usda_cache = {}
def usda_lookup(q):
    if not q: return None
    if q in _usda_cache: return _usda_cache[q]
    try:
        r = requests.get("https://api.nal.usda.gov/fdc/v1/foods/search",
            params={"api_key": USDA_KEY, "query": q, "pageSize": 10,
                    "dataType": "Foundation,SR Legacy,Survey (FNDDS)"}, timeout=30)
        if r.status_code != 200: return None
        for food in r.json().get("foods", []):
            p = f = 0.0
            for n in food.get("foodNutrients", []):
                num = str(n.get("nutrientNumber", "")); nm = (n.get("nutrientName") or "").lower()
                if num == "203" or nm.startswith("protein"): p = n.get("value", p) or p
                if num == "291" or nm.startswith("fiber"): f = n.get("value", f) or f
            if p > 0:
                out = {"protein": p, "fibre": f}; _usda_cache[q] = out; return out
    except Exception:
        return None
    return None

def compute_macros(ingredients, est_p, est_f):
    P = F = 0.0; ok = False
    for ing in ingredients:
        g = float(ing.get("grams") or 0)
        if not g: continue
        n = usda_lookup(ing.get("fdcQuery") or ing.get("display"))
        if n: P += g/100*n["protein"]; F += g/100*n["fibre"]; ok = True
    if ok and (est_p == 0 or P >= est_p*0.7):
        return round(P), round(F)
    return est_p, est_f

def pexels_photo(queries):
    if not PEXELS_KEY: return None
    tries = list(queries or []) + ["healthy high protein meal plated"]
    for q in tries:
        if not q: continue
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": q, "per_page": 1, "orientation": "landscape"}, timeout=30)
            if r.status_code != 200: continue
            photos = r.json().get("photos", [])
            if not photos: continue
            src = photos[0]["src"]
            img = requests.get(src.get("landscape") or src.get("large") or src.get("medium"), timeout=30)
            if img.status_code == 200: return img.content
        except Exception:
            continue
    return None

def generate_guide(d):
    recipes = call_claude(build_prompt(d))
    sections = []
    for key, label, black_lines, magenta_word, toc_name, intro in SECTION_CFG:
        out_recipes = []
        for rec in (recipes.get(key) or [])[:5]:
            p, f = compute_macros(rec.get("ingredients", []), int(rec.get("protein") or 0), int(rec.get("fibre") or 0))
            out_recipes.append({
                "name": rec.get("name", ""), "makes": rec.get("makes", ""),
                "time": rec.get("time", ""), "utensils": rec.get("utensils", ""),
                "protein": p, "fibre": f,
                "ingredients": [ (i.get("display") if isinstance(i, dict) else str(i)) for i in rec.get("ingredients", []) ],
                "steps": rec.get("steps", []),
                "photo": pexels_photo(rec.get("photoQueries")),
            })
        sections.append({"label": label, "black_lines": black_lines, "magenta_word": magenta_word,
                         "toc_name": toc_name, "intro_lines": intro, "recipes": out_recipes})
    name = (str(d.get("first_name", "")).strip() + " " + str(d.get("last_name", "")).strip()).strip() or "Your"
    return render_guide(name, sections)
