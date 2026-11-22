"""אחריותי - Streamlit prototype. Run with: streamlit run app.py"""
from __future__ import annotations

import json
import os
from datetime import date
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
PAGES = ["בית", "הוספה / סריקה", "פרטי מוצר", "ציר זמן", "הגדרות"]

STATUS_LABEL = {
    STATUS_EXPIRED: "פג תוקף",
    STATUS_SOON: "מסתיימת בקרוב",
    "ok": "בתוקף",
    STATUS_UNKNOWN: "תאריך חסר",
}

RTL_CSS = """
<style>
html, body, [class*="css"], .stApp { direction: rtl; text-align: right; }
[data-testid="stSidebar"] { direction: rtl; }
.block-container { max-width: 720px; padding-left: 16px; padding-right: 16px; }
</style>
"""


def conn():
    return db.connect(DB_PATH)


def go(page: str, product_id: int | None = None) -> None:
    # The nav widget is created before page content, so navigation is requested
    # via "goto" and applied at the top of the next run in main().
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
    return f"נותרו {left} ימים ({STATUS_LABEL[item['status']]})"


# ---------- screens ----------

def page_home(c, lead: int) -> None:
    st.title("אחריותי")
    st.caption("כל האחריות שלך, במקום אחד")
    today = date.today()
    products = db.list_products(c)
    enriched = [reminders.enrich(p, today, lead) for p in products]

    total_value = sum(p["price"] or 0 for p in enriched)
    c1, c2 = st.columns(2)
    c1.metric("מוצרים מבוטחים", len(enriched))
    c2.metric("שווי מצטבר", f"{total_value:,.0f}")

    due = reminders.due_reminders(products, today, lead)
    if due:
        st.warning(f"{len(due)} אחריות דורשות תשומת לב")
        for item in due:
            st.write(f"**{item['name']}** - {status_text(item)}")
            if st.button("פתח", key=f"due_{item['id']}"):
                go("פרטי מוצר", item["id"])
                st.rerun()

    st.button("סריקה / הוספת מוצר", type="primary", use_container_width=True,
              on_click=go, args=("הוספה / סריקה",))

    rooms = db.list_rooms(c)
    room = st.selectbox("סינון לפי חדר", ["הכל", *rooms]) if rooms else "הכל"
    shown = [p for p in enriched if room == "הכל" or p.get("room") == room]
    if not shown:
        st.info("עדיין אין מוצרים. לחצו על סריקה או הוספה כדי להתחיל.")
    for item in shown:
        with st.container(border=True):
            st.write(f"**{item['name']}** {('- ' + item['room']) if item.get('room') else ''}")
            st.caption(f"{status_text(item)} | תאריך רכישה: {fmt_date(item.get('purchase_date'))}")
            if st.button("פרטים", key=f"open_{item['id']}"):
                go("פרטי מוצר", item["id"])
                st.rerun()


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
        brand = st.text_input("יצרן", value=prefill.get("brand") or "")
        model = st.text_input("דגם", value=prefill.get("model") or "")
        store = st.text_input("חנות", value=prefill.get("store") or "")
        price = st.number_input("מחיר", min_value=0.0, value=float(prefill.get("price") or 0.0))
        pd_value = prefill.get("purchase_date")
        purchase = st.date_input(
            "תאריך רכישה", value=date.fromisoformat(pd_value) if pd_value else date.today(),
        )
        months = st.number_input("תקופת אחריות (חודשים)", min_value=0, step=1,
                                 value=int(prefill.get("warranty_months") or 12))
        room = st.text_input("חדר", value=prefill.get("room") or "")
        phone = st.text_input("טלפון שירות", value=prefill.get("support_phone") or "")
        submitted = st.form_submit_button("שמירה", type="primary")
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
        st.success("המוצר נשמר")
        go("בית")
        st.rerun()


def page_add(c) -> None:
    st.title("הוספת מוצר")
    tab_ai, tab_manual = st.tabs(["סריקה עם AI", "הוספה ידנית"])

    with tab_ai:
        st.caption("צלמו או העלו קבלה / תעודת אחריות. תוכלו לתקן כל שדה לפני השמירה.")
        upload = st.file_uploader("קבלה או תעודת אחריות", type=["jpg", "jpeg", "png", "webp", "pdf"])
        if upload is not None and st.button("זיהוי פרטים"):
            content = upload.getvalue()
            try:
                relative, digest = storage.save_upload(DATA_DIR, upload.name, content)
            except ValueError as exc:
                st.error(str(exc))
                return
            if not os.environ.get("ANTHROPIC_API_KEY"):
                st.warning("לא הוגדר ANTHROPIC_API_KEY. ממלאים ידנית, והקובץ נשמר.")
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
            st.info("בדקו את הפרטים שזוהו ותקנו במידת הצורך.")
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

    lead = st.session_state.get("lead", DEFAULT_LEAD)
    item = reminders.enrich(product, date.today(), lead)
    st.title(product["name"])
    st.caption(f"{product.get('brand') or ''} {product.get('model') or ''}".strip())
    c1, c2, c3 = st.columns(3)
    c1.metric("תאריך רכישה", fmt_date(product.get("purchase_date")))
    c2.metric("סיום אחריות", fmt_date(item["end_date"].isoformat() if item["end_date"] else None))
    c3.metric("ימים נותרו", item["days_left"] if item["days_left"] is not None else "-")
    st.write(f"**סטטוס:** {status_text(item)}")
    if product.get("support_phone"):
        st.write(f"**טלפון שירות:** {product['support_phone']}")

    st.subheader("מסמכים")
    docs = db.list_documents(c, pid)
    if not docs:
        st.caption("אין מסמכים עדיין.")
    for doc in docs:
        path = storage.absolute_path(DATA_DIR, doc["file_path"])
        if path.exists():
            st.download_button(f"הורדת {doc['kind']}", path.read_bytes(),
                               file_name=path.name, key=f"dl_{doc['id']}")
    extra = st.file_uploader("הוספת מסמך נוסף", type=["jpg", "jpeg", "png", "webp", "pdf"],
                             key="extra_doc")
    if extra is not None and st.button("שמירת מסמך"):
        try:
            relative, digest = storage.save_upload(DATA_DIR, extra.name, extra.getvalue())
            db.add_document(c, pid, "warranty", relative, digest)
            st.success("המסמך נשמר")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.subheader("עוזר AI")
    question = st.text_input("שאלה על תנאי האחריות", key="question")
    if st.button("שאלו את העוזר") and question:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.warning("העוזר דורש ANTHROPIC_API_KEY.")
        else:
            with st.spinner("בודק..."):
                try:
                    st.markdown(ai_assistant.answer(question, product))
                except Exception as exc:
                    st.error(f"העוזר לא זמין כרגע: {exc}")

    st.subheader("מכתב לשירות")
    problem = st.text_area("תיאור התקלה", key="problem")
    sender = st.text_input("השם שלכם (לחתימה)", key="sender")
    st.caption("זו טיוטה בלבד. העתיקו והדביקו בעצמכם; האפליקציה לא שולחת דבר.")
    st.code(letters.draft_letter(product, problem, sender), language=None)

    st.subheader("פעולות")
    if st.button("מחיקת המוצר", type="secondary"):
        st.session_state["confirm_delete"] = True
    if st.session_state.get("confirm_delete"):
        st.warning("המוצר והמסמכים שלו יימחקו. לא ניתן לשחזר.")
        if st.button("כן, מחקו"):
            for doc in docs:
                storage.delete_file(DATA_DIR, doc["file_path"])
            db.delete_product(c, pid)
            st.session_state.pop("confirm_delete", None)
            go("בית")
            st.rerun()


def page_timeline(c, lead: int) -> None:
    st.title("ציר זמן")
    items = [reminders.enrich(p, date.today(), lead) for p in db.list_products(c)]
    dated = sorted([i for i in items if i["end_date"]], key=lambda i: i["end_date"])
    undated = [i for i in items if not i["end_date"]]
    current_year = None
    for item in dated:
        if item["end_date"].year != current_year:
            current_year = item["end_date"].year
            st.subheader(str(current_year))
        st.write(f"{item['end_date'].strftime('%d/%m/%Y')} - **{item['name']}** ({STATUS_LABEL[item['status']]})")
    if undated:
        st.subheader("ללא תאריך סיום")
        for item in undated:
            st.write(f"**{item['name']}**")


def page_settings(c) -> None:
    st.title("הגדרות")
    st.slider("התראה לפני סיום אחריות (ימים)", 7, 90, key="lead")

    st.subheader("פרטיות")
    st.write(
        "המוצרים שלכם נשמרים במחשב הזה, בקובץ מקומי. "
        "מסמכים שאתם מזהים עם AI נשלחים ל-Claude API כדי לחלץ את הפרטים. "
        "לא נשלחים מסמכים לחנויות או לשירות הלקוחות."
    )
    st.subheader("מחיקת כל הנתונים")
    confirm = st.checkbox("אני מבין/ה שכל המוצרים והמסמכים יימחקו לצמיתות")
    if st.button("מחיקת כל הנתונים", disabled=not confirm):
        db.delete_all(c)
        storage.delete_all_files(DATA_DIR)
        st.session_state.clear()
        st.success("כל הנתונים נמחקו")


def main() -> None:
    st.set_page_config(page_title="אחריותי", page_icon="🧾", layout="centered")
    st.markdown(RTL_CSS, unsafe_allow_html=True)
    if "goto" in st.session_state:
        st.session_state["nav"] = st.session_state.pop("goto")
    st.session_state.setdefault("nav", "בית")
    st.session_state.setdefault("lead", DEFAULT_LEAD)

    with st.sidebar:
        st.radio("ניווט", PAGES, key="nav")

    c = conn()
    page = st.session_state["nav"]
    lead = st.session_state["lead"]
    if page == "בית":
        page_home(c, lead)
    elif page == "הוספה / סריקה":
        page_add(c)
    elif page == "פרטי מוצר":
        page_detail(c)
    elif page == "ציר זמן":
        page_timeline(c, lead)
    else:
        page_settings(c)
    c.close()


main()
