import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
from io import BytesIO
from streamlit_autorefresh import st_autorefresh

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="IELTS Speaking Generator", page_icon="🗣️", layout="centered")

# ─────────────────────────────────────────────
# THEME — Orange palette
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Primary accent: Bronze / Rustic Orange */
    :root {
        --accent:       #E77D22;
        --accent-dark:  #D16002;
        --accent-mid:   #D78C3D;
        --accent-light: #FDAE44;
        --accent-pale:  #FEE8D6;
        --accent-warn:  #E77D22;
    }

    /* Page background */
    .stApp {
        background-color: #FFFAF5 !important;

    /* Sidebar & top bar tint */
    header[data-testid="stHeader"] { background: var(--accent-dark) !important; }

    /* Buttons — primary */
    div.stButton > button {
        background: var(--accent) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    div.stButton > button:hover {
        background: var(--accent-dark) !important;
    }

    /* Metric label & value */
    div[data-testid="metric-container"] label {
        color: var(--accent-dark) !important;
        font-weight: 700 !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: var(--accent) !important;
        font-size: 1.6rem !important;
        font-family: monospace !important;
    }

    /* Section dividers */
    hr { border-color: var(--accent-light) !important; }

    /* Info boxes (read-aloud prompts) */
    div[data-testid="stAlert"][aria-label="info"] {
        background: var(--accent-pale) !important;
        border-left: 4px solid var(--accent-light) !important;
        color: #5a3000 !important;
    }

    /* Warning boxes (reminders) */
    div[data-testid="stAlert"][aria-label="warning"] {
        border-left: 4px solid var(--accent-warn) !important;
    }

    /* Toggle */
    div[data-testid="stToggle"] span[data-checked="true"] {
        background: var(--accent) !important;
    }

    /* Elapsed bar */
    .elapsed-bar {
        background: var(--accent-pale);
        border: 1px solid var(--accent-light);
        border-radius: 8px;
        padding: 6px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.9rem;
        color: var(--accent-dark);
        margin-bottom: 10px;
        font-weight: 600;
    }
    .elapsed-bar span.val {
        font-family: monospace;
        font-size: 1.1rem;
        color: var(--accent-dark);
    }

    /* Question card */
    .q-box {
        background: #fff;
        border: 1px solid #e8cba8;
        border-left: 5px solid var(--accent);
        border-radius: 7px;
        padding: 13px 17px;
        margin: 6px 0 10px 0;
        font-size: 1.15rem;
        line-height: 1.6;
    }
    .q-label {
        color: var(--accent-light);
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    /* Skip button — grey with red text */
    button[kind="secondary"].skip-btn,
    div[data-testid="stButton"] button.skip-btn {
        background: #f0f0f0 !important;
        color: #cc0000 !important;
        border: 1px solid #ddd !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stButton"]:has(button[key*="skip"]) button {
        background: #f0f0f0 !important;
        color: #cc0000 !important;
        border: 1px solid #ddd !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }

    /* Cue card */
    .cue-card {
        background: #fffbf0;
        border: 2px solid var(--accent-light);
        border-radius: 9px;
        padding: 18px 22px;
        margin: 12px 0;
        font-size: 1.05rem;
        line-height: 1.7;
    }
    .cue-card .cue-label {
        font-size: 0.72rem;
        color: var(--accent-light);
        font-weight: 700;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    .cue-card .cue-title {
        font-weight: bold;
        font-size: 1.1rem;
        color: var(--accent-dark);
        margin-bottom: 10px;
    }
    .cue-card ul { margin: 0; padding-left: 20px; color: #4a2800; }
    .cue-card ul li { margin: 5px 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOAD DATA FROM GOOGLE SHEETS
# ─────────────────────────────────────────────
SHEET_ID   = "1rtQRtaq36d9pLSDXMDqzYprCQVYWtEBmewhYJzJCjzU"
SHEET_NAME = "Questions"

@st.cache_data(ttl=300)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    df  = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    required = ["set", "part", "topic", "question"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"❌ Missing columns: {', '.join(missing)}")
        st.stop()
    if "examiner_prompt" not in df.columns: df["examiner_prompt"] = ""
    if "question_set"    not in df.columns: df["question_set"]    = ""
    df["part"]            = df["part"].astype(str).str.strip()
    df["set"]             = df["set"].astype(str).str.strip()
    df["topic"]           = df["topic"].astype(str).str.strip()
    df["question"]        = df["question"].astype(str).str.strip()
    df["examiner_prompt"] = df["examiner_prompt"].fillna("").astype(str).str.strip()
    df["question_set"]    = df["question_set"].fillna("").astype(str).str.strip()
    df = df[df["question"].notna() & (df["question"] != "") & (df["question"] != "nan")]
    df = df[df["set"].notna()      & (df["set"]      != "") & (df["set"]      != "nan")]
    df = df[df["topic"].notna()    & (df["topic"]    != "") & (df["topic"]    != "nan")]
    df = df.drop_duplicates(subset=["part", "topic", "question_set", "question"])
    return df

# ─────────────────────────────────────────────
# EXAMINER PROMPTS
# ─────────────────────────────────────────────
def get_read_aloud_prompts(part, topic):
    if part == "1":
        return [f"Now let's talk about **{topic}**.",
                "Can you tell me more about that?", "Why do you think so?"]
    elif part == "2":
        return [f"I'd like you to talk about **{topic}**. Here is your topic card. You have one minute to prepare.",
                "All right, I'd like you to start speaking now."]
    elif part == "3":
        return [f"We've been talking about **{topic}**. I'd like to discuss some more general questions related to this.",
                "Can you explain why?", "What do other people think about this?"]
    return []

def get_reminders(part):
    if part == "1": return ["⏱ Press **Start** before asking each question."]
    elif part == "2": return ["⏱ Press **Start Prep** after handing the card.",
                              "⏱ Press **Start Speaking** when candidate begins."]
    elif part == "3": return ["⏱ Press **Start** before asking each question."]
    return []

# ─────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────
def format_time(seconds):
    m, s = divmod(int(max(0, seconds)), 60)
    return f"{m:02d}:{s:02d}"

def scroll_to_top():
    st.components.v1.html(
        "<script>window.parent.document.querySelector('section.main').scrollTo(0,0);</script>",
        height=0)

def elapsed_timer_bar(position="top"):
    """Orange pill bar — call with position='top' or 'bottom'."""
    if st.session_state.get("test_start_time"):
        elapsed = time.time() - st.session_state.test_start_time
        margin  = "margin-bottom:10px;" if position == "top" else "margin-top:18px;"
        st.markdown(
            f"<div class='elapsed-bar' style='{margin}'>"
            f"<span>⏱ Total elapsed</span>"
            f"<span class='val'>{format_time(elapsed)}</span>"
            f"</div>",
            unsafe_allow_html=True)

def question_box(number, text):
    label = f"<div class='q-label'>Q{number}</div>" if number != "" else ""
    st.markdown(
        f"<div class='q-box'>{label}{text}</div>",
        unsafe_allow_html=True)

def cue_card_box(topic, lines):
    if not lines:
        return
    title   = lines[0]
    bullets = "".join(f"<li>{l}</li>" for l in lines[1:]) if len(lines) > 1 else ""
    st.markdown(
        f"<div class='cue-card'>"
        f"<div class='cue-label'>📋 CUE CARD</div>"
        f"<div class='cue-title'>{title}</div>"
        f"<ul>{bullets}</ul>"
        f"</div>",
        unsafe_allow_html=True)

def any_timer_running():
    return any(v for k, v in st.session_state.items()
               if k.startswith("timer_") and k.endswith("_running") and v)

def compact_timer(key, duration, label=""):
    timer_key = f"timer_{key}_running"
    start_key = f"timer_{key}_start"
    done_key  = f"timer_{key}_done"
    if timer_key not in st.session_state:
        st.session_state[timer_key] = False
        st.session_state[start_key] = None
        st.session_state[done_key]  = False

    running   = st.session_state[timer_key]
    just_done = False
    if running:
        elapsed   = time.time() - st.session_state[start_key]
        remaining = max(0.0, duration - elapsed)
        if remaining == 0:
            st.session_state[timer_key] = False
            st.session_state[done_key]  = True
            just_done = True
    else:
        remaining = 0.0 if st.session_state[done_key] else float(duration)

    display_label = label if label else ("⏱ Running" if running else ("⏱ Done" if st.session_state[done_key] else "⏱ Ready"))
    st.metric(label=display_label, value=format_time(remaining))

    btn_label = "⏹ Stop" if running else ("🔁 Reset" if st.session_state[done_key] else "▶ Start")
    if st.button(btn_label, key=f"btn_{key}", use_container_width=True):
        if running:
            st.session_state[timer_key] = False
        elif st.session_state[done_key]:
            st.session_state[timer_key] = False
            st.session_state[done_key]  = False
            st.session_state[start_key] = None
        else:
            st.session_state[timer_key] = True
            st.session_state[start_key] = time.time()
            st.session_state[done_key]  = False
        st.rerun()
    if just_done:
        st.warning("⚠️ Time's up! Examiner — please decide.")
    return just_done

# ─────────────────────────────────────────────
# PART 1 TOPIC SELECTION LOGIC (Test mode)
# ─────────────────────────────────────────────
def pick_test_p1_topics(all_topics):
    """Pick 3 random Part 1 topics."""
    return random.sample(all_topics, min(3, len(all_topics)))

# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "page": "home", "mode": None, "df": None,
        "test_questions": None, "test_start_time": None, "test_end_time": None,
        "show_read_aloud": True, "practice_settings": {}, "test_log": [],
        "locked_p1_questions": {}, "locked_p3_set": [],
        "locked_practice_p1_questions": {}, "locked_practice_p3_set": {},
        "preview_data": None,
        # Practice mode memory
        "prac_mem_sets": [], "prac_mem_p1_topics": [],
        "prac_mem_p23_topics": [], "prac_mem_timer": "No timer",
        # Skip tracking
        "skipped_p1": {}, "skipped_p3": [],
        # Examiner notes per part
        "notes_p1": "", "notes_p2": "", "notes_p3": "",
        # Part timestamps for time breakdown
        "time_p1_start": None, "time_p1_end": None,
        "time_p2_start": None, "time_p2_end": None,
        "time_p3_start": None, "time_p3_end": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

st.session_state.logo_url = "https://raw.githubusercontent.com/anhpham-mrtomielts/ielts-speaking-app/main/logo.png"

if any_timer_running() or st.session_state.get("test_start_time"):
    st_autorefresh(interval=1000, limit=None, key="global_refresh")

# Logo — shows on every page
logo_url = st.session_state.get("logo_url", "")
if logo_url:
    st.markdown(
        f"<div style='text-align:center;'><img src='{logo_url}' width='240'></div>",
        unsafe_allow_html=True)
# ─────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────
def page_home():
    st.title("🗣️ IELTS Speaking Generator")
    st.markdown("Welcome! Choose a mode to get started.")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📚 Practice Mode", use_container_width=True):
            st.session_state.page = "practice_setup"; st.rerun()
    with col2:
        if st.button("🎯 Test Mode", use_container_width=True):
            st.session_state.page = "test_setup"; st.rerun()
    

# ─────────────────────────────────────────────
# PRACTICE SETUP
# ─────────────────────────────────────────────
def page_practice_setup():
    st.title("📚 Practice Mode — Setup")
    df = load_data()

    available_sets = sorted(df["set"].unique().tolist())

    # Memory: restore last selections
    mem_sets       = st.session_state.prac_mem_sets       or available_sets[:1]
    mem_p1_topics  = st.session_state.prac_mem_p1_topics
    mem_p23_topics = st.session_state.prac_mem_p23_topics
    mem_timer      = st.session_state.prac_mem_timer

    col_title, col_clear = st.columns([4, 1])
    with col_clear:
        if st.button("🗑 Clear", use_container_width=True):
            st.session_state.prac_mem_sets       = []
            st.session_state.prac_mem_p1_topics  = []
            st.session_state.prac_mem_p23_topics = []
            st.session_state.prac_mem_timer      = "No timer"
            st.rerun()

    selected_sets = st.multiselect(
        "Select question set(s):", available_sets,
        default=[s for s in mem_sets if s in available_sets])
    if not selected_sets:
        st.warning("Please select at least one question set.")
        return

    filtered = df[df["set"].isin(selected_sets)]

    st.markdown("### Part 1")
    p1_topics          = sorted(filtered[filtered["part"] == "1"]["topic"].unique().tolist())
    selected_p1_topics = st.multiselect(
        "Choose Part 1 topics:", p1_topics,
        default=[t for t in mem_p1_topics if t in p1_topics])

    if len(selected_p1_topics) >= 2:
        num_p1_topics = st.slider(
            "Number of Part 1 topics to use:",
            min_value=1, max_value=len(selected_p1_topics),
            value=min(3, len(selected_p1_topics)))
    elif len(selected_p1_topics) == 1:
        num_p1_topics = 1
        st.caption("1 topic selected — all questions from that topic will be used.")
    else:
        num_p1_topics = 0

    st.markdown("### Part 2 & 3")
    p2_topics           = sorted(filtered[filtered["part"] == "2"]["topic"].unique().tolist())
    selected_p23_topics = st.multiselect(
        "Choose Part 2 & 3 topics:", p2_topics,
        default=[t for t in mem_p23_topics if t in p2_topics])
    if len(selected_p23_topics) >= 2:
        num_p23_topics = st.slider(
            "Number of Part 2 & 3 topics:", min_value=1,
            max_value=len(selected_p23_topics), value=1)
    elif len(selected_p23_topics) == 1:
        num_p23_topics = 1
    else:
        num_p23_topics = 0

    st.markdown("### Timer")
    timer_options = ["No timer", "Elapsed time", "Countdown"]
    timer_mode    = st.radio("Timer mode:", timer_options,
                             index=timer_options.index(mem_timer) if mem_timer in timer_options else 0)

    if st.button("▶ Start Practice", use_container_width=True):
        if not selected_p1_topics and not selected_p23_topics:
            st.warning("Please select at least one topic.")
            return

        # Save selections to memory
        st.session_state.prac_mem_sets       = selected_sets
        st.session_state.prac_mem_p1_topics  = selected_p1_topics
        st.session_state.prac_mem_p23_topics = selected_p23_topics
        st.session_state.prac_mem_timer      = timer_mode

        p1_chosen  = random.sample(selected_p1_topics,  min(num_p1_topics,  len(selected_p1_topics)))  if selected_p1_topics  else []
        p23_chosen = random.sample(selected_p23_topics, min(num_p23_topics, len(selected_p23_topics))) if selected_p23_topics else []

        locked_p1 = {}
        for topic in p1_chosen:
            qs = filtered[(filtered["part"] == "1") & (filtered["topic"] == topic)]["question"].tolist()
            locked_p1[topic] = random.sample(qs, min(4, len(qs)))

        locked_p3 = {}
        for topic in p23_chosen:
            p3df  = filtered[(filtered["part"] == "3") & (filtered["topic"] == topic)]
            avail = p3df["question_set"].unique().tolist()
            if avail:
                locked_p3[topic] = p3df[p3df["question_set"] == random.choice(avail)]["question"].tolist()

        st.session_state.practice_settings            = {
            "sets": selected_sets, "p1_topics": p1_chosen,
            "p23_topics": p23_chosen, "timer_mode": timer_mode, "df": filtered}
        st.session_state.locked_practice_p1_questions = locked_p1
        st.session_state.locked_practice_p3_set       = locked_p3
        st.session_state.test_start_time              = time.time() if timer_mode != "No timer" else None
        st.session_state.page = "practice_run"
        st.rerun()

    if st.button("🏠 Back to Home"):
        st.session_state.page = "home"; st.rerun()

# ─────────────────────────────────────────────
# PRACTICE RUN
# ─────────────────────────────────────────────
def page_practice_run():
    settings   = st.session_state.practice_settings
    timer_mode = settings["timer_mode"]

    st.title("📚 Practice Mode")
    st.session_state.show_read_aloud = st.toggle("🔊 Show read-aloud prompts", value=st.session_state.show_read_aloud)
    if timer_mode != "No timer":
        elapsed_timer_bar()
    st.markdown("---")

    if settings["p1_topics"]:
        st.header("Part 1")
        for topic in settings["p1_topics"]:
            st.subheader(f"Topic: {topic}")
            chosen_qs = st.session_state.locked_practice_p1_questions.get(topic, [])
            if st.session_state.show_read_aloud:
                for p in get_read_aloud_prompts("1", topic): st.info(f"🔊 {p}")
            for r in get_reminders("1"): st.warning(r)
            for i, q in enumerate(chosen_qs):
                col_q, col_t = st.columns([3, 1])
                with col_q: question_box(i + 1, q)
                with col_t:
                    if timer_mode == "Countdown": compact_timer(f"prac_p1_{topic}_{i}", 30)
            st.markdown("---")

    if settings["p23_topics"]:
        df = settings["df"]
        for topic in settings["p23_topics"]:
            st.header(f"Part 2 — {topic}")
            p2_qs = df[(df["part"] == "2") & (df["topic"] == topic)]["question"].tolist()
            if p2_qs:
                raw_lines = [l.strip() for l in p2_qs[0].replace("\r", "").split("\n") if l.strip()]
                if st.session_state.show_read_aloud:
                    for p in get_read_aloud_prompts("2", topic): st.info(f"🔊 {p}")
                for r in get_reminders("2"): st.warning(r)
                cue_card_box(topic, raw_lines)
                if timer_mode == "Countdown":
                    compact_timer(f"prac_p2_prep_{topic}",  60,  "Prep (1 min)")
                    compact_timer(f"prac_p2_speak_{topic}", 120, "Speaking (2 min)")
            st.markdown("---")

            st.header(f"Part 3 — {topic}")
            set_qs = st.session_state.locked_practice_p3_set.get(topic, [])
            if set_qs:
                if st.session_state.show_read_aloud:
                    for p in get_read_aloud_prompts("3", topic): st.info(f"🔊 {p}")
                for r in get_reminders("3"): st.warning(r)
                for i, q in enumerate(set_qs):
                    col_q, col_t = st.columns([3, 1])
                    with col_q:
                        lines = [l.strip() for l in q.split("\n") if l.strip()]
                        for j, line in enumerate(lines): question_box(i + 1 if j == 0 else "", line)
                    with col_t:
                        if timer_mode == "Countdown": compact_timer(f"prac_p3_{topic}_{i}", 45)
            else:
                st.info("No Part 3 questions available for this topic.")
            st.markdown("---")

    if st.button("🏠 Back to Home", use_container_width=True):
        st.session_state.page = "home"; st.rerun()

# ─────────────────────────────────────────────
# TEST SETUP
# ─────────────────────────────────────────────
def page_test_setup():
    st.title("🎯 Test Mode")
    st.markdown("The system will automatically select **3 Part 1 topics** and **1 Part 2 & 3 topic**.")
    df = load_data()

    available_sets = sorted(df["set"].unique().tolist())
    selected_sets  = st.multiselect("Select question set(s) to draw from:", available_sets, default=available_sets[:1])

    if st.button("▶ Start Test", use_container_width=True):
        if not selected_sets:
            st.warning("Please select at least one question set.")
            return
        filtered  = df[df["set"].isin(selected_sets)]
        p1_topics = filtered[filtered["part"] == "1"]["topic"].unique().tolist()
        p2_topics = filtered[filtered["part"] == "2"]["topic"].unique().tolist()
        p3_topics = filtered[filtered["part"] == "3"]["topic"].unique().tolist()
        paired    = [t for t in p2_topics if t in p3_topics]

        if len(p1_topics) < 3:
            st.error("Not enough Part 1 topics. Need at least 3.")
            return
        if not paired:
            st.error("No paired Part 2 & 3 topics found. Check topic names match exactly.")
            return

        # Fix #5 — structured slot 1 selection
        chosen_p1  = pick_test_p1_topics(p1_topics)
        chosen_p23 = random.choice(paired)

        locked_p1 = {}
        for topic in chosen_p1:
            qs = filtered[(filtered["part"] == "1") & (filtered["topic"] == topic)]["question"].tolist()
            locked_p1[topic] = random.sample(qs, min(4, len(qs)))

        p3df     = filtered[(filtered["part"] == "3") & (filtered["topic"] == chosen_p23)]
        avail_p3 = p3df["question_set"].unique().tolist()
        locked_p3 = p3df[p3df["question_set"] == random.choice(avail_p3)]["question"].tolist() if avail_p3 else []

        p2_raw   = filtered[(filtered["part"] == "2") & (filtered["topic"] == chosen_p23)]["question"].tolist()
        p2_lines = [l.strip() for l in p2_raw[0].replace("\r", "").split("\n") if l.strip()] if p2_raw else []

        st.session_state.test_questions      = {"p1_topics": chosen_p1, "p23_topic": chosen_p23, "df": filtered}
        st.session_state.locked_p1_questions = locked_p1
        st.session_state.locked_p3_set       = locked_p3
        st.session_state.test_log            = []
        st.session_state.preview_data        = {"topic": chosen_p23, "lines": p2_lines}
        st.session_state.page                = "test_preview"
        st.rerun()

    if st.button("🏠 Back to Home"):
        st.session_state.page = "home"; st.rerun()

# ─────────────────────────────────────────────
# TEST — CUE CARD PREVIEW
# ─────────────────────────────────────────────
def page_test_preview():
    preview = st.session_state.preview_data
    tq      = st.session_state.test_questions

    st.title("🎯 Test Mode — Preview")
    st.markdown("Review the Part 2 cue card and prepare the physical card. Press **Begin Test** when ready.")
    st.markdown("---")

    st.markdown("### 📋 Part 2 Cue Card")
    cue_card_box(preview["topic"], preview["lines"])

    st.markdown("### 📃 Topics for this test")
    st.markdown("**Part 1:**")
    for t in tq["p1_topics"]: st.markdown(f"- {t}")
    st.markdown(f"**Part 2 & 3:** {tq['p23_topic']}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Begin Test", use_container_width=True, type="primary"):
            st.session_state.test_start_time = time.time()
            st.session_state.time_p1_start   = time.time()
            st.session_state.skipped_p1      = {}
            st.session_state.skipped_p3      = []
            st.session_state.notes_p1        = ""
            st.session_state.notes_p2        = ""
            st.session_state.notes_p3        = ""
            st.session_state.page = "test_part1"
            scroll_to_top(); st.rerun()
    with col2:
        if st.button("🏠 Back to Home", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

# ─────────────────────────────────────────────
# TEST — PART 1
# ─────────────────────────────────────────────
def page_test_part1():
    tq = st.session_state.test_questions
    st.title("🎯 Test Mode — Part 1")
    st.session_state.show_read_aloud = st.toggle("🔊 Show read-aloud prompts", value=st.session_state.show_read_aloud)
    elapsed_timer_bar()
    st.markdown("---")

    for topic in tq["p1_topics"]:
        st.subheader(f"Topic: {topic}")
        chosen_qs = st.session_state.locked_p1_questions.get(topic, [])
        skipped   = st.session_state.skipped_p1.get(topic, [])
        if st.session_state.show_read_aloud:
            for p in get_read_aloud_prompts("1", topic): st.info(f"🔊 {p}")
        for r in get_reminders("1"): st.warning(r)
        for i, q in enumerate(chosen_qs):
            is_skipped = i in skipped
            col_q, col_t, col_s = st.columns([3, 1, 1])
            with col_q:
                if is_skipped:
                    st.markdown(f"<div class='q-box' style='opacity:0.4;text-decoration:line-through;'>"
                                f"<div class='q-label'>Q{i+1}</div>{q}</div>", unsafe_allow_html=True)
                else:
                    question_box(i + 1, q)
            with col_t:
                if not is_skipped:
                    compact_timer(f"test_p1_{topic}_{i}", 30)
            with col_s:
                btn_label = "↩ Restore" if is_skipped else "⏭ Skip"
                if st.button(btn_label, key=f"skip_p1_{topic}_{i}", use_container_width=True):
                    cur = st.session_state.skipped_p1.get(topic, [])
                    if is_skipped:
                        cur = [x for x in cur if x != i]
                    else:
                        cur = cur + [i]
                    st.session_state.skipped_p1[topic] = cur
                    st.rerun()
        st.markdown("---")

    st.markdown("#### 📝 Examiner Notes — Part 1")
    st.session_state.notes_p1 = st.text_area(
        "Notes (optional):", value=st.session_state.notes_p1,
        placeholder="e.g. Candidate struggled with pronunciation on topic 2...",
        key="notes_p1_input", label_visibility="collapsed")

    elapsed_timer_bar("bottom")
    if st.button("➡ Continue to Part 2", use_container_width=True):
        st.session_state.time_p1_end   = time.time()
        st.session_state.time_p2_start = time.time()
        st.session_state.page = "test_transit_2"; scroll_to_top(); st.rerun()

# ─────────────────────────────────────────────
# TRANSITION — PART 2
# ─────────────────────────────────────────────
def page_test_transit_2():
    tq = st.session_state.test_questions
    elapsed_timer_bar()
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; padding: 40px 0;'>"
        "<div style='font-size:3rem;'>📄</div>"
        "<div style='font-size:1.8rem; font-weight:bold; margin:12px 0;'>Get Ready for Part 2</div>"
        f"<div style='font-size:1.1rem; color:#888;'>Topic: <b>{tq['p23_topic']}</b></div>"
        "</div>", unsafe_allow_html=True)
    st.markdown("---")
    if st.button("▶ Begin Part 2", use_container_width=True, type="primary"):
        st.session_state.page = "test_part2"; scroll_to_top(); st.rerun()

# ─────────────────────────────────────────────
# TEST — PART 2
# ─────────────────────────────────────────────
def page_test_part2():
    tq    = st.session_state.test_questions
    df    = tq["df"]
    topic = tq["p23_topic"]

    st.title("🎯 Test Mode — Part 2")
    st.subheader(f"Topic: {topic}")
    st.session_state.show_read_aloud = st.toggle("🔊 Show read-aloud prompts", value=st.session_state.show_read_aloud)
    elapsed_timer_bar()
    st.markdown("---")

    p2_qs = df[(df["part"] == "2") & (df["topic"] == topic)]["question"].tolist()
    if p2_qs:
        raw_lines = [l.strip() for l in p2_qs[0].replace("\r", "").split("\n") if l.strip()]
        if st.session_state.show_read_aloud:
            for p in get_read_aloud_prompts("2", topic): st.info(f"🔊 {p}")
        for r in get_reminders("2"): st.warning(r)
        cue_card_box(topic, raw_lines)
        st.markdown("&nbsp;")
        compact_timer("test_p2_prep",  60,  "Prep (1 min)")
        compact_timer("test_p2_speak", 120, "Speaking (2 min)")
    else:
        st.error("No Part 2 question found for this topic.")

    st.markdown("#### 📝 Examiner Notes — Part 2")
    st.session_state.notes_p2 = st.text_area(
        "Notes:", value=st.session_state.notes_p2,
        placeholder="e.g. Good use of linking words, needs more detail...",
        key="notes_p2_input", label_visibility="collapsed")

    st.markdown("---")
    elapsed_timer_bar("bottom")
    if st.button("➡ Continue to Part 3", use_container_width=True):
        st.session_state.time_p2_end   = time.time()
        st.session_state.time_p3_start = time.time()
        st.session_state.page = "test_transit_3"; scroll_to_top(); st.rerun()

# ─────────────────────────────────────────────
# TRANSITION — PART 3
# ─────────────────────────────────────────────
def page_test_transit_3():
    tq = st.session_state.test_questions
    elapsed_timer_bar()
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; padding: 40px 0;'>"
        "<div style='font-size:3rem;'>💬</div>"
        "<div style='font-size:1.8rem; font-weight:bold; margin:12px 0;'>Get Ready for Part 3</div>"
        f"<div style='font-size:1.1rem; color:#888;'>Topic: <b>{tq['p23_topic']}</b></div>"
        "</div>", unsafe_allow_html=True)
    st.markdown("---")
    if st.button("▶ Begin Part 3", use_container_width=True, type="primary"):
        st.session_state.page = "test_part3"; scroll_to_top(); st.rerun()

# ─────────────────────────────────────────────
# TEST — PART 3
# ─────────────────────────────────────────────
def page_test_part3():
    tq    = st.session_state.test_questions
    topic = tq["p23_topic"]

    st.title("🎯 Test Mode — Part 3")
    st.subheader(f"Topic: {topic}")
    st.session_state.show_read_aloud = st.toggle("🔊 Show read-aloud prompts", value=st.session_state.show_read_aloud)
    elapsed_timer_bar()
    st.markdown("---")

    set_qs   = st.session_state.locked_p3_set
    skipped3 = st.session_state.skipped_p3
    if set_qs:
        if st.session_state.show_read_aloud:
            for p in get_read_aloud_prompts("3", topic): st.info(f"🔊 {p}")
        for r in get_reminders("3"): st.warning(r)
        for i, q in enumerate(set_qs):
            is_skipped = i in skipped3
            col_q, col_t, col_s = st.columns([3, 1, 1])
            with col_q:
                lines = [l.strip() for l in q.split("\n") if l.strip()]
                if is_skipped:
                    for j, line in enumerate(lines):
                        st.markdown(
                            f"<div class='q-box' style='opacity:0.4;text-decoration:line-through;'>"
                            f"<div class='q-label'>Q{i+1}</div>{line}</div>",
                            unsafe_allow_html=True)
                else:
                    for j, line in enumerate(lines):
                        question_box(i + 1 if j == 0 else "", line)
            with col_t:
                if not is_skipped:
                    compact_timer(f"test_p3_{i}", 45)
            with col_s:
                btn_label = "↩ Restore" if is_skipped else "⏭ Skip"
                if st.button(btn_label, key=f"skip_p3_{i}", use_container_width=True):
                    if is_skipped:
                        st.session_state.skipped_p3 = [x for x in skipped3 if x != i]
                    else:
                        st.session_state.skipped_p3 = skipped3 + [i]
                    st.rerun()
            st.markdown("---")
    else:
        st.warning("No Part 3 questions found for this topic.")

    st.markdown("#### 📝 Examiner Notes — Part 3")
    st.session_state.notes_p3 = st.text_area(
        "Notes:", value=st.session_state.notes_p3,
        placeholder="e.g. Strong opinions, good vocabulary range...",
        key="notes_p3_input", label_visibility="collapsed")

    elapsed_timer_bar("bottom")
    if st.button("✅ End Test & See Report", use_container_width=True):
        st.session_state.time_p3_end   = time.time()
        st.session_state.test_end_time = time.time()
        st.session_state.page = "test_report"; st.rerun()

# ─────────────────────────────────────────────
# TEST REPORT
# ─────────────────────────────────────────────
def page_test_report():
    tq = st.session_state.test_questions
    st.title("📊 Test Report")
    st.markdown("---")

    # Total time
    total = st.session_state.test_end_time - st.session_state.test_start_time
    st.metric("⏱ Total Test Time", format_time(total))

    # Part breakdown
    st.markdown("### ⏱ Time per Part")
    col1, col2, col3 = st.columns(3)
    def part_dur(s, e):
        if s and e: return format_time(e - s)
        return "—"
    with col1: st.metric("Part 1", part_dur(st.session_state.time_p1_start, st.session_state.time_p1_end))
    with col2: st.metric("Part 2", part_dur(st.session_state.time_p2_start, st.session_state.time_p2_end))
    with col3: st.metric("Part 3", part_dur(st.session_state.time_p3_start, st.session_state.time_p3_end))

    # Topics
    st.markdown("### 📋 Topics Covered")
    st.markdown("**Part 1:**")
    for t in tq["p1_topics"]: st.markdown(f"- {t}")
    st.markdown(f"**Part 2 & 3:** {tq['p23_topic']}")

    # Skipped questions
    skipped_p1 = st.session_state.get("skipped_p1", {})
    skipped_p3 = st.session_state.get("skipped_p3", [])
    any_skipped = any(v for v in skipped_p1.values()) or skipped_p3
    if any_skipped:
        st.markdown("### ⏭ Skipped Questions")
        for topic, idxs in skipped_p1.items():
            if idxs:
                qs = st.session_state.locked_p1_questions.get(topic, [])
                for i in idxs:
                    if i < len(qs): st.markdown(f"- **P1 / {topic}:** {qs[i]}")
        if skipped_p3:
            set_qs = st.session_state.locked_p3_set
            for i in skipped_p3:
                if i < len(set_qs): st.markdown(f"- **P3:** {set_qs[i]}")

    # Examiner notes
    notes_p1 = st.session_state.get("notes_p1", "")
    notes_p2 = st.session_state.get("notes_p2", "")
    notes_p3 = st.session_state.get("notes_p3", "")
    if notes_p1 or notes_p2 or notes_p3:
        st.markdown("### 📝 Examiner Notes")
        if notes_p1: st.markdown(f"**Part 1:** {notes_p1}")
        if notes_p2: st.markdown(f"**Part 2:** {notes_p2}")
        if notes_p3: st.markdown(f"**Part 3:** {notes_p3}")

    # ── Export section ──
    st.markdown("---")
    st.markdown("### 📥 Export Report")

    candidate_name = st.text_input(
        "Candidate name (optional):",
        placeholder="e.g. Nguyen Van A",
        key="candidate_name_input")

    now          = datetime.now()
    date_str     = now.strftime("%Y-%m-%d")
    time_str     = now.strftime("%H:%M")
    datetime_str = now.strftime("%Y-%m-%d %H:%M")
    safe_name    = candidate_name.strip().replace(" ", "_") if candidate_name.strip() else "candidate"
    file_stem    = f"IELTS_Report_{safe_name}_{now.strftime('%Y%m%d_%H%M')}"

    # Build shared report content
    report_lines = [
        "IELTS SPEAKING TEST REPORT",
        "=" * 40,
        f"Date: {date_str}   Time: {time_str}",
        f"Candidate: {candidate_name.strip() if candidate_name.strip() else '—'}",
        "",
        "TIME SUMMARY",
        f"  Total : {format_time(total)}",
        f"  Part 1: {part_dur(st.session_state.time_p1_start, st.session_state.time_p1_end)}",
        f"  Part 2: {part_dur(st.session_state.time_p2_start, st.session_state.time_p2_end)}",
        f"  Part 3: {part_dur(st.session_state.time_p3_start, st.session_state.time_p3_end)}",
        "",
        "TOPICS COVERED",
        "  Part 1: " + ", ".join(tq["p1_topics"]),
        f"  Part 2 & 3: {tq['p23_topic']}",
    ]

    skipped_p1 = st.session_state.get("skipped_p1", {})
    skipped_p3 = st.session_state.get("skipped_p3", [])
    any_skipped = any(v for v in skipped_p1.values()) or skipped_p3
    if any_skipped:
        report_lines += ["", "SKIPPED QUESTIONS"]
        for topic, idxs in skipped_p1.items():
            if idxs:
                qs = st.session_state.locked_p1_questions.get(topic, [])
                for i in idxs:
                    if i < len(qs): report_lines.append(f"  P1 / {topic}: {qs[i]}")
        if skipped_p3:
            set_qs = st.session_state.locked_p3_set
            for i in skipped_p3:
                if i < len(set_qs): report_lines.append(f"  P3: {set_qs[i]}")

    if notes_p1: report_lines += ["", "EXAMINER NOTES — Part 1", f"  {notes_p1}"]
    if notes_p2: report_lines += ["", "EXAMINER NOTES — Part 2", f"  {notes_p2}"]
    if notes_p3: report_lines += ["", "EXAMINER NOTES — Part 3", f"  {notes_p3}"]

    report_text = "\n".join(report_lines)

    def build_pdf(lines, candidate, dt_str):
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        # Use built-in core font with latin encoding — avoids Unicode width crash
        # Strip any non-latin1 characters safely so fpdf never chokes
        def safe(text):
            return text.encode("latin-1", errors="replace").decode("latin-1")
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, safe("IELTS Speaking Test Report"), ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, safe(f"Date & Time: {dt_str}"), ln=True, align="C")
        if candidate:
            pdf.cell(0, 7, safe(f"Candidate: {candidate}"), ln=True, align="C")
        pdf.ln(4)
        pdf.set_draw_color(205, 127, 50)
        pdf.set_line_width(0.8)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 11)
        for line in lines[4:]:
            if line.startswith("="):
                continue
            stripped = line.strip()
            if stripped and stripped == stripped.upper() and len(stripped) > 2:
                pdf.set_font("Helvetica", "B", 12)
                pdf.ln(2)
                pdf.cell(0, 8, safe(line), ln=True)
                pdf.set_font("Helvetica", "", 11)
            else:
                pdf.multi_cell(0, 7, safe(line) if stripped else " ")
        return bytes(pdf.output())

    col_txt, col_pdf = st.columns(2)
    with col_txt:
        st.download_button(
            label="📄 Download TXT",
            data=report_text,
            file_name=f"{file_stem}.txt",
            mime="text/plain",
            use_container_width=True)
    with col_pdf:
        try:
            pdf_bytes = build_pdf(report_lines, candidate_name.strip(), datetime_str)
            st.download_button(
                label="📕 Download PDF",
                data=pdf_bytes,
                file_name=f"{file_stem}.pdf",
                mime="application/pdf",
                use_container_width=True)
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Test", use_container_width=True):
            for key in ["test_questions","test_start_time","test_end_time",
                        "locked_p1_questions","locked_p3_set","skipped_p1","skipped_p3",
                        "notes_p1","notes_p2","notes_p3",
                        "time_p1_start","time_p1_end","time_p2_start","time_p2_end",
                        "time_p3_start","time_p3_end"]:
                st.session_state.pop(key, None)
            st.session_state.page = "test_setup"; st.rerun()
    with col2:
        if st.button("🏠 Back to Home", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

# ─────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────
page = st.session_state.page
if   page == "home":             page_home()
elif page == "practice_setup":   page_practice_setup()
elif page == "practice_run":     page_practice_run()
elif page == "test_setup":       page_test_setup()
elif page == "test_preview":     page_test_preview()
elif page == "test_part1":       page_test_part1()
elif page == "test_transit_2":   page_test_transit_2()
elif page == "test_part2":       page_test_part2()
elif page == "test_transit_3":   page_test_transit_3()
elif page == "test_part3":       page_test_part3()
elif page == "test_report":      page_test_report()
