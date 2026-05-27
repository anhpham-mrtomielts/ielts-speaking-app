import streamlit as st
import pandas as pd
import random
import time

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
        return ["⏱ Press **Start Timer** before asking each question."]
    elif part == "2":
        return [
            "⏱ Press **Start Prep Timer** after handing the card.",
            "⏱ Press **Start Speaking Timer** when candidate begins.",
        ]
    elif part == "3":
        return ["⏱ Press **Start Timer** before asking each question."]
    return []

# ─────────────────────────────────────────────
# TIMER HELPERS
# ─────────────────────────────────────────────
def format_time(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def show_elapsed_timer():
    if "test_start_time" in st.session_state and st.session_state.test_start_time:
        elapsed = time.time() - st.session_state.test_start_time
        st.markdown(
            f"<div style='text-align:center; font-size:1.1rem; color:gray;'>⏱ Total elapsed: <b>{format_time(elapsed)}</b></div>",
            unsafe_allow_html=True,
        )

def countdown_timer_widget(key, duration, label="Timer"):
    timer_key = f"timer_{key}_running"
    start_key = f"timer_{key}_start"

    if timer_key not in st.session_state:
        st.session_state[timer_key] = False
        st.session_state[start_key] = None

    col1, col2 = st.columns([2, 1])
    with col1:
        if not st.session_state[timer_key]:
            remaining = duration
        else:
            elapsed = time.time() - st.session_state[start_key]
            remaining = max(0, duration - elapsed)

        if remaining == 0 and st.session_state[timer_key]:
            st.error(f"⚠️ {label} is up! Examiner — please decide.")
            st.session_state[timer_key] = False
        else:
            color = "red" if remaining <= 10 and st.session_state[timer_key] else "black"
            st.markdown(
                f"<div style='font-size:2rem; font-weight:bold; color:{color};'>{format_time(remaining)}</div>",
                unsafe_allow_html=True,
            )

    with col2:
        if not st.session_state[timer_key]:
            if st.button(f"▶ Start {label}", key=f"btn_{key}"):
                st.session_state[timer_key] = True
                st.session_state[start_key] = time.time()
                st.rerun()
        else:
            if st.button(f"⏹ Stop {label}", key=f"btn_{key}"):
                st.session_state[timer_key] = False
                st.rerun()

    if st.session_state[timer_key] and remaining > 0:
        time.sleep(1)
        st.rerun()

# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "page": "home",
        "mode": None,
        "df": None,
        "test_questions": None,
        "current_part": None,
        "current_q_index": 0,
        "current_topic_index": 0,
        "test_start_time": None,
        "test_end_time": None,
        "show_read_aloud": True,
        "practice_settings": {},
        "test_log": [],
        # Locked question selections (never re-randomized)
        "locked_p1_questions": {},   # {topic: [q1, q2, ...]}
        "locked_p3_set": None,
        "locked_practice_p1_questions": {},
        "locked_practice_p3_set": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

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
        p1_chosen = random.sample(selected_p1_topics, min(num_p1_topics, len(selected_p1_topics))) if selected_p1_topics else []
        p23_chosen = random.sample(selected_p23_topics, min(num_p23_topics, len(selected_p23_topics))) if selected_p23_topics else []

        # Lock questions NOW before any timer refreshes
        locked_p1 = {}
        for topic in p1_chosen:
            topic_qs = filtered[(filtered["part"] == "1") & (filtered["topic"] == topic)]["question"].tolist()
            locked_p1[topic] = random.sample(topic_qs, min(4, len(topic_qs)))

        locked_p3 = {}
        for topic in p23_chosen:
            p3_sets = filtered[(filtered["part"] == "3") & (filtered["topic"] == topic)]
            available = p3_sets["question_set"].unique().tolist()
            if available:
                chosen_set = random.choice(available)
                locked_p3[topic] = p3_sets[p3_sets["question_set"] == chosen_set]["question"].tolist()

        st.session_state.practice_settings = {
            "sets": selected_sets,
            "p1_topics": p1_chosen,
            "p23_topics": p23_chosen,
            "timer_mode": timer_mode,
            "df": filtered,
        }
        st.session_state.locked_practice_p1_questions = locked_p1
        st.session_state.locked_practice_p3_set = locked_p3
        st.session_state.test_start_time = time.time()
        st.session_state.page = "practice_run"
        st.rerun()

    if st.button("🏠 Back to Home"):
        st.session_state.page = "home"
        st.rerun()

# ─────────────────────────────────────────────
# PRACTICE RUN
# ─────────────────────────────────────────────
def page_practice_run():
    settings = st.session_state.practice_settings
    timer_mode = settings["timer_mode"]

    st.title("📚 Practice Mode")
    st.session_state.show_read_aloud = st.toggle("🔊 Show read-aloud prompts", value=st.session_state.show_read_aloud)

    if timer_mode == "Elapsed time":
        show_elapsed_timer()

    st.markdown("---")

    # Part 1
    if settings["p1_topics"]:
        st.header("Part 1")
        for topic in settings["p1_topics"]:
            st.subheader(f"Topic: {topic}")
            # Use locked questions — never re-randomized
            chosen_qs = st.session_state.locked_practice_p1_questions.get(topic, [])

            if st.session_state.show_read_aloud:
                for prompt in get_read_aloud_prompts("1", topic):
                    st.info(f"🔊 {prompt}")
            for reminder in get_reminders("1"):
                st.warning(reminder)

            for i, q in enumerate(chosen_qs):
                st.markdown(f"**Q{i+1}.** {q}")
                if timer_mode == "Countdown":
                    countdown_timer_widget(f"prac_p1_{topic}_{i}", 30, "30s")
            st.markdown("---")

    # Part 2 & 3
    if settings["p23_topics"]:
        df = settings["df"]
        for topic in settings["p23_topics"]:
            st.header(f"Part 2 — {topic}")
            p2_qs = df[(df["part"] == "2") & (df["topic"] == topic)]["question"].tolist()
            if p2_qs:
                if st.session_state.show_read_aloud:
                    for prompt in get_read_aloud_prompts("2", topic):
                        st.info(f"🔊 {prompt}")
                for reminder in get_reminders("2"):
                    st.warning(reminder)
                st.markdown(p2_qs[0].replace("\n", "\n\n"))
                if timer_mode == "Countdown":
                    countdown_timer_widget(f"prac_p2_prep_{topic}", 60, "1 min Prep")
                    countdown_timer_widget(f"prac_p2_speak_{topic}", 120, "2 min Speaking")

            st.markdown("---")
            st.header(f"Part 3 — {topic}")
            # Use locked Part 3 questions
            set_qs = st.session_state.locked_practice_p3_set.get(topic, [])
            if set_qs:
                if st.session_state.show_read_aloud:
                    for prompt in get_read_aloud_prompts("3", topic):
                        st.info(f"🔊 {prompt}")
                for reminder in get_reminders("3"):
                    st.warning(reminder)
                for i, q in enumerate(set_qs):
                    for line in q.split("\n"):
                        st.markdown(f"**Q{i+1}.** {line}")
                    if timer_mode == "Countdown":
                        countdown_timer_widget(f"prac_p3_{topic}_{i}", 45, "45s")
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
    st.session_state.df = df

    available_sets = sorted(df["set"].unique().tolist())
    selected_sets = st.multiselect("Select question set(s) to draw from:", available_sets, default=available_sets[:1])

    if st.button("▶ Start Test", use_container_width=True):
        if not selected_sets:
            st.warning("Please select at least one question set.")
            return
        filtered = df[df["set"].isin(selected_sets)]
        p1_topics = filtered[filtered["part"] == "1"]["topic"].unique().tolist()
        p2_topics = filtered[filtered["part"] == "2"]["topic"].unique().tolist()
        p3_topics = filtered[filtered["part"] == "3"]["topic"].unique().tolist()
        paired_topics = [t for t in p2_topics if t in p3_topics]

        if len(p1_topics) < 3:
            st.error("Not enough Part 1 topics in the selected set(s). Need at least 3.")
            return
        if not paired_topics:
            st.error("No paired Part 2 & 3 topics found. Make sure topic names match exactly.")
            return

        chosen_p1 = random.sample(p1_topics, 3)
        chosen_p23 = random.choice(paired_topics)

        # Lock all questions NOW before any timer refreshes
        locked_p1 = {}
        for topic in chosen_p1:
            topic_qs = filtered[(filtered["part"] == "1") & (filtered["topic"] == topic)]["question"].tolist()
            locked_p1[topic] = random.sample(topic_qs, min(4, len(topic_qs)))

        p3_sets_df = filtered[(filtered["part"] == "3") & (filtered["topic"] == chosen_p23)]
        available_p3 = p3_sets_df["question_set"].unique().tolist()
        locked_p3_qs = []
        if available_p3:
            chosen_set = random.choice(available_p3)
            locked_p3_qs = p3_sets_df[p3_sets_df["question_set"] == chosen_set]["question"].tolist()

        st.session_state.test_questions = {
            "p1_topics": chosen_p1,
            "p23_topic": chosen_p23,
            "df": filtered,
        }
        st.session_state.locked_p1_questions = locked_p1
        st.session_state.locked_p3_set = locked_p3_qs
        st.session_state.test_start_time = time.time()
        st.session_state.test_log = []
        st.session_state.page = "test_part1"
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
    show_elapsed_timer()
    st.markdown("---")

    for topic in tq["p1_topics"]:
        st.subheader(f"Topic: {topic}")
        # Use locked questions — never re-randomized
        chosen_qs = st.session_state.locked_p1_questions.get(topic, [])

        if st.session_state.show_read_aloud:
            for prompt in get_read_aloud_prompts("1", topic):
                st.info(f"🔊 {prompt}")
        for reminder in get_reminders("1"):
            st.warning(reminder)

        for i, q in enumerate(chosen_qs):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**Q{i+1}.** {q}")
            with col2:
                st.button("⏭ Skip", key=f"skip_p1_{topic}_{i}")
            countdown_timer_widget(f"test_p1_{topic}_{i}", 30, "30s")
        st.markdown("---")

    if st.button("➡ Continue to Part 2", use_container_width=True):
        st.session_state.page = "test_part2"
        st.rerun()

# ─────────────────────────────────────────────
# TEST — PART 2
# ─────────────────────────────────────────────
def page_test_part2():
    tq = st.session_state.test_questions
    df = tq["df"]
    topic = tq["p23_topic"]

    st.title("🎯 Test Mode — Part 2")
    st.subheader(f"Topic: {topic}")
    st.session_state.show_read_aloud = st.toggle("🔊 Show read-aloud prompts", value=st.session_state.show_read_aloud)
    show_elapsed_timer()
    st.markdown("---")

    p2_qs = df[(df["part"] == "2") & (df["topic"] == topic)]["question"].tolist()
    if p2_qs:
        if st.session_state.show_read_aloud:
            for prompt in get_read_aloud_prompts("2", topic):
                st.info(f"🔊 {prompt}")
        for reminder in get_reminders("2"):
            st.warning(reminder)
        st.markdown(p2_qs[0].replace("\n", "\n\n"))
        countdown_timer_widget("test_p2_prep", 60, "1 min Prep")
        countdown_timer_widget("test_p2_speak", 120, "2 min Speaking")
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
    tq = st.session_state.test_questions
    topic = tq["p23_topic"]

    st.title("🎯 Test Mode — Part 3")
    st.subheader(f"Topic: {topic}")
    st.session_state.show_read_aloud = st.toggle("🔊 Show read-aloud prompts", value=st.session_state.show_read_aloud)
    show_elapsed_timer()
    st.markdown("---")

    # Use locked questions — never re-randomized
    set_qs = st.session_state.locked_p3_set

    if set_qs:
        if st.session_state.show_read_aloud:
            for prompt in get_read_aloud_prompts("3", topic):
                st.info(f"🔊 {prompt}")
        for reminder in get_reminders("3"):
            st.warning(reminder)

        for i, q in enumerate(set_qs):
            col1, col2 = st.columns([4, 1])
            with col1:
                for line in q.split("\n"):
                    st.markdown(f"**Q{i+1}.** {line}")
            with col2:
                st.button("⏭ Skip", key=f"skip_p3_{i}")
            countdown_timer_widget(f"test_p3_{i}", 45, "45s")
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
                if key in st.session_state:
                    del st.session_state[key]
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

if page == "home":
    page_home()
elif page == "practice_setup":
    page_practice_setup()
elif page == "practice_run":
    page_practice_run()
elif page == "test_setup":
    page_test_setup()
elif page == "test_part1":
    page_test_part1()
elif page == "test_part2":
    page_test_part2()
elif page == "test_part3":
    page_test_part3()
elif page == "test_report":
    page_test_report()
