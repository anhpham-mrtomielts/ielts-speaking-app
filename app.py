import streamlit as st
import pandas as pd
import random
import time
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
        f"<div style='text-align:center;'><img src='{logo_url}' width='180'></div>",
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
# PRACTICE SETUP   (Fix #1 — slider bug)
# ─────────────────────────────────────────────
def page_practice_setup():
    st.title("📚 Practice Mode — Setup")
    df = load_data()

    available_sets = sorted(df["set"].unique().tolist())
    selected_sets  = st.multiselect("Select question set(s):", available_sets, default=available_sets[:1])
    if not selected_sets:
        st.warning("Please select at least one question set.")
        return

    filtered = df[df["set"].isin(selected_sets)]

    st.markdown("### Part 1")
    p1_topics          = sorted(filtered[filtered["part"] == "1"]["topic"].unique().tolist())
    selected_p1_topics = st.multiselect("Choose Part 1 topics:", p1_topics)

    # Fix: slider only shown when ≥2 topics selected; exactly 1 → no slider needed
    if len(selected_p1_topics) >= 2:
        num_p1_topics = st.slider(
            "Number of Part 1 topics to use:",
            min_value=1,
            max_value=len(selected_p1_topics),
            value=min(3, len(selected_p1_topics)))
    elif len(selected_p1_topics) == 1:
        num_p1_topics = 1
        st.caption("1 topic selected — all questions from that topic will be used.")
    else:
        num_p1_topics = 0

    st.markdown("### Part 2 & 3")
    p2_topics           = sorted(filtered[filtered["part"] == "2"]["topic"].unique().tolist())
    selected_p23_topics = st.multiselect("Choose Part 2 & 3 topics:", p2_topics)
    if len(selected_p23_topics) >= 2:
        num_p23_topics = st.slider(
            "Number of Part 2 & 3 topics:",
            min_value=1,
            max_value=len(selected_p23_topics),
            value=1)
    elif len(selected_p23_topics) == 1:
        num_p23_topics = 1
    else:
        num_p23_topics = 0

    st.markdown("### Timer")
    timer_mode = st.radio("Timer mode:", ["No timer", "Elapsed time", "Countdown"])

    if st.button("▶ Start Practice", use_container_width=True):
        if not selected_p1_topics and not selected_p23_topics:
            st.warning("Please select at least one topic.")
            return
        p1_chosen  = random.sample(selected_p1_topics, min(num_p1_topics,  len(selected_p1_topics)))  if selected_p1_topics  else []
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
        if st.session_state.show_read_aloud:
            for p in get_read_aloud_prompts("1", topic): st.info(f"🔊 {p}")
        for r in get_reminders("1"): st.warning(r)
        for i, q in enumerate(chosen_qs):
            col_q, col_t = st.columns([3, 1])
            with col_q: question_box(i + 1, q)
            with col_t: compact_timer(f"test_p1_{topic}_{i}", 30)
        st.markdown("---")

    elapsed_timer_bar("bottom")
    if st.button("➡ Continue to Part 2", use_container_width=True):
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

    st.markdown("---")
    elapsed_timer_bar("bottom")
    if st.button("➡ Continue to Part 3", use_container_width=True):
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

    set_qs = st.session_state.locked_p3_set
    if set_qs:
        if st.session_state.show_read_aloud:
            for p in get_read_aloud_prompts("3", topic): st.info(f"🔊 {p}")
        for r in get_reminders("3"): st.warning(r)
        for i, q in enumerate(set_qs):
            col_q, col_t = st.columns([3, 1])
            with col_q:
                lines = [l.strip() for l in q.split("\n") if l.strip()]
                for j, line in enumerate(lines): question_box(i + 1 if j == 0 else "", line)
            with col_t: compact_timer(f"test_p3_{i}", 45)
            st.markdown("---")
    else:
        st.warning("No Part 3 questions found for this topic.")

    elapsed_timer_bar("bottom")
    if st.button("✅ End Test & See Report", use_container_width=True):
        st.session_state.test_end_time = time.time()
        st.session_state.page = "test_report"; st.rerun()

# ─────────────────────────────────────────────
# TEST REPORT
# ─────────────────────────────────────────────
def page_test_report():
    tq = st.session_state.test_questions
    st.title("📊 Test Report")
    st.markdown("---")
    total = st.session_state.test_end_time - st.session_state.test_start_time
    st.metric("⏱ Total Test Time", format_time(total))
    st.markdown("### Topics Covered")
    st.markdown("**Part 1:**")
    for t in tq["p1_topics"]: st.markdown(f"- {t}")
    st.markdown(f"**Part 2 & 3:** {tq['p23_topic']}")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Test", use_container_width=True):
            for key in ["test_questions","test_start_time","test_end_time",
                        "locked_p1_questions","locked_p3_set"]:
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
if   page == "home":           page_home()
elif page == "practice_setup": page_practice_setup()
elif page == "practice_run":   page_practice_run()
elif page == "test_setup":     page_test_setup()
elif page == "test_preview":   page_test_preview()
elif page == "test_part1":     page_test_part1()
elif page == "test_part2":     page_test_part2()
elif page == "test_part3":     page_test_part3()
elif page == "test_report":    page_test_report()
