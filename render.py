"""The Fit Physician — branded recipe guide PDF renderer (reportlab).
render_guide(client_name, sections) -> PDF bytes. Same design as the Cowork template:
full-bleed cover with the client's name, welcome + table of contents with a disclaimer and
page numbers, magenta section dividers, one recipe per page with a charcoal header band,
real photo, time + utensils, comprehensive directions, macro pill, magenta header/footer bars,
and the two branded closing pages.
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
CHAR = HexColor("#231F20")
W, H = letter

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

    # welcome + TOC
    page_bars(); draw_logo(LOGO_LIGHT, W/2, H-95, 150, 5736, 1875)
    fr = Frame(72, 430, W-144, H-150-430, showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    fr.addFromList([
        Paragraph("<b>Welcome to The Fit Physician Recipe Guide.</b>", st_body),
        Paragraph("This guide features some of our favourite go-to meals and snacks, built around the foods you "
                  "told us you love, to help you reach your goals. Everything here is high in protein and fibre.", st_body),
        Paragraph("The key to a nutrition plan you will actually stick to is a recipe arsenal: a few staples for each "
                  "part of your day that you enjoy week in and week out. Mix in your favourite indulgences to build a "
                  "flexible diet that fits your life. This guide supports your coaching, it does not replace it.", st_body),
        Paragraph("<font name='Lato-BoldItalic' size=15>Enjoy! Suzanne &amp; Jake</font>", st_body),
    ], c)
    c.setFillColor(PURPLE); c.setFont('Lato-Bold', 10.5)
    c.drawCentredString(W/2, 416, "Each recipe makes 1 serving. For more servings, simply multiply all ingredient amounts.")
    c.setFillColor(MIDGRAY); c.setFont('Lato-Italic', 9.5)
    c.drawCentredString(W/2, 398, "Please note: all protein and fibre values in this guide are estimates.")
    c.setFillColor(BLACK); c.setFont('Headline', 28); c.drawCentredString(W/2, 360, "TABLE OF CONTENTS")
    y = 320; pg = 3
    for s in sections:
        c.setStrokeColor(PURPLE); c.setLineWidth(2); c.rect(72, y-8, 30, 32, fill=0, stroke=1)
        c.setFillColor(PURPLE); c.setFont('Headline', 20); c.drawCentredString(72+15, y+2, str(sections.index(s)+1))
        nf = Frame(115, y-8, W-115-110, 34, showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=6)
        nf.addFromList([Paragraph(s['toc_name'], st_toc)], c)
        c.setStrokeColor(MIDGRAY); c.setLineWidth(0.5); c.setDash(1, 3); c.line(W-150, y+4, W-96, y+4); c.setDash()
        c.setFillColor(PURPLE); c.setFont('Lato-Bold', 14); c.drawRightString(W-72, y+2, "p. %d" % pg)
        pg += 1 + len(s['recipes']); y -= 48
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
        # auto-fit recipe title to the page width (shrink; wrap to 2 lines only if truly long)
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
        # photo (real image if provided, else placeholder)
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
        # shrink to fit so long ingredient lists + directions never run off the page
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

    # bonus page: sample daily meal combinations (breakfast + lunch + dinner)
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
            for label, nm, cal, pro in cb['items']:
                flow.append(Paragraph("<b>%s:</b> %s <font color='#595959'>(%s cal, %s g protein)</font>" % (label, nm, cal, pro), st_cc))
        flow.append(Spacer(1, 10))
        flow.append(Paragraph("<i>All values are estimates. Add any snack from Section 4 to add roughly 200 to 300 calories and "
                              "20 to 28 g protein, or scale portions up or down to hit your own targets.</i>",
                              _PS('note', fontSize=10, textColor=MIDGRAY, leading=14)))
        bf = Frame(60, 90, W-120, H-150-90, showBoundary=0, leftPadding=0, rightPadding=0)
        bf.addFromList([KeepInFrame(W-120, H-150-90, flow, mode='shrink')], c)
        page_number(); c.showPage()

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
    c.drawImage(CLOSE2, 0, 0, W, H); c.showPage()
    c.save(); buf.seek(0)
    return buf.getvalue()
