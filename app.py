
import json
import random
from dataclasses import dataclass
from typing import List, Optional

import streamlit as st


# ---------- Data models ----------
@dataclass
class CognitiveBias:
    title: str
    definition: str
    is_authentic: bool
    reference: str
    category: str

    @classmethod
    def from_dict(cls, data: dict) -> "CognitiveBias":
        return cls(
            title=data.get("title", ""),
            definition=data.get("definition", ""),
            is_authentic=bool(data.get("is_authentic", False)),
            reference=data.get("reference", ""),
            category=data.get("category", ""),
        )


@dataclass
class Answer:
    value: Optional[bool] = None
    is_correct: Optional[bool] = None


@dataclass
class Quiz:
    biases: List[CognitiveBias]
    answers: List[Answer]
    current_index: int = 0


# ---------- Data loading ----------
def _try_and_load(fn: str):
    try:
        with open(fn, "r") as fh:
            data = json.load(fh).get("biases", [])
        return data
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        st.error(f"Failed to parse JSON in {fn}.")
        return []


def load_and_shuffle_data(limit: int = 10) -> List[dict]:
    filenames = [
        "./biases.json",
        "./data/biases.json",
        "./biases/data/biases.json",
    ]
    data = []
    for fn in filenames:
        data = _try_and_load(fn)
        if data:
            break
    if not data:
        st.stop()  # clean stop with message below
    random.shuffle(data)
    return data[:limit]


def create_quiz() -> Quiz:
    data = load_and_shuffle_data()
    biases = [CognitiveBias.from_dict(d) for d in data]
    answers = [Answer() for _ in biases]
    return Quiz(biases=biases, answers=answers, current_index=0)


# ---------- Helpers for session state ----------
def get_state():
    if "quiz" not in st.session_state:
        try:
            st.session_state.quiz = create_quiz()
        except st.runtime.scriptrunner.StopException:
            # Will be raised by st.stop() if no data found; surface message below
            pass
    if "revealed" not in st.session_state:
        st.session_state.revealed = False
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    return st.session_state


def set_answer(value: bool):
    state = get_state()
    if state.submitted:
        return
    q: Quiz = state.quiz
    i = q.current_index
    if i >= len(q.biases):
        return
    bias = q.biases[i]
    ans = q.answers[i]
    ans.value = value
    ans.is_correct = (value == bias.is_authentic)
    state.revealed = True


def go_prev():
    state = get_state()
    if state.submitted:
        return
    q: Quiz = state.quiz
    if q.current_index > 0:
        q.current_index -= 1
    ans = q.answers[q.current_index]
    state.revealed = (ans.value is not None)


def go_next():
    state = get_state()
    if state.submitted:
        return
    q: Quiz = state.quiz
    if q.current_index < len(q.biases) - 1:
        q.current_index += 1
    ans = q.answers[q.current_index]
    state.revealed = (ans.value is not None)


def all_answered(q: Quiz) -> bool:
    return all(a.value is not None for a in q.answers)


def restart_quiz():
    # reshuffle a fresh quiz
    st.session_state.quiz = create_quiz()
    st.session_state.revealed = False
    st.session_state.submitted = False


# ---------- UI pieces ----------
def show_quiz_view(q: Quiz, revealed: bool):
    i = q.current_index
    total = len(q.biases)

    bias = q.biases[i]
    ans = q.answers[i]

    with st.container(border=True):
        st.markdown(f"### Question {i + 1}: {bias.title} [{bias.category}]")
        st.markdown(f"#### { bias.definition }")


        if not revealed:
            cols = st.columns(5)
            with cols[3]:
                if st.button("Authentic", type="primary"):
                    set_answer(True)
                    st.rerun()
            with cols[4]:
                if st.button("Fake", type="primary"):
                    set_answer(False)
                    st.rerun()
        else:
            # reveal view
            if ans.value is not None:
                correct = bool(ans.is_correct)
                verdict = "Correct" if correct else "Incorrect"
                expected = "Authentic" if bias.is_authentic else "Fake"
                chosen = "Authentic" if ans.value else "Fake"
                st.markdown(f"**{verdict}.** You chose **{chosen}**. The correct answer is: **{expected}**.")
            if bias.reference:
                st.caption(f"Reference: {bias.reference}")

    q: Quiz = state.quiz
    if not all_answered(q):
        prev_col, next_col, prog_col = st.columns([1, 1, 4])
        with prev_col:
            st.button("Prev. Bias", on_click=go_prev, disabled=(i == 0))
        with prog_col:
            st.progress((i+1) / total)
        with next_col:
            st.button("Next Bias", on_click=go_next, disabled=(i == total - 1))
        


def show_results(q: Quiz):
    total = len(q.biases)
    correct = sum(1 for a in q.answers if a.is_correct)
    st.subheader(f"**Final score:** {correct}/{total}")
    for idx, (bias, ans) in enumerate(zip(q.biases, q.answers), start=1):
        with st.container(border=True):
            st.markdown(f"**{idx}. {bias.title}**")
            st.markdown(bias.definition)
            st.markdown(f"_Category: {bias.category}_")
            st.markdown("")
            chosen = "Authentic" if ans.value else "Fake" if ans.value is not None else "—"
            expected = "Authentic" if bias.is_authentic else "Fake"
            verdict = "✅ Correct" if ans.is_correct else "❌ Incorrect"
            st.write(f"{verdict} · You: **{chosen}** · Expected: **{expected}**")
            if bias.reference:
                st.caption(f"Reference: {bias.reference}")


# ---------- Page ----------
st.set_page_config(page_title="Cognitive Bias Quiz", page_icon="🧠", layout="centered")
st.title("🧠 Cognitive Bias Quiz")

state = get_state()

# If no data was found, guide the user then stop.
if "quiz" not in st.session_state or st.session_state.quiz is None:
    st.error("Could not find a biases.json file in any expected location.")
    st.markdown(
        """
Place a **biases.json** file next to the app, or in **./data/biases.json**, or **./biases/data/biases.json**.

Expected format:
```json
{
  "biases": [
    {
      "title": "Anchoring bias",
      "definition": "Example definition",
      "is_authentic": true,
      "reference": "Tversky & Kahneman, 1974",
      "category": "Decision-making"
    }
  ]
}
```
"""
    )
    st.stop()

q: Quiz = state.quiz

if state.submitted:
    show_results(q)
    st.button("Restart quiz", on_click=restart_quiz)
else:
    show_quiz_view(q, state.revealed)
    if all_answered(q):
        st.button(
            "View Results",
            on_click=lambda: setattr(state, "submitted", True),
        )
