import streamlit as st
import pandas as pd
import random
import time
from streamlit_autorefresh import st_autorefresh

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="IELTS Speaking App", page_icon="🎓", layout="centered")

# ─────────────────────────────────────────────
# LOAD DATA FROM GOOGLE SHEETS
# ─────────────────────────────────────────────
SHEET_ID = "1rtQRtaq36d9pLSDXMDqzYprCQVYWtEBmewhYJzJCjzU"
SHEET_NAME = "Questions"

@st.cache_data(ttl=300)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["part"] = df["part"].astype(str).str.strip()
    df["set"] = df["set"].astype(str).str.strip()
    df["topic"] = df["topic"].astype(str).str.strip()
    df["question"] = df["question"].astype(str).str.strip()
    df["examiner_prompt"] = df["examiner_prompt"].fillna("").astype(str).str.strip()
    df["question_set"] = df["question_set"].fillna("").astype(str).str.strip()
    df = df.drop_duplicates(subset=["part", "topic", "question_set", "question"])
    df = df[df["question"].notna() & (df["question"] != "") & (df["question"] != "nan")]
    return df

# ─────────────────────────────────────────────
# FIXED EXAMINER PROMPTS
# ─────────────────────────────────────────────
def get_read_aloud_prompts(part, topic):
    if part == "1":
        return [
            f"Now let's talk about **{topic}**.",
            "Can you tell me more about that?",
            "Why do you think so?",
        ]
    elif part == "2":
        return [
            f"I'd like you to talk about **{topic}**. Here is your topic card. You have one minute to prepare.",
            "All right, I'd like you to start speaking now.",
        ]
    elif part == "3":
        return [
            f"We've been talking about **{topic}**. I'd like to discuss some more general questions related to this.",
            "Can you explain why?",
            "What do other people think about this?",
        ]
    return []

def get_reminders(part):
    if part == "1":
        return ["⏱ Press **Start** before asking each question."]
    elif part == "2":
        return [
            "⏱ Press **Start Prep** after handing the card.",
            "⏱ Press **Start Speaking** when candidate begins.",
        ]
    elif part == "3":
        return ["⏱ Press **Start** before asking each question."]
    return []

# ─────────────────────────────────────────────
# TIMER HELPERS
# ─────────────────────────────────────────────
def format_time(seconds):
    m, s = divmod(int(max(0, seconds)), 60)
    return f"{m:02d}:{s:02d}"

def any_timer_running():
    """Check if any countdown timer is currently active."""
    return any(
        v for k, v in st.session_state.items()
        if k.startswith("timer_") and k.endswith("_running") and v
    )

def elapsed_timer_bar():
    """Slim elapsed time bar — always visible during a session."""
    if st.session_state.get("test_start_time"):
        elapsed = time.time() - st.session_state.test_start_time
        st.metric(label="⏱ Total elapsed", value=format_time(elapsed))

def compact_timer(key, duration, label=""):
    """
    Compact inline timer using st.metric — works safely inside columns.
    """
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

    # Display — st.metric renders reliably everywhere
    display_label = label if label else ("⏱ Running" if running else ("⏱ Done" if st.session_state[done_key] else "⏱ Ready"))
    st.metric(label=display_label, value=format_time(remaining))

    # Button
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
# SESSION STATE INIT
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "page": "home",
        "mode": None,
        "df": None,
        "test_questions": None,
        "test_start_time": None,
        "test_end_time": None,
        "show_read_aloud": True,
        "practice_settings": {},
        "test_log": [],
        "locked_p1_questions": {},
        "locked_p3_set": [],
        "locked_practice_p1_questions": {},
        "locked_practice_p3_set": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Auto-refresh every second only when a timer is running or elapsed timer is active
if any_timer_running() or st.session_state.get("test_start_time"):
    st_autorefresh(interval=1000, limit=None, key="global_refresh")

# ─────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────
def page_home():
    st.title("🎓 IELTS Speaking App")
    st.markdown("Welcome! Choose a mode to get started.")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📚 Practice Mode", use_container_width=True):
            st.session_state.page = "practice_setup"
            st.rerun()
    with col2:
        if st.button("🎯 Test Mode", use_container_width=True):
            st.session_state.page = "test_setup"
            st.rerun()

# ─────────────────────────────────────────────
# PRACTICE SETUP
# ─────────────────────────────────────────────
def page_practice_setup():
    st.title("📚 Practice Mode — Setup")
    df = load_data()

    available_sets = sorted(df["set"].unique().tolist())
    selected_sets = st.multiselect("Select question set(s):", available_sets, default=available_sets[:1])

    if not selected_sets:
        st.warning("Please select at least one question set.")
        return

    filtered = df[df["set"].isin(selected_sets)]

    st.markdown("### Part 1")
    p1_topics = sorted(filtered[filtered["part"] == "1"]["topic"].unique().tolist())
    selected_p1_topics = st.multiselect("Choose Part 1 topics:", p1_topics)
    num_p1_topics = st.slider("Number of Part 1 topics to use:", 1, max(1, len(selected_p1_topics)), min(3, max(1, len(selected_p1_topics)))) if selected_p1_topics else 0

    st.markdown("### Part 2 & 3")
    p2_topics = sorted(filtered[filtered["part"] == "2"]["topic"].unique().tolist())
    selected_p23_topics = st.multiselect("Choose Part 2 & 3 topics:", p2_topics)
    num_p23_topics = st.slider("Number of Part 2 & 3 topics:", 1, max(1, len(selected_p23_topics)), 1) if selected_p23_topics else 0

    st.markdown("### Timer")
    timer_mode = st.radio("Timer mode:", ["No timer", "Elapsed time", "Countdown"])

    if st.button("▶ Start Practice", use_container_width=True):
        if not selected_p1_topics and not selected_p23_topics:
            st.warning("Please select at least one topic.")
            return
        p1_chosen  = random.sample(selected_p1_topics, min(num_p1_topics, len(selected_p1_topics))) if selected_p1_topics else []
        p23_chosen = random.sample(selected_p23_topics, min(num_p23_topics, len(selected_p23_topics))) if selected_p23_topics else []

        locked_p1 = {}
        for topic in p1_chosen:
            qs = filtered[(filtered["part"] == "1") & (filtered["topic"] == topic)]["question"].tolist()
            locked_p1[topic] = random.sample(qs, min(4, len(qs)))

        locked_p3 = {}
        for topic in p23_chosen:
            p3df = filtered[(filtered["part"] == "3") & (filtered["topic"] == topic)]
            avail = p3df["question_set"].unique().tolist()
            if avail:
                locked_p3[topic] = p3df[p3df["question_set"] == random.choice(avail)]["question"].tolist()

        st.session_state.practice_settings = {
            "sets": selected_sets, "p1_topics": p1_chosen,
            "p23_topics": p23_chosen, "timer_mode": timer_mode, "df": filtered,
        }
        st.session_state.locked_practice_p1_questions = locked_p1
        st.session_state.locked_practice_p3_set = locked_p3
        st.session_state.test_start_time = time.time() if timer_mode != "No timer" else None
        st.session_state.page = "practice_run"
        st.rerun()

    if st.button("🏠 Back to Home"):
        st.session_state.page = "home"
        st.rerun()

# ─────────────────────────────────────────────
# PRACTICE RUN
# ─────────────────────────────────────────────
def page_practice_run():
    settings   = st.session_state.practice_settings
    timer_mode = settings["timer_mode"]

    st.title("📚 Practice Mode")
    st.session_state.show_read_aloud = st.toggle(
        "🔊 Show read-aloud prompts", value=st.session_state.show_read_aloud)

    if timer_mode != "No timer":
        elapsed_timer_bar()

    st.markdown("---")

    # ── Part 1 ──
    if settings["p1_topics"]:
        st.header("Part 1")
        for topic in settings["p1_topics"]:
            st.subheader(f"Topic: {topic}")
            chosen_qs = st.session_state.locked_practice_p1_questions.get(topic, [])

            if st.session_state.show_read_aloud:
                for p in get_read_aloud_prompts("1", topic):
                    st.info(f"🔊 {p}")
            for r in get_reminders("1"):
                st.warning(r)

            for i, q in enumerate(chosen_qs):
                col_q, col_t = st.columns([3, 1])
                with col_q:
                    st.markdown(f"**Q{i+1}.** {q}")
                with col_t:
                    if timer_mode == "Countdown":
                        compact_timer(f"prac_p1_{topic}_{i}", 30)
            st.markdown("---")

    # ── Part 2 & 3 ──
    if settings["p23_topics"]:
        df = settings["df"]
        for topic in settings["p23_topics"]:
            st.header(f"Part 2 — {topic}")
            p2_qs = df[(df["part"] == "2") & (df["topic"] == topic)]["question"].tolist()
            if p2_qs:
                if st.session_state.show_read_aloud:
                    for p in get_read_aloud_prompts("2", topic):
                        st.info(f"🔊 {p}")
                for r in get_reminders("2"):
                    st.warning(r)
                st.markdown(p2_qs[0].replace("\n", "\n\n"))
                if timer_mode == "Countdown":
                    compact_timer(f"prac_p2_prep_{topic}", 60, "Prep (1 min)")
                    compact_timer(f"prac_p2_speak_{topic}", 120, "Speaking (2 min)")
            st.markdown("---")

            st.header(f"Part 3 — {topic}")
            set_qs = st.session_state.locked_practice_p3_set.get(topic, [])
            if set_qs:
                if st.session_state.show_read_aloud:
                    for p in get_read_aloud_prompts("3", topic):
                        st.info(f"🔊 {p}")
                for r in get_reminders("3"):
                    st.warning(r)
                for i, q in enumerate(set_qs):
                    col_q, col_t = st.columns([3, 1])
                    with col_q:
                        for line in q.split("\n"):
                            st.markdown(f"**Q{i+1}.** {line}")
                    with col_t:
                        if timer_mode == "Countdown":
                            compact_timer(f"prac_p3_{topic}_{i}", 45)
            else:
                st.info("No Part 3 questions available for this topic.")
            st.markdown("---")

    if st.button("🏠 Back to Home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

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
        filtered     = df[df["set"].isin(selected_sets)]
        p1_topics    = filtered[filtered["part"] == "1"]["topic"].unique().tolist()
        p2_topics    = filtered[filtered["part"] == "2"]["topic"].unique().tolist()
        p3_topics    = filtered[filtered["part"] == "3"]["topic"].unique().tolist()
        paired       = [t for t in p2_topics if t in p3_topics]

        if len(p1_topics) < 3:
            st.error("Not enough Part 1 topics. Need at least 3.")
            return
        if not paired:
            st.error("No paired Part 2 & 3 topics found. Check that topic names match exactly.")
            return

        chosen_p1  = random.sample(p1_topics, 3)
        chosen_p23 = random.choice(paired)

        locked_p1 = {}
        for topic in chosen_p1:
            qs = filtered[(filtered["part"] == "1") & (filtered["topic"] == topic)]["question"].tolist()
            locked_p1[topic] = random.sample(qs, min(4, len(qs)))

        p3df     = filtered[(filtered["part"] == "3") & (filtered["topic"] == chosen_p23)]
        avail_p3 = p3df["question_set"].unique().tolist()
        locked_p3 = p3df[p3df["question_set"] == random.choice(avail_p3)]["question"].tolist() if avail_p3 else []

        st.session_state.test_questions          = {"p1_topics": chosen_p1, "p23_topic": chosen_p23, "df": filtered}
        st.session_state.locked_p1_questions     = locked_p1
        st.session_state.locked_p3_set           = locked_p3
        st.session_state.test_start_time         = time.time()
        st.session_state.test_log                = []
        st.session_state.page                    = "test_part1"
        st.rerun()

    if st.button("🏠 Back to Home"):
        st.session_state.page = "home"
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
            for p in get_read_aloud_prompts("1", topic):
                st.info(f"🔊 {p}")
        for r in get_reminders("1"):
            st.warning(r)

        for i, q in enumerate(chosen_qs):
            col_q, col_t = st.columns([3, 1])
            with col_q:
                st.markdown(f"**Q{i+1}.** {q}")
            with col_t:
                compact_timer(f"test_p1_{topic}_{i}", 30)
        st.markdown("---")

    if st.button("➡ Continue to Part 2", use_container_width=True):
        st.session_state.page = "test_part2"
        st.rerun()

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
        if st.session_state.show_read_aloud:
            for p in get_read_aloud_prompts("2", topic):
                st.info(f"🔊 {p}")
        for r in get_reminders("2"):
            st.warning(r)
        st.markdown(p2_qs[0].replace("\n", "\n\n"))
        st.markdown("&nbsp;")
        compact_timer("test_p2_prep",  60,  "Prep (1 min)")
        compact_timer("test_p2_speak", 120, "Speaking (2 min)")
    else:
        st.error("No Part 2 question found for this topic.")

    st.markdown("---")
    if st.button("➡ Continue to Part 3", use_container_width=True):
        st.session_state.page = "test_part3"
        st.rerun()

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
            for p in get_read_aloud_prompts("3", topic):
                st.info(f"🔊 {p}")
        for r in get_reminders("3"):
            st.warning(r)

        for i, q in enumerate(set_qs):
            col_q, col_t = st.columns([3, 1])
            with col_q:
                for line in q.split("\n"):
                    st.markdown(f"**Q{i+1}.** {line}")
            with col_t:
                compact_timer(f"test_p3_{i}", 45)
            st.markdown("---")
    else:
        st.warning("No Part 3 questions found for this topic.")

    if st.button("✅ End Test & See Report", use_container_width=True):
        st.session_state.test_end_time = time.time()
        st.session_state.page = "test_report"
        st.rerun()

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
    for t in tq["p1_topics"]:
        st.markdown(f"- {t}")
    st.markdown(f"**Part 2 & 3:** {tq['p23_topic']}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Test", use_container_width=True):
            for key in ["test_questions", "test_start_time", "test_end_time",
                        "locked_p1_questions", "locked_p3_set"]:
                st.session_state.pop(key, None)
            st.session_state.page = "test_setup"
            st.rerun()
    with col2:
        if st.button("🏠 Back to Home", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# ─────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────
page = st.session_state.page
if page == "home":             page_home()
elif page == "practice_setup": page_practice_setup()
elif page == "practice_run":   page_practice_run()
elif page == "test_setup":     page_test_setup()
elif page == "test_part1":     page_test_part1()
elif page == "test_part2":     page_test_part2()
elif page == "test_part3":     page_test_part3()
elif page == "test_report":    page_test_report()
