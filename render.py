"""The Fit Physician — branded recipe guide PDF renderer (reportlab).
render_guide(client_name, sections) -> PDF bytes. Cover with the client's name, a full-page
welcome/intro, a table of contents on its own page, magenta section dividers, one recipe per
page with a charcoal header band, real photo, time + utensils, directions, macro pill, a
"Costco Picks" reference section after the recipes, and one branded closing page.
"""
import io, os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, Frame, Spacer, KeepInFrame
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets"); F = os.path.join(A, "fonts")

PURPLE = HexColor("#9B2484"); LIGHT = HexColor("#F6F6F6"); BLACK = HexColor("#000000")
WHITE = HexColor("#FFFFFF"); MIDGRAY = HexColor("#595959"); BORDER = HexColor("#CFCFCF")
CHAR = HexColor("#231F20"); ROWALT = HexColor("#F3F0F4")
W, H = letter

# Costco Canada finds (static reference shown on every guide).
COSTCO_SNACKS = [
    ("Premier Protein / Fairlife shakes", "30 g protein"),
    ("Quest / Kirkland protein bars", "20-21 g protein, 7-11 g fibre"),
    ("Frozen edamame", "12 g protein, 5 g fibre"),
    ("Quest protein chips", "18-20 g protein"),
    ("Three Farmers protein snack mix", "15 g protein, 12 g fibre"),
    ("Three Farmers chickpea & fava packs", "6 g protein, 5 g fibre"),
    ("Oikos high-protein yogurt cups", "15 g protein"),
    ("Kirkland grass-fed beef sticks", "10 g protein"),
    ("Kirkland turkey jerky / pepperoni", "10 g protein"),
    ("Cottage cheese snack cups", "12-15 g protein"),
    ("Hard-boiled eggs", "12 g protein / 2 eggs"),
    ("Popcorn", "4-5 g fibre"),
    ("Whisps parmesan cheese crisps", "14 g protein / 30 g"),
    ("Pears / apples", "4-6 g fibre / fruit"),
    ("Hummus cups + veggies", "varies by serving"),
]
COSTCO_BREADS = [
    ("Oroweat Keto Original Tortillas", "1 wrap", "~90", "3 g", "17 g"),
    ("Silver Hills Little Big Bread", "2 slices", "~100", "6 g", "5 g"),
    ("Silver Hills Squirrelly Bread", "2 slices", "~170", "11 g", "8 g"),
    ("Carbonaut Gluten-Free Plain Bagel", "1 bagel", "90", "2 g", "33 g"),
    ("Carbonaut Original Keto Bread", "1 slice", "~80", "7 g", "7 g"),
]

_registered = False
def _fonts():
    global _registered
    if _registered: return
    pdfmetrics.registerFont(TTFont("Lato", os.path.join(F, "Lato-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Lato-Bold", os.path.join(F, "Lato-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Lato-Italic", os.path.join(F, "Lato-Italic.ttf")))
    pdfmetrics.registerFont(TTFont("Lato-BoldItalic", os.path.join(F, "Lato-BoldItalic.ttf")))
    pdfmetrics.registerFont(TTFont("Lato-Black", os.path.join(F, "Lato-Black.ttf")))
    registerFontFamily("Lato", normal="Lato", bold="Lato-Bold", italic="Lato-Italic", boldItalic="Lato-BoldItalic")
    anton = os.path.join(F, "Anton-Regular.ttf")
    pdfmetrics.registerFont(TTFont("Headline", anton if os.path.exists(anton) else os.path.join(F, "Lato-Black.ttf")))
    _registered = True

COVER_IMG = os.path.join(A, "cover.png"); CLOSE1 = os.path.join(A, "closing-page-1.png")
CLOSE2 = os.path.join(A, "closing-page-2.png"); LOGO_DARK = os.path.join(A, "logo-white.png")
LOGO_LIGHT = os.path.join(A, "logo-color.png")

def _PS(name, **kw):
    kw.setdefault('fontName', 'Lato'); return ParagraphStyle(name, **kw)

def _crop_cover(img_bytes, target_w, target_h):
    """Center-crop image bytes to target aspect ratio, return ImageReader."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        iw, ih = im.size; tar = target_w / target_h; cur = iw / ih
        if cur > tar:
            nw = int(ih * tar); x = (iw - nw)//2; im = im.crop((x, 0, x+nw, ih))
        else:
            nh = int(iw / tar); y = (ih - nh)//2; im = im.crop((0, y, iw, y+nh))
        b = io.BytesIO(); im.save(b, format="JPEG", quality=85); b.seek(0)
        return ImageReader(b)
    except Exception:
        return None

def render_guide(client_name, sections, combos=None):
    _fonts()
    st_makes = _PS('m', fontName='Lato-Italic', fontSize=11, textColor=MIDGRAY, alignment=TA_CENTER, leading=14)
    st_meta = _PS('mt', fontSize=10.5, textColor=BLACK, alignment=TA_LEFT, leading=15)
    st_h = _PS('h', fontName='Lato-Bold', fontSize=13, textColor=PURPLE, alignment=TA_LEFT, leading=16, spaceBefore=4, spaceAfter=4)
    st_ing = _PS('i', fontSize=11.5, textColor=BLACK, alignment=TA_LEFT, leading=16)
    st_step = _PS('s', fontSize=11.5, textColor=BLACK, alignment=TA_LEFT, leading=16, leftIndent=22, firstLineIndent=-22, spaceAfter=3)
    st_body = _PS('b', fontSize=11, textColor=BLACK, alignment=TA_JUSTIFY, leading=16, spaceAfter=9)
    st_bodyc = _PS('bc', fontSize=11, textColor=BLACK, alignment=TA_CENTER, leading=16, spaceAfter=8)
    st_toc = _PS('toc', fontName='Lato-Bold', fontSize=14, textColor=BLACK, alignment=TA_LEFT, leading=17)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    def draw_logo(path, cx, cy, w, iw, ih):
        h = w*ih/iw; c.drawImage(path, cx-w/2, cy-h/2, w, h, mask='auto', preserveAspectRatio=True)
    def page_bars(logo=True):
        c.setFillColor(PURPLE); c.rect(0, H-30, W, 30, fill=1, stroke=0); c.rect(0, 0, W, 16, fill=1, stroke=0)
        if logo: draw_logo(LOGO_DARK, W-58, H-15, 72, 5517, 1890)
    def page_number():
        c.setFillColor(WHITE); c.setFont('Lato-Bold', 8.5); c.drawCentredString(W/2, 4.5, "Page %d" % c.getPageNumber())

    # cover
    c.drawImage(COVER_IMG, 0, 0, W, H)
    nm = client_name.upper(); ty = H*0.355; c.setFont('Headline', 30); c.setFillColor(BLACK)
    for dx, dy in [(-1.3,0),(1.3,0),(0,-1.3),(0,1.3),(-1,-1),(1,1),(-1,1),(1,-1)]:
        c.drawCentredString(W/2+dx, ty+dy, nm)
    c.setFillColor(WHITE); c.drawCentredString(W/2, ty, nm); c.showPage()

    # ===== intro (full page) =====
    page_bars(); draw_logo(LOGO_LIGHT, W/2, H-80, 132, 5736, 1875)
    st_ih = _PS('ih', fontName='Lato-Bold', fontSize=16, textColor=PURPLE, alignment=TA_CENTER, leading=20, spaceAfter=11)
    st_ib = _PS('ib', fontSize=10.8, textColor=BLACK, alignment=TA_LEFT, leading=15, spaceAfter=7)
    st_inote = _PS('inote', fontName='Lato-Bold', fontSize=10.8, textColor=PURPLE, alignment=TA_CENTER, leading=14, spaceBefore=3, spaceAfter=8)
    intro_flow = [
        Paragraph("Welcome to your personal Fit Physician Recipe Guide", st_ih),
        Paragraph("This guide was created to give you more tools, ideas, and inspiration to make eating well easier in your everyday life.", st_ib),
        Paragraph("One important thing before you dive in: this is <b>NOT</b> a meal plan. We don't believe in rigid plans that tell you exactly what to eat and when to eat it, especially when they're filled with foods you don't actually enjoy.", st_ib),
        Paragraph("Instead, our goal is to help you build your own recipe arsenal: a collection of go-to meals and snacks you genuinely enjoy, that fit your lifestyle, and help you work toward your goals. That's why the recipes in this guide were built around the foods YOU told us you love.", st_ib),
        Paragraph("You'll find simple, practical options that prioritize protein and fibre and can be mixed, matched, and adjusted based on your individual needs and preferences.", st_ib),
        Paragraph("Most importantly, this guide is designed to support the individualized nutrition coaching you'll receive throughout The Fit Physician program, not replace it.", st_ib),
        Paragraph("Each recipe makes 1 serving. For more servings, simply multiply all ingredient amounts.", st_inote),
        Paragraph("Please note that all calories, protein, fibre, and other macro calculations included in this guide are estimates. Exact nutrition information will vary depending on the brands, ingredients, quantities, and substitutions you use, so refer to your specific food labels when more precise tracking is important.", st_ib),
        Paragraph("We hope this becomes a resource you come back to again and again as you build a way of eating that is healthy, enjoyable, flexible, and sustainable.", st_ib),
        Paragraph("Enjoy!", st_ib),
        Paragraph("<b>The Fit Physician Team</b>", st_ib),
    ]
    ifr = Frame(80, 58, W-160, H-150-58, showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    ifr.addFromList([KeepInFrame(W-160, H-150-58, intro_flow, mode='shrink')], c)
    page_number(); c.showPage()

    # ===== table of contents (own page) =====
    page_bars(); draw_logo(LOGO_LIGHT, W/2, H-80, 132, 5736, 1875)
    c.setFillColor(BLACK); c.setFont('Headline', 30); c.drawCentredString(W/2, H-150, "TABLE OF CONTENTS")
    toc_entries = [s['toc_name'] for s in sections] + ["Costco Picks"]
    y = H-210; pg = 4  # cover=1, intro=2, TOC=3, sections start at 4
    for i, name in enumerate(toc_entries):
        is_costco = (name == "Costco Picks")
        c.setStrokeColor(PURPLE); c.setLineWidth(2); c.rect(80, y-8, 30, 32, fill=0, stroke=1)
        c.setFillColor(PURPLE); c.setFont('Headline', 20); c.drawCentredString(80+15, y+2, str(i+1))
        nf = Frame(123, y-8, W-123-110, 34, showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=6)
        nf.addFromList([Paragraph(name, st_toc)], c)
        c.setStrokeColor(MIDGRAY); c.setLineWidth(0.5); c.setDash(1, 3); c.line(W-150, y+4, W-96, y+4); c.setDash()
        c.setFillColor(PURPLE); c.setFont('Lato-Bold', 14); c.drawRightString(W-80, y+2, "p. %d" % pg)
        if not is_costco:
            pg += 1 + len(sections[i]['recipes'])
        y -= 52
    page_number(); c.showPage()

    def divider(s):
        page_bars(); cy = H/2 + 60
        c.setFillColor(BLACK); c.setFont('Headline', 40)
        for line in s['black_lines']:
            c.drawCentredString(W/2, cy, line); cy -= 44
        c.setFillColor(PURPLE); c.setFont('Headline', 40); c.drawCentredString(W/2, cy, s['magenta_word']); cy -= 20
        c.setFillColor(PURPLE); c.rect(W/2-45, cy, 90, 4, fill=1, stroke=0); cy -= 26
        f2 = Frame(90, cy-150, W-180, 150, showBoundary=0)
        f2.addFromList([Paragraph(t, st_bodyc) for t in s['intro_lines']], c)
        page_number(); c.showPage()

    def recipe_page(label, r):
        bh = 92; c.setFillColor(CHAR); c.rect(0, H-bh, W, bh, fill=1, stroke=0)
        draw_logo(LOGO_DARK, W/2, H-28, 116, 5517, 1890)
        c.setFillColor(WHITE); c.setFont('Headline', 25); c.drawCentredString(W/2, H-74, "RECIPE GUIDE")
        c.setFillColor(PURPLE); c.rect(0, H-bh-22, W, 22, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('Lato-Bold', 10.5); c.drawCentredString(W/2, H-bh-22+7, label.upper())
        up = r['name'].upper(); max_w = W - 96
        c.setFillColor(BLACK)
        size = 24
        while size > 13 and c.stringWidth(up, 'Headline', size) > max_w:
            size -= 1
        if c.stringWidth(up, 'Headline', size) <= max_w:
            c.setFont('Headline', size); c.drawCentredString(W/2, H-150, up)
        else:
            words = up.split(); mid = len(words)//2 or 1
            l1 = ' '.join(words[:mid]); l2 = ' '.join(words[mid:]); size = 18
            while size > 12 and (c.stringWidth(l1, 'Headline', size) > max_w or c.stringWidth(l2, 'Headline', size) > max_w):
                size -= 1
            c.setFont('Headline', size)
            c.drawCentredString(W/2, H-144, l1); c.drawCentredString(W/2, H-144-size, l2)
        if r.get('makes'):
            c.setFillColor(MIDGRAY); c.setFont('Lato-Italic', 10.5); c.drawCentredString(W/2, H-168, r['makes'])
        ph_top = H-176; ph_h = 104; bx, bw = 72, W-144
        img = _crop_cover(r['photo'], bw, ph_h) if r.get('photo') else None
        if img:
            c.drawImage(img, bx, ph_top-ph_h, bw, ph_h, mask='auto')
            c.setStrokeColor(BORDER); c.setLineWidth(0.6); c.roundRect(bx, ph_top-ph_h, bw, ph_h, 6, fill=0, stroke=1)
        else:
            c.setFillColor(LIGHT); c.setStrokeColor(BORDER); c.setLineWidth(0.6)
            c.roundRect(bx, ph_top-ph_h, bw, ph_h, 6, fill=1, stroke=1)
            c.setFillColor(MIDGRAY); c.setFont('Lato-Italic', 10); c.drawCentredString(W/2, ph_top-ph_h/2-4, "Recipe photo")
        mf = Frame(72, ph_top-ph_h-52, W-144, 46, showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        mf.addFromList([Paragraph("<b>Time to complete:</b> %s" % r.get('time',''), st_meta),
                        Paragraph("<b>Utensils:</b> %s" % r.get('utensils',''), st_meta)], c)
        fr2_h = (ph_top-ph_h-58)-120
        fr2 = Frame(72, 120, W-144, fr2_h, showBoundary=0, leftPadding=0, rightPadding=0)
        flow = [Paragraph("INGREDIENTS", st_h), Spacer(1, 2), Paragraph("<br/>".join(r['ingredients']), st_ing),
                Spacer(1, 12), Paragraph("DIRECTIONS", st_h), Spacer(1, 2)]
        for i, s2 in enumerate(r['steps']):
            flow.append(Paragraph("%d.&nbsp;&nbsp;&nbsp;%s" % (i+1, s2), st_step))
        fr2.addFromList([KeepInFrame(W-144, fr2_h, flow, mode='shrink')], c)
        if r.get('cal'):
            pw = 360; pill_text = "P: %sg   |   Fibre: %sg   |   %s cal" % (r['protein'], r['fibre'], r['cal'])
        else:
            pw = 280; pill_text = "P: %sg  |  Fibre: %sg" % (r['protein'], r['fibre'])
        ph2, yy = 30, 74
        c.setFillColor(CHAR); c.roundRect(W/2-pw/2, yy, pw, ph2, 5, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('Lato-Bold', 12)
        c.drawCentredString(W/2, yy+ph2/2-5, pill_text)
        c.setFillColor(MIDGRAY); c.setFont('Lato-Italic', 8.5); c.drawCentredString(W/2, yy-13, "(PER SERVING)")
        c.setFillColor(PURPLE); c.rect(0, 0, W, 16, fill=1, stroke=0); page_number(); c.showPage()

    for s in sections:
        divider(s)
        for r in s['recipes']:
            recipe_page(s['label'], r)

    # ===== Costco Picks (static reference, every guide) =====
    page_bars()
    c.setFillColor(BLACK); c.setFont('Headline', 30); c.drawCentredString(W/2, H-90, "COSTCO PICKS")
    c.setFillColor(PURPLE); c.rect(W/2-45, H-104, 90, 4, fill=1, stroke=0)
    c.setFillColor(MIDGRAY); c.setFont('Lato-Italic', 10)
    c.drawCentredString(W/2, H-122, "High-protein, high-fibre finds at Costco Canada to make hitting your targets easier.")

    def _rowline(x0, x1, yb):
        c.setStrokeColor(BORDER); c.setLineWidth(0.4); c.line(x0, yb, x1, yb)

    LMX, RMX = 60, W-60
    # --- snacks table ---
    y = H-146
    c.setFillColor(PURPLE); c.setFont('Lato-Bold', 12.5); c.drawString(LMX, y, "15 High-Protein Snack Finds"); y -= 16
    hh = 17
    c.setFillColor(CHAR); c.rect(LMX, y-hh+3, RMX-LMX, hh, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont('Lato-Bold', 9)
    c.drawString(LMX+6, y-hh+8, "SNACK / FIND"); c.drawString(LMX+320, y-hh+8, "PROTEIN / FIBRE PER SERVING")
    y -= hh
    rh = 16.4
    for idx, (nm2, macro) in enumerate(COSTCO_SNACKS):
        if idx % 2 == 0:
            c.setFillColor(ROWALT); c.rect(LMX, y-rh+3, RMX-LMX, rh, fill=1, stroke=0)
        c.setFillColor(BLACK); c.setFont('Lato', 9)
        c.drawString(LMX+6, y-rh+7, nm2)
        c.setFillColor(MIDGRAY); c.drawString(LMX+320, y-rh+7, macro)
        y -= rh
    _rowline(LMX, RMX, y+3)

    # --- breads & wraps table ---
    y -= 20
    c.setFillColor(PURPLE); c.setFont('Lato-Bold', 12.5); c.drawString(LMX, y, "5 Better Bread & Wrap Finds"); y -= 16
    cols = [LMX+6, LMX+232, LMX+312, LMX+388, LMX+452]  # product, serving, cal, protein, fibre
    c.setFillColor(CHAR); c.rect(LMX, y-hh+3, RMX-LMX, hh, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont('Lato-Bold', 9)
    for cx2, htxt in zip(cols, ["PRODUCT", "SERVING", "CAL", "PROTEIN", "FIBRE"]):
        c.drawString(cx2, y-hh+8, htxt)
    y -= hh
    for idx, row in enumerate(COSTCO_BREADS):
        if idx % 2 == 0:
            c.setFillColor(ROWALT); c.rect(LMX, y-rh+3, RMX-LMX, rh, fill=1, stroke=0)
        c.setFillColor(BLACK); c.setFont('Lato', 9)
        for cx2, val in zip(cols, row):
            c.drawString(cx2, y-rh+7, val)
        y -= rh
    _rowline(LMX, RMX, y+3)

    y -= 18
    st_fn = _PS('fn', fontSize=8, textColor=MIDGRAY, alignment=TA_LEFT, leading=11)
    fnf = Frame(LMX, y-34, RMX-LMX, 40, showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    fnf.addFromList([Paragraph("Nutrition values can vary by flavour, formulation, package size and warehouse, and Costco "
                               "inventory changes over time. Always check the Nutrition Facts panel on the specific product "
                               "you buy. These picks are suggestions, not endorsements.", st_fn)], c)
    page_number(); c.showPage()

    # bonus page: sample daily meal combinations (special calorie product only)
    if combos:
        page_bars()
        c.setFillColor(BLACK); c.setFont('Headline', 30); c.drawCentredString(W/2, H-96, "MEAL COMBINATIONS")
        c.setFillColor(PURPLE); c.rect(W/2-45, H-110, 90, 4, fill=1, stroke=0)
        c.setFillColor(MIDGRAY); c.setFont('Lato-Italic', 10.5)
        c.drawCentredString(W/2, H-130, "Sample days aiming for about 1600 calories and 130 to 150 g protein. Mix and match to fit you.")
        st_ch = _PS('ch', fontName='Lato-Bold', fontSize=12.5, textColor=PURPLE, leading=15, spaceBefore=9)
        st_cc = _PS('cc', fontSize=11, textColor=BLACK, leading=15, leftIndent=10)
        flow = []
        for idx, cb in enumerate(combos, 1):
            flow.append(Paragraph("Day %d &nbsp;&bull;&nbsp; about %s cal, %s g protein" % (idx, cb['cal'], cb['protein']), st_ch))
            for label, nm2, cal, pro in cb['items']:
                flow.append(Paragraph("<b>%s:</b> %s <font color='#595959'>(%s cal, %s g protein)</font>" % (label, nm2, cal, pro), st_cc))
        flow.append(Spacer(1, 10))
        flow.append(Paragraph("<i>All values are estimates. Add any snack from Section 4 to add roughly 200 to 300 calories and "
                              "20 to 28 g protein, or scale portions up or down to hit your own targets.</i>",
                              _PS('note', fontSize=10, textColor=MIDGRAY, leading=14)))
        bf = Frame(60, 90, W-120, H-150-90, showBoundary=0, leftPadding=0, rightPadding=0)
        bf.addFromList([KeepInFrame(W-120, H-150-90, flow, mode='shrink')], c)
        page_number(); c.showPage()

    # closing page (branded thank-you). The promo "learn more" page is intentionally not included.
    c.drawImage(CLOSE1, 0, 0, W, H)
    f3 = Frame(W*0.205, H*0.44, W*0.62, H*0.30, showBoundary=0)
    f3.addFromList([
        Paragraph("And there you have it! These are some of our favourite high-protein, high-fibre staples, built "
                  "around the foods you enjoy, to help you build a flexible diet that fits your taste buds and your goals.", st_body),
        Paragraph("You are not meant to only eat from this guide. Eat out, enjoy the glass of wine, grab ice cream with "
                  "the family, then lean on these staples to keep hitting your goals.", st_body),
        Paragraph("Any questions? Email hello@thefitphysician.com.", st_body),
    ], c)
    c.showPage()
    c.save(); buf.seek(0)
    return buf.getvalue()
