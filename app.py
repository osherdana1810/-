"""אחריותי - Streamlit app. Run with: streamlit run app.py"""
from __future__ import annotations

import json
import os
from datetime import date
from html import escape
from pathlib import Path

import streamlit as st

from core import ai_assistant, ai_extract, db, letters, reminders, storage
from core.warranty import STATUS_EXPIRED, STATUS_SOON, STATUS_UNKNOWN

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "warranty.db"

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

DEFAULT_LEAD = int(os.environ.get("REMINDER_LEAD_DAYS", "30"))
NAV = ["בית", "הוספה", "ציר זמן", "הגדרות"]
VIEW_DETAIL = "פרטי מוצר"
UPLOAD_TYPES = ["jpg", "jpeg", "png", "webp", "pdf"]

STATUS_LABEL = {
    STATUS_EXPIRED: "פג תוקף",
    STATUS_SOON: "מסתיימת בקרוב",
    "ok": "בתוקף",
    STATUS_UNKNOWN: "תאריך חסר",
}
# Visual tone per status: good / warn / bad / muted (see DESIGN_CSS).
STATUS_TONE = {
    STATUS_EXPIRED: "bad",
    STATUS_SOON: "warn",
    "ok": "good",
    STATUS_UNKNOWN: "muted",
}

DESIGN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700;800&display=swap');

:root {
  --brand: #0F766E; --brand-2: #14B8A6;
  --ink: #152033; --muted: #667085; --line: #E4E7EC;
  --page: #F5F7F9; --card: #FFFFFF;
  --good: #067647; --good-bg: #ECFDF3;
  --warn: #B54708; --warn-bg: #FFFAEB; --warn-line: #FEDF89;
  --bad: #B42318; --bad-bg: #FEF3F2; --bad-line: #FECDCA;
  --muted-bg: #F2F4F7;
}
html, body, .stApp, [class*="css"] {
  font-family: 'Heebo', system-ui, sans-serif !important; direction: rtl;
}
.stApp { background: var(--page); color: var(--ink); }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { max-width: 640px; padding: 1rem 16px 4rem; }
h1 { font-weight: 800 !important; font-size: 1.7rem !important; letter-spacing: -0.3px; }
h2, h3 { font-weight: 700 !important; }

/* top navigation: one line, even on phones */
div[data-testid="stSegmentedControl"] { direction: rtl; margin: 4px 0 14px; }
div[data-testid="stSegmentedControl"] > div { width: 100%; display: flex; }
div[data-testid="stSegmentedControl"] { width: 100%; }
div[data-testid="stButtonGroup"] { width: 100% !important; display: flex !important; }
div[data-testid="stButtonGroup"] > div { width: 100%; }
div[data-testid="stSegmentedControl"] button { flex: 1 1 0; min-width: 0; padding: 8px 6px; }
div[data-testid="stSegmentedControl"] button p { font-size: .9rem; font-weight: 600; white-space: nowrap; }

/* page header */
.greet { margin: 4px 0 2px; }
.greet .hi { font-size: 1.6rem; font-weight: 800; letter-spacing: -.3px; }
.greet .date { color: var(--muted); font-size: .92rem; margin-top: 2px; }

/* empty state */
.empty { background: var(--card); border: 2px dashed #CFE7E3; border-radius: 20px;
  padding: 28px 20px; text-align: center; margin: 12px 0; }
.empty .icon { font-size: 2.4rem; }
.empty .t { font-weight: 800; font-size: 1.15rem; margin-top: 6px; }
.empty .d { color: var(--muted); margin-top: 6px; line-height: 1.6; }

/* hero summary */
.hero { background: linear-gradient(135deg, var(--brand), var(--brand-2)); color: #fff;
  border-radius: 20px; padding: 20px; margin: 4px 0 14px; }
.hero .label { opacity: .9; font-size: .95rem; }
.hero .stats { display: flex !important; flex-direction: row !important; gap: 10px; margin-top: 14px; }
.hero .stat { flex: 1; background: rgba(255,255,255,.18); border-radius: 14px; padding: 10px 12px; font-size: .85rem; }
.hero .stat b { display: block; font-size: 1.35rem; font-weight: 800; }

/* cards */
.card { background: var(--card); border: 1px solid var(--line); border-radius: 16px;
  padding: 16px; margin: 10px 0; box-shadow: 0 1px 2px rgba(16,24,40,.04); }
.card-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.card-title { font-weight: 700; font-size: 1.05rem; }
.card-sub { color: var(--muted); font-size: .9rem; margin-top: 4px; }
.kv { color: var(--muted); font-size: .9rem; margin-top: 6px; }

/* status chips and progress bars */
.chip { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .8rem; font-weight: 600; white-space: nowrap; }
.chip.good { background: var(--good-bg); color: var(--good); }
.chip.warn { background: var(--warn-bg); color: var(--warn); }
.chip.bad { background: var(--bad-bg); color: var(--bad); }
.chip.muted { background: var(--muted-bg); color: var(--muted); }
.bar { height: 8px; background: #EEF2F6; border-radius: 99px; overflow: hidden; margin-top: 12px; }
.bar > span { display: block; height: 100%; border-radius: 99px; background: var(--brand); }
.bar.warn > span { background: #F79009; }
.bar.bad > span { background: #F04438; }

/* alerts */
.alert { border-radius: 16px; padding: 14px 16px; margin: 10px 0; border: 1px solid; }
.alert.warn { background: var(--warn-bg); border-color: var(--warn-line); color: var(--warn); }
.alert.bad { background: var(--bad-bg); border-color: var(--bad-line); color: var(--bad); }
.alert b { font-weight: 800; }

/* detail tiles */
.tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0; }
.tile { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 12px 8px; text-align: center; }
.tile b { display: block; font-size: 1.1rem; font-weight: 800; }
.tile span { color: var(--muted); font-size: .8rem; }

/* steps on the add screen */
.steps { display: flex; gap: 8px; margin: 6px 0 12px; }
.steps div { flex: 1; text-align: center; font-size: .8rem; color: var(--muted);
  background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 8px 4px; }
.steps div b { display: block; color: var(--brand); font-size: 1rem; }

/* buttons and forms */
.stButton > button { border-radius: 12px; font-weight: 600; min-height: 44px; }
.stButton > button[kind="primary"] { background: var(--brand); border-color: var(--brand); }
.stButton > button[kind="primary"]:hover { background: #0B5F59; border-color: #0B5F59; }
[data-testid="stForm"] { background: var(--card); border-radius: 16px; border: 1px solid var(--line); padding: 16px; }
[data-testid="stFileUploader"] section { border-radius: 14px; }

@media (max-width: 480px) {
  .block-container { padding-left: 12px; padding-right: 12px; }
  .tiles { grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
  .hero .stat { padding: 8px 6px; font-size: .75rem; }
  .hero .stat b { font-size: 1.1rem; }
}
</style>
"""


def conn():
    return db.connect(DB_PATH)


def go(page: str, product_id: int | None = None) -> None:
    # Navigation widgets are created before page content, so the request is
    # stored under "goto" and applied at the top of the next run in main().
    st.session_state["goto"] = page
    if product_id is not None:
        st.session_state["selected_id"] = product_id


def fmt_date(value: str | None) -> str:
    return date.fromisoformat(value).strftime("%d/%m/%Y") if value else "לא ידוע"


def status_text(item: dict) -> str:
    left = item.get("days_left")
    if left is None:
        return STATUS_LABEL[STATUS_UNKNOWN]
    if left < 0:
        return f"פג לפני {-left} ימים"
    return f"נותרו {left} ימים"


def chip_html(item: dict) -> str:
    tone = STATUS_TONE[item["status"]]
    return f'<span class="chip {tone}">{STATUS_LABEL[item["status"]]}</span>'


def used_percent(item: dict, today: date) -> int | None:
    """Share of the warranty period already used, 0-100. None if dates are missing."""
    if not item.get("purchase_date") or not item.get("end_date"):
        return None
    start = date.fromisoformat(item["purchase_date"])
    total = (item["end_date"] - start).days
    if total <= 0:
        return None
    used = (today - start).days
    return max(0, min(100, round(used * 100 / total)))


def bar_html(item: dict, today: date) -> str:
    pct = used_percent(item, today)
    if pct is None:
        return ""
    tone = STATUS_TONE[item["status"]]
    extra = " warn" if tone == "warn" else " bad" if tone == "bad" else ""
    return f'<div class="bar{extra}"><span style="width:{pct}%"></span></div>'


def product_card_html(item: dict, today: date) -> str:
    room = f" · {escape(item['room'])}" if item.get("room") else ""
    return (
        '<div class="card">'
        '<div class="card-head">'
        f'<div class="card-title">{escape(item["name"])}</div>{chip_html(item)}'
        "</div>"
        f'<div class="card-sub">{escape(status_text(item))}{room}</div>'
        f"{bar_html(item, today)}"
        "</div>"
    )


@st.dialog("המוצר התקלקל?")
def fault_dialog(item: dict) -> None:
    """Ask for a short description of the fault and show ready-to-send messages."""
    pid = item["id"]
    st.write(f"**{item['name']}**")
    problem = st.text_area(
        "מה התקלה? כתבו בקצרה",
        key=f"problem_{pid}",
        placeholder="למשל: המכונה לא מסתובבת ומציגה קוד E21",
        height=90,
    )
    sender = st.text_input("השם שלכם (לחתימה)", key=f"sender_{pid}")
    if not problem.strip():
        st.info("כתבו משפט אחד על התקלה, ואנחנו נכין לכם הודעה רשמית לשירות הלקוחות.")
        return

    whatsapp = letters.whatsapp_message(item, problem, sender)
    subject, body = letters.email_draft(item, problem, sender)
    st.markdown("#### וואטסאפ")
    st.code(whatsapp, language=None, wrap_lines=True)
    st.markdown("#### מייל")
    st.code(f"נושא: {subject}\n\n{body}", language=None, wrap_lines=True)
    st.caption("לחצו על סמל ההעתקה בכל תיבה והדביקו בוואטסאפ או במייל. האפליקציה לא שולחת דבר בעצמה.")


def product_actions(item: dict, key: str) -> None:
    """Two buttons under a product card: open details, or report a fault."""
    c1, c2 = st.columns(2)
    if c1.button("פרטים", key=f"open_{key}_{item['id']}", use_container_width=True):
        go(VIEW_DETAIL, item["id"])
        st.rerun()
    if c2.button("המוצר התקלקל", key=f"fault_{key}_{item['id']}", use_container_width=True):
        fault_dialog(item)


# ---------- screens ----------

def page_home(c, lead: int) -> None:
    today = date.today()
    products = db.list_products(c)
    enriched = [reminders.enrich(p, today, lead) for p in products]
    due = reminders.due_reminders(products, today, lead)
    total_value = sum(p["price"] or 0 for p in enriched)

    st.markdown(
        '<div class="greet">'
        '<div class="hi">שלום 👋</div>'
        f'<div class="date">{today.strftime("%d/%m/%Y")} · כל האחריות שלכם במקום אחד</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero">'
        '<div class="label">כל האחריות שלך, במקום אחד</div>'
        '<div class="stats">'
        f'<div class="stat"><b>{len(enriched)}</b>מוצרים מבוטחים</div>'
        f'<div class="stat"><b>{total_value:,.0f} ₪</b>שווי מצטבר</div>'
        f'<div class="stat"><b>{len(due)}</b>דורשים תשומת לב</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )

    st.button("הוספת מוצר", type="primary", use_container_width=True,
              on_click=go, args=("הוספה",))

    if due:
        st.markdown(
            f'<div class="alert warn"><b>{len(due)} אחריות דורשות תשומת לב</b><br>'
            "בדקו את המוצרים הבאים לפני שהאחריות מסתיימת.</div>",
            unsafe_allow_html=True,
        )
        for item in due:
            st.markdown(product_card_html(item, today), unsafe_allow_html=True)
            product_actions(item, "due")

    st.subheader("המוצרים שלי")
    rooms = db.list_rooms(c)
    room = st.selectbox("סינון לפי חדר", ["הכל", *rooms]) if rooms else "הכל"
    shown = [p for p in enriched if room == "הכל" or p.get("room") == room]
    if not shown:
        if not enriched:
            st.markdown(
                '<div class="empty"><div class="icon">🧾</div>'
                '<div class="t">עוד אין כאן מוצרים</div>'
                '<div class="d">צלמו את הקבלה של המוצר הראשון, ואנחנו נמלא את הפרטים בשבילכם.<br>'
                "כך לא תצטרכו לחפש שוב את תעודת האחריות.</div></div>",
                unsafe_allow_html=True,
            )
            st.button("צילום קבלה ראשון", type="primary", use_container_width=True,
                      key="empty_cta", on_click=go, args=("הוספה",))
        else:
            st.caption("אין מוצרים בחדר הזה.")
    for item in shown:
        if item["id"] in {d["id"] for d in due}:
            continue  # already shown in the alert list above
        st.markdown(product_card_html(item, today), unsafe_allow_html=True)
        product_actions(item, "list")


def _save_product(c, fields: dict, document: tuple[str, str, str] | None,
                  extraction_json: str | None) -> int:
    product_id = db.add_product(c, **fields)
    if document:
        relative, digest, _original_name = document
        doc_id = db.add_document(c, product_id, "receipt", relative, digest)
        if extraction_json:
            db.add_extraction(c, doc_id, extraction_json)
    return product_id


def _product_form(c, prefill: dict, key: str) -> None:
    with st.form(key):
        name = st.text_input("שם המוצר *", value=prefill.get("name") or "")
        c1, c2 = st.columns(2)
        brand = c1.text_input("יצרן", value=prefill.get("brand") or "")
        model = c2.text_input("דגם", value=prefill.get("model") or "")
        c3, c4 = st.columns(2)
        store = c3.text_input("חנות", value=prefill.get("store") or "")
        price = c4.number_input("מחיר", min_value=0.0, value=float(prefill.get("price") or 0.0))
        pd_value = prefill.get("purchase_date")
        c5, c6 = st.columns(2)
        purchase = c5.date_input(
            "תאריך רכישה", value=date.fromisoformat(pd_value) if pd_value else date.today(),
        )
        months = c6.number_input("תקופת אחריות (חודשים)", min_value=0, step=1,
                                 value=int(prefill.get("warranty_months") or 12))
        c7, c8 = st.columns(2)
        room = c7.text_input("חדר", value=prefill.get("room") or "")
        phone = c8.text_input("טלפון שירות", value=prefill.get("support_phone") or "")
        submitted = st.form_submit_button("שמירת מוצר", type="primary", use_container_width=True)
    if submitted:
        if not name.strip():
            st.error("יש להזין שם מוצר")
            return
        fields = dict(
            name=name, brand=brand, model=model, store=store, price=price or None,
            purchase_date=purchase, warranty_months=int(months) or None,
            room=room, support_phone=phone, currency=prefill.get("currency") or "ILS",
        )
        _save_product(c, fields, st.session_state.pop("pending_doc", None),
                      st.session_state.pop("pending_json", None))
        st.session_state.pop("prefill", None)
        go("בית")
        st.toast("המוצר נשמר")
        st.rerun()


def page_add(c) -> None:
    st.title("הוספת מוצר")
    st.markdown(
        '<div class="steps"><div><b>1</b>צילום או העלאה</div>'
        '<div><b>2</b>בדיקת הפרטים</div><div><b>3</b>שמירה</div></div>',
        unsafe_allow_html=True,
    )
    tab_ai, tab_manual = st.tabs(["סריקה עם AI", "הוספה ידנית"])

    with tab_ai:
        upload = st.file_uploader("קבלה או תעודת אחריות", type=UPLOAD_TYPES)
        if upload is not None and st.button("זיהוי פרטים", type="primary"):
            content = upload.getvalue()
            try:
                relative, digest = storage.save_upload(DATA_DIR, upload.name, content)
            except ValueError as exc:
                st.error(str(exc))
                return
            if not os.environ.get("ANTHROPIC_API_KEY"):
                st.info("זיהוי אוטומטי לא מוגדר. מלאו את הפרטים ידנית, והקובץ יישמר.")
                fields = {}
            else:
                with st.spinner("מזהה פרטים..."):
                    try:
                        fields = ai_extract.extract_from_file(content, relative)
                    except Exception as exc:  # network / auth errors shown to the user
                        st.error(f"הזיהוי נכשל: {exc}")
                        fields = {}
            st.session_state["prefill"] = fields
            st.session_state["pending_doc"] = (relative, digest, upload.name)
            st.session_state["pending_json"] = json.dumps(fields, ensure_ascii=False)
        if "prefill" in st.session_state:
            st.markdown(
                '<div class="alert warn">בדקו את הפרטים שזוהו ותקנו כל שדה שאינו נכון.</div>',
                unsafe_allow_html=True,
            )
            _product_form(c, st.session_state["prefill"], "form_ai")

    with tab_manual:
        _product_form(c, {}, "form_manual")


def page_detail(c) -> None:
    pid = st.session_state.get("selected_id")
    product = db.get_product(c, pid) if pid else None
    if not product:
        st.info("בחרו מוצר מהרשימה.")
        st.button("חזרה לבית", on_click=go, args=("בית",))
        return

    today = date.today()
    lead = st.session_state.get("lead", DEFAULT_LEAD)
    item = reminders.enrich(product, today, lead)
    model_line = " · ".join(x for x in [product.get("brand"), product.get("model")] if x)
    room_line = f' · {escape(product["room"])}' if product.get("room") else ""

    st.title(product["name"])
    st.markdown(
        '<div class="card">'
        '<div class="card-head">'
        f'<div class="card-sub">{escape(model_line)}{room_line}</div>{chip_html(item)}'
        "</div>"
        f'<div class="card-title" style="margin-top:6px">{escape(status_text(item))}</div>'
        f"{bar_html(item, today)}"
        "</div>",
        unsafe_allow_html=True,
    )
    end_text = fmt_date(item["end_date"].isoformat() if item["end_date"] else None)
    left_text = item["days_left"] if item["days_left"] is not None else "-"
    st.markdown(
        '<div class="tiles">'
        f'<div class="tile"><b>{fmt_date(product.get("purchase_date"))}</b><span>תאריך רכישה</span></div>'
        f'<div class="tile"><b>{end_text}</b><span>סיום אחריות</span></div>'
        f'<div class="tile"><b>{left_text}</b><span>ימים נותרו</span></div>'
        "</div>",
        unsafe_allow_html=True,
    )
    if product.get("support_phone"):
        phone = escape(product["support_phone"])
        st.markdown(
            f'<div class="card"><div class="card-sub">טלפון שירות</div>'
            f'<a href="tel:{phone}" style="font-weight:700;font-size:1.1rem">{phone}</a></div>',
            unsafe_allow_html=True,
        )

    st.subheader("מסמכים")
    docs = db.list_documents(c, pid)
    if not docs:
        st.caption("אין מסמכים עדיין.")
    for doc in docs:
        path = storage.absolute_path(DATA_DIR, doc["file_path"])
        if path.exists():
            st.download_button(f"הורדת {doc['kind']}", path.read_bytes(),
                               file_name=path.name, key=f"dl_{doc['id']}")
    extra = st.file_uploader("הוספת מסמך נוסף", type=UPLOAD_TYPES, key="extra_doc")
    if extra is not None and st.button("שמירת מסמך"):
        try:
            relative, digest = storage.save_upload(DATA_DIR, extra.name, extra.getvalue())
            db.add_document(c, pid, "warranty", relative, digest)
            st.toast("המסמך נשמר")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.subheader("עוזר AI")
    question = st.text_input("שאלה על תנאי האחריות", key="question",
                             placeholder="למשל: האם הסוללה מכוסה?")
    if st.button("שאלו את העוזר") and question:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.info("העוזר דורש הגדרת ANTHROPIC_API_KEY.")
        else:
            with st.spinner("בודק..."):
                try:
                    st.markdown(ai_assistant.answer(question, product))
                except Exception as exc:
                    st.error(f"העוזר לא זמין כרגע: {exc}")

    st.subheader("המוצר התקלקל?")
    st.caption("כתבו מה התקלה, וקבלו הודעה רשמית מוכנה לוואטסאפ או למייל.")
    if st.button("הכנת פנייה לשירות", type="primary", use_container_width=True):
        fault_dialog(item)

    st.subheader("פעולות")
    if st.button("מחיקת המוצר"):
        st.session_state["confirm_delete"] = True
    if st.session_state.get("confirm_delete"):
        st.markdown(
            '<div class="alert bad">המוצר והמסמכים שלו יימחקו לצמיתות. לא ניתן לשחזר.</div>',
            unsafe_allow_html=True,
        )
        if st.button("כן, מחקו", type="primary"):
            for doc in docs:
                storage.delete_file(DATA_DIR, doc["file_path"])
            db.delete_product(c, pid)
            st.session_state.pop("confirm_delete", None)
            go("בית")
            st.rerun()


def page_timeline(c, lead: int) -> None:
    today = date.today()
    st.title("ציר זמן")
    st.caption("מועדי סיום האחריות של כל המוצרים בבית")
    items = [reminders.enrich(p, today, lead) for p in db.list_products(c)]
    dated = sorted([i for i in items if i["end_date"]], key=lambda i: i["end_date"])
    undated = [i for i in items if not i["end_date"]]
    if not items:
        st.markdown('<div class="card"><div class="card-sub">אין מוצרים להצגה.</div></div>',
                    unsafe_allow_html=True)
    current_year = None
    for item in dated:
        if item["end_date"].year != current_year:
            current_year = item["end_date"].year
            st.subheader(str(current_year))
        st.markdown(
            '<div class="card"><div class="card-head">'
            f'<div><div class="card-title">{escape(item["name"])}</div>'
            f'<div class="card-sub">עד {item["end_date"].strftime("%d/%m/%Y")}</div></div>'
            f"{chip_html(item)}</div></div>",
            unsafe_allow_html=True,
        )
    if undated:
        st.subheader("ללא תאריך סיום")
        for item in undated:
            st.markdown(product_card_html(item, today), unsafe_allow_html=True)


def page_settings(c) -> None:
    st.title("הגדרות")
    st.subheader("התראות")
    st.slider("התראה לפני סיום אחריות (ימים)", 7, 90, key="lead")

    st.subheader("פרטיות")
    st.markdown(
        '<div class="card"><div class="card-sub">'
        "המוצרים שלכם נשמרים במחשב הזה, בקובץ מקומי.<br>"
        "מסמכים שאתם מזהים עם AI נשלחים ל-Claude API כדי לחלץ את הפרטים.<br>"
        "לא נשלחים מסמכים לחנויות או לשירות הלקוחות."
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.subheader("מחיקת כל הנתונים")
    confirm = st.checkbox("אני מבין/ה שכל המוצרים והמסמכים יימחקו לצמיתות")
    if st.button("מחיקת כל הנתונים", disabled=not confirm, type="primary"):
        db.delete_all(c)
        storage.delete_all_files(DATA_DIR)
        st.session_state.clear()
        st.success("כל הנתונים נמחקו")


def _nav_changed() -> None:
    st.session_state["view"] = st.session_state.get("nav") or "בית"


def main() -> None:
    st.set_page_config(page_title="אחריותי", page_icon="🧾", layout="centered")
    st.markdown(DESIGN_CSS, unsafe_allow_html=True)

    if "goto" in st.session_state:
        target = st.session_state.pop("goto")
        st.session_state["view"] = target
        if target in NAV:
            st.session_state["nav"] = target
    st.session_state.setdefault("view", "בית")
    st.session_state.setdefault("nav", "בית")
    st.session_state.setdefault("lead", DEFAULT_LEAD)

    st.segmented_control("ניווט", NAV, key="nav", on_change=_nav_changed,
                         label_visibility="collapsed")

    c = conn()
    view = st.session_state["view"]
    lead = st.session_state["lead"]
    if view == "בית":
        page_home(c, lead)
    elif view == "הוספה":
        page_add(c)
    elif view == VIEW_DETAIL:
        page_detail(c)
    elif view == "ציר זמן":
        page_timeline(c, lead)
    else:
        page_settings(c)
    c.close()


main()
