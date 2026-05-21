from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from click import prompt
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for

from google import genai
from flask import jsonify


load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "digital-twin-demo-secret-key")
app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

client = genai.Client(
    api_key="AIzaSyD-iIJe2cSMA8Rm73Ut4tHzNel1_khRPPA"
)
DIMENSIONS = {
    "introversion_extroversion": {
        "low": "Introverted",
        "mid": "Ambivert",
        "high": "Extroverted",
        "label_low": "Introverted",
        "label_high": "Extroverted",
    },
    "risk_level": {
        "low": "Cautious",
        "mid": "Balanced",
        "high": "Bold",
        "label_low": "Cautious",
        "label_high": "Bold",
    },
    "logical_emotional": {
        "low": "Emotion-led",
        "mid": "Balanced",
        "high": "Logic-led",
        "label_low": "Emotion-led",
        "label_high": "Logic-led",
    },
    "planning_spontaneity": {
        "low": "Spontaneous",
        "mid": "Flexible",
        "high": "Planner",
        "label_low": "Spontaneous",
        "label_high": "Planner",
    },
}


def scale_question(question_id: int, section: str, text: str, metric_map: dict[str, dict[str, int]], left: str = "1", right: str = "10") -> dict[str, Any]:
    return {
        "id": question_id,
        "section": section,
        "text": text,
        "type": "scale",
        "min": 1,
        "max": 10,
        "left": left,
        "right": right,
        "metric_map": metric_map,
    }


def radio_question(question_id: int, section: str, text: str, options: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": question_id,
        "section": section,
        "text": text,
        "type": "radio",
        "options": options,
    }


QUESTIONS: list[dict[str, Any]] = [

    # =====================================================
    # HABITS & ROUTINE
    # =====================================================

    radio_question(
        1,
        "Habits & Routine",
        "How do you usually begin your day?",
        [
            {"label": "With a structured plan", "scores": {"planning_spontaneity": 12}},
            {"label": "With a rough idea of tasks", "scores": {"planning_spontaneity": 6}},
            {"label": "Depends on the day", "scores": {"planning_spontaneity": 0}},
            {"label": "I decide things spontaneously", "scores": {"planning_spontaneity": -8}},
            {"label": "I completely go with the flow", "scores": {"planning_spontaneity": -12}},
        ],
    ),

    radio_question(
        2,
        "Habits & Routine",
        "When your plans suddenly change, how do you react?",
        [
            {"label": "Adapt calmly", "scores": {"logical_emotional": 10}},
            {"label": "Feel stressed but adjust", "scores": {"logical_emotional": -2}},
            {"label": "Enjoy the unpredictability", "scores": {"risk_level": 8}},
            {"label": "Feel frustrated immediately", "scores": {"logical_emotional": -8}},
            {"label": "Need time to mentally adjust", "scores": {"planning_spontaneity": 4}},
        ],
    ),

    scale_question(
        3,
        "Habits & Routine",
        "How consistent are your daily habits? (1–10 scale)",
        {
            "planning_spontaneity": {"direction": 1, "weight": 14}
        },
        "Very inconsistent",
        "Highly consistent",
    ),

    radio_question(
        4,
        "Habits & Routine",
        "How do you handle deadlines?",
        [
            {"label": "Finish tasks early", "scores": {"planning_spontaneity": 12}},
            {"label": "Work steadily over time", "scores": {"planning_spontaneity": 8}},
            {"label": "Need pressure to work efficiently", "scores": {"risk_level": 4}},
            {"label": "Often procrastinate", "scores": {"planning_spontaneity": -10}},
            {"label": "Completely improvise at the last moment", "scores": {"planning_spontaneity": -14}},
        ],
    ),

    scale_question(
        5,
        "Habits & Routine",
        "How organized is your lifestyle? (1–10 scale)",
        {
            "planning_spontaneity": {"direction": 1, "weight": 12}
        },
        "Very disorganized",
        "Highly organized",
    ),

    # =====================================================
    # VALUES
    # =====================================================

    radio_question(
        6,
        "Values",
        "What motivates you the most in life?",
        [
            {"label": "Achievement and success", "scores": {"logical_emotional": 8}},
            {"label": "Freedom and independence", "scores": {"risk_level": 10}},
            {"label": "Security and stability", "scores": {"planning_spontaneity": 12}},
            {"label": "Relationships and belonging", "scores": {"introversion_extroversion": 10}},
            {"label": "Growth and learning", "scores": {"logical_emotional": 6, "risk_level": 4}},
        ],
    ),

    radio_question(
        7,
        "Values",
        "Would you choose passion over financial stability?",
        [
            {"label": "Definitely yes", "scores": {"risk_level": 10}},
            {"label": "Probably yes", "scores": {"risk_level": 6}},
            {"label": "Depends on the situation", "scores": {"logical_emotional": 4}},
            {"label": "Probably not", "scores": {"planning_spontaneity": 6}},
            {"label": "Definitely not", "scores": {"planning_spontaneity": 12}},
        ],
    ),

    scale_question(
        8,
        "Values",
        "How important is long-term stability in your life decisions? (1–10 scale)",
        {
            "planning_spontaneity": {"direction": 1, "weight": 14},
            "risk_level": {"direction": -1, "weight": 8}
        },
        "Not important",
        "Extremely important",
    ),

    radio_question(
        9,
        "Values",
        "Which matters more to you?",
        [
            {"label": "Personal happiness", "scores": {"logical_emotional": -2}},
            {"label": "Career growth", "scores": {"planning_spontaneity": 6}},
            {"label": "Financial success", "scores": {"risk_level": -2}},
            {"label": "Strong relationships", "scores": {"introversion_extroversion": 8}},
            {"label": "Freedom to explore life", "scores": {"risk_level": 8}},
        ],
    ),

    scale_question(
        10,
        "Values",
        "How much do other people’s opinions affect your decisions? (1–10 scale)",
        {
            "introversion_extroversion": {"direction": 1, "weight": 8},
            "logical_emotional": {"direction": -1, "weight": 4}
        },
        "Not at all",
        "Very strongly",
    ),

    # =====================================================
    # RISK & UNCERTAINTY
    # =====================================================

    radio_question(
        11,
        "Risk & Uncertainty",
        "You receive a risky opportunity with high rewards. What do you do?",
        [
            {"label": "Take it immediately", "scores": {"risk_level": 14}},
            {"label": "Research before deciding", "scores": {"logical_emotional": 12}},
            {"label": "Seek advice from others", "scores": {"introversion_extroversion": 6}},
            {"label": "Avoid the risk completely", "scores": {"risk_level": -12}},
            {"label": "Take a smaller safer version of the risk", "scores": {"risk_level": 4}},
        ],
    ),

    scale_question(
        12,
        "Risk & Uncertainty",
        "How comfortable are you with uncertainty? (1–10 scale)",
        {
            "risk_level": {"direction": 1, "weight": 14}
        },
        "Very uncomfortable",
        "Very comfortable",
    ),

    radio_question(
        13,
        "Risk & Uncertainty",
        "How do you react when things don't go according to plan?",
        [
            {"label": "Stay calm and solve the issue", "scores": {"logical_emotional": 12}},
            {"label": "Feel anxious but adapt", "scores": {"logical_emotional": -2}},
            {"label": "Act quickly without overthinking", "scores": {"risk_level": 8}},
            {"label": "Overthink the situation", "scores": {"planning_spontaneity": 6}},
            {"label": "Seek emotional support", "scores": {"introversion_extroversion": 6}},
        ],
    ),

    radio_question(
        14,
        "Risk & Uncertainty",
        "Would you relocate alone to a completely new city for growth?",
        [
            {"label": "Definitely yes", "scores": {"risk_level": 12}},
            {"label": "Probably yes", "scores": {"risk_level": 6}},
            {"label": "Only if necessary", "scores": {"planning_spontaneity": 4}},
            {"label": "Probably not", "scores": {"risk_level": -6}},
            {"label": "Definitely not", "scores": {"risk_level": -12}},
        ],
    ),

    scale_question(
        15,
        "Risk & Uncertainty",
        "How often do you step outside your comfort zone? (1–10 scale)",
        {
            "risk_level": {"direction": 1, "weight": 12}
        },
        "Rarely",
        "Very often",
    ),

    # =====================================================
    # SOCIAL & RELATIONSHIPS
    # =====================================================

    radio_question(
        16,
        "Social & Relationships",
        "At a social gathering, you usually:",
        [
            {"label": "Talk to many people confidently", "scores": {"introversion_extroversion": 14}},
            {"label": "Interact with a few people", "scores": {"introversion_extroversion": 4}},
            {"label": "Observe before interacting", "scores": {"logical_emotional": 4}},
            {"label": "Prefer staying quiet", "scores": {"introversion_extroversion": -8}},
            {"label": "Avoid interaction completely", "scores": {"introversion_extroversion": -14}},
        ],
    ),

    radio_question(
        17,
        "Social & Relationships",
        "How do you usually handle conflicts?",
        [
            {"label": "Address it calmly and directly", "scores": {"logical_emotional": 10}},
            {"label": "Avoid conflict if possible", "scores": {"introversion_extroversion": -4}},
            {"label": "Get emotional during arguments", "scores": {"logical_emotional": -10}},
            {"label": "Try to understand both sides", "scores": {"logical_emotional": 8}},
            {"label": "Need time alone before responding", "scores": {"introversion_extroversion": -2}},
        ],
    ),

    scale_question(
        18,
        "Social & Relationships",
        "How energized do you feel after social interaction? (1–10 scale)",
        {
            "introversion_extroversion": {"direction": 1, "weight": 14}
        },
        "Very drained",
        "Very energized",
    ),

    radio_question(
        19,
        "Social & Relationships",
        "What role do you usually take in a team?",
        [
            {"label": "Leader", "scores": {"introversion_extroversion": 12}},
            {"label": "Planner/strategist", "scores": {"logical_emotional": 10}},
            {"label": "Supportive contributor", "scores": {"introversion_extroversion": 4}},
            {"label": "Independent worker", "scores": {"introversion_extroversion": -8}},
            {"label": "Observer", "scores": {"introversion_extroversion": -12}},
        ],
    ),

    scale_question(
        20,
        "Social & Relationships",
        "How important are close relationships in your life? (1–10 scale)",
        {
            "introversion_extroversion": {"direction": 1, "weight": 10}
        },
        "Not important",
        "Extremely important",
    ),

    # =====================================================
    # DECISION MAKING
    # =====================================================

    radio_question(
        21,
        "Decision Making",
        "How do you usually make important decisions?",
        [
            {"label": "Analyze all available information", "scores": {"logical_emotional": 14}},
            {"label": "Trust intuition", "scores": {"logical_emotional": -10}},
            {"label": "Balance logic and emotions", "scores": {"logical_emotional": 4}},
            {"label": "Ask others for advice", "scores": {"introversion_extroversion": 6}},
            {"label": "Decide quickly and adapt later", "scores": {"risk_level": 8}},
        ],
    ),

    scale_question(
        22,
        "Decision Making",
        "How much do emotions influence your decisions? (1–10 scale)",
        {
            "logical_emotional": {"direction": -1, "weight": 16}
        },
        "Not at all",
        "Very strongly",
    ),

    radio_question(
        23,
        "Decision Making",
        "After making a wrong decision, what do you usually do?",
        [
            {"label": "Analyze and learn from it", "scores": {"logical_emotional": 12}},
            {"label": "Move on quickly", "scores": {"risk_level": 4}},
            {"label": "Feel regret for a long time", "scores": {"logical_emotional": -10}},
            {"label": "Seek support from others", "scores": {"introversion_extroversion": 6}},
            {"label": "Try to fix the mistake immediately", "scores": {"planning_spontaneity": 6}},
        ],
    ),

    radio_question(
        24,
        "Decision Making",
        "When faced with uncertainty, what do you trust more?",
        [
            {"label": "Logic and evidence", "scores": {"logical_emotional": 14}},
            {"label": "Past experiences", "scores": {"planning_spontaneity": 8}},
            {"label": "Instinct and emotions", "scores": {"logical_emotional": -10}},
            {"label": "Advice from trusted people", "scores": {"introversion_extroversion": 6}},
            {"label": "Immediate action", "scores": {"risk_level": 8}},
        ],
    ),

    scale_question(
        25,
        "Decision Making",
        "How confident are you in your own decisions? (1–10 scale)",
        {
            "logical_emotional": {"direction": 1, "weight": 8},
            "risk_level": {"direction": 1, "weight": 6}
        },
        "Not confident",
        "Very confident",
    ),

]


SECTION_ORDER = [
    "Habits & Routine",
    "Values",
    "Risk & Uncertainty",
    "Social & Relationships",
    "Decision Making",
]


def group_questions() -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in QUESTIONS:
        grouped[question["section"]].append(question)
    return [{"title": section, "questions": grouped[section]} for section in SECTION_ORDER]


def update_scores(scores: dict[str, float], delta: dict[str, float]) -> None:
    for key, value in delta.items():
        scores[key] = scores.get(key, 50.0) + value


def score_scale(question: dict[str, Any], raw_value: str) -> dict[str, float]:
    value = int(raw_value)
    centered = value - 5.5
    delta: dict[str, float] = {}
    for metric, config in question["metric_map"].items():
        direction = config["direction"]
        weight = config["weight"]
        delta[metric] = delta.get(metric, 0.0) + ((centered / 4.5) * weight * direction)
    return delta


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def classify_dimension(score: float, low_label: str, high_label: str) -> str:
    if score >= 60:
        return high_label
    if score <= 40:
        return low_label
    return "Balanced"


def build_archetype(scores: dict[str, float]) -> str:
    extroversion = scores["introversion_extroversion"]
    risk = scores["risk_level"]
    logic = scores["logical_emotional"]
    planning = scores["planning_spontaneity"]

    if extroversion >= 60 and risk >= 60 and planning <= 50:
        return "Visionary Catalyst"
    if extroversion >= 60 and logic >= 60 and planning >= 55:
        return "Strategic Connector"
    if extroversion <= 40 and logic >= 60 and planning >= 60:
        return "Analytical Architect"
    if extroversion <= 40 and planning >= 60 and risk <= 45:
        return "Grounded Strategist"
    if risk >= 60 and planning <= 50:
        return "Adaptive Explorer"
    if planning >= 60 and logic >= 60:
        return "Deliberate Analyst"
    return "Adaptive Navigator"


def build_summary(scores: dict[str, float]) -> str:
    labels = {
        key: classify_dimension(score, values["low"], values["high"])
        for key, score in scores.items()
        for values in [DIMENSIONS[key]]
    }
    archetype = build_archetype(scores)
    return (
        f"Your Digital Twin suggests you are a {archetype.lower()} with a {labels['logical_emotional'].lower()} mindset, "
        f"a {labels['planning_spontaneity'].lower()} decision style, and a {labels['risk_level'].lower()} comfort zone."
    )


def generate_scenarios(scores: dict[str, float]) -> list[dict[str, str]]:
    extroversion = scores["introversion_extroversion"]
    risk = scores["risk_level"]
    logic = scores["logical_emotional"]
    planning = scores["planning_spontaneity"]

    if risk >= 60:
        risky_response = "you move quickly, scan for upside, and commit if the opportunity feels worth the exposure."
    else:
        risky_response = "you slow the moment down, build a fallback, and wait for more certainty before acting."

    if extroversion >= 60:
        conflict_response = "you will likely talk it through directly, using conversation to reset the room."
    else:
        conflict_response = "you will likely observe first, process privately, and step in once the tension is clearer."

    if logic >= 60:
        setback_response = "you will analyze the mistake, extract the lesson, and turn it into a better next move."
    else:
        setback_response = "you may feel the emotional weight first, then recover through support and reflection."

    if planning >= 60:
        uncertainty_response = "you create structure around uncertainty and reduce noise before making a final call."
    else:
        uncertainty_response = "you prefer to test the waters, adapt as you go, and keep options open."

    return [
        {"title": "In a risky situation", "body": f"You are likely to {risky_response}"},
        {"title": "During a team disagreement", "body": f"You are likely to {conflict_response}"},
        {"title": "After a wrong decision", "body": f"You are likely to {setback_response}"},
        {"title": "When facing uncertainty", "body": f"You are likely to {uncertainty_response}"},
    ]


def build_profile(responses: dict[str, str]) -> dict[str, Any]:
    scores = {key: 50.0 for key in DIMENSIONS}

    for question in QUESTIONS:
        response = responses.get(str(question["id"]))
        if not response:
            continue
        if question["type"] == "scale":
            update_scores(scores, score_scale(question, response))
            continue
        selected_option = next((option for option in question["options"] if option["label"] == response), None)
        if selected_option:
            update_scores(scores, selected_option["scores"])

    for key in scores:
        scores[key] = clamp_score(scores[key])

    labels = {
        "introversion_extroversion": classify_dimension(scores["introversion_extroversion"], "Introverted", "Extroverted"),
        "risk_level": classify_dimension(scores["risk_level"], "Cautious", "Bold"),
        "logical_emotional": classify_dimension(scores["logical_emotional"], "Emotion-led", "Logic-led"),
        "planning_spontaneity": classify_dimension(scores["planning_spontaneity"], "Spontaneous", "Planner"),
    }

    return {
        "scores": scores,
        "labels": labels,
        "archetype": build_archetype(scores),
        "summary": build_summary(scores),
        "scenarios": generate_scenarios(scores),
        "recommendation": "Lean into deliberate experimentation: keep your strongest strengths, but create a small feedback loop before major decisions.",
        "answers": responses,
    }


@app.route("/")
def home() -> str:
    return render_template("home.html", active_page="home")


@app.route("/overview")
def overview() -> str:
    return render_template("overview.html", active_page="overview")


@app.route("/methodology")
def methodology() -> str:
    return render_template("methodology.html", active_page="methodology")


@app.route("/assessment", methods=["GET"])
def assessment() -> str:
    return render_template(
        "assessment.html",
        active_page="assessment",
        sections=group_questions(),
        responses=session.get("responses", {}),
    )


@app.route("/submit", methods=["POST"])
def submit_assessment() -> str:
    responses = {key[1:]: value for key, value in request.form.items() if key.startswith("q") and value}
    answered_questions = len(responses)
    if answered_questions < len(QUESTIONS):
        flash("Please answer every question to generate your Digital Twin profile.", "warning")
        session["responses"] = responses
        return redirect(url_for("assessment"))

    profile = build_profile(responses)
    session["responses"] = responses
    session["profile"] = profile
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard() -> str:
    profile = session.get("profile")
    if not profile:
        flash("Complete the assessment first to unlock your dashboard.", "info")
        return redirect(url_for("assessment"))
    return render_template("dashboard.html", active_page="dashboard", profile=profile)


@app.route("/scenarios")
def scenarios() -> str:
    profile = session.get("profile")
    if not profile:
        flash("Complete the assessment first to view predictive scenarios.", "info")
        return redirect(url_for("assessment"))
    return render_template("scenarios.html", active_page="scenarios", profile=profile)


@app.route("/reset")
def reset() -> str:
    session.clear()
    flash("Assessment reset. You can start a fresh Digital Twin profile now.", "success")
    return redirect(url_for("home"))


@app.route("/ai-insights")
def ai_insights():

    profile = session.get("profile")

    if not profile:
        return jsonify({
            "result": "No profile found."
        })

    prompt = f"""
Analyze this Digital Twin personality profile.

Archetype:
{profile['archetype']}

Summary:
{profile['summary']}

Return the response in clean HTML format using:

<h2>
<h3>
<p>
<ul>
<li>

Sections:
1. Personality Style
2. Strengths
3. Weaknesses
4. Career Tendencies
5. Social Behavior
6. Decision-Making Style
7. Final Verdict

Keep it elegant and professional.
Write it within 200 words.
"""

    try:

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        return jsonify({
            "result": response.text
        })

    except Exception as e:

        return jsonify({
            "result": str(e)
        })

@app.route("/simulate-scenario")
def simulate_scenario():

    profile = session.get("profile")

    if not profile:
        return jsonify({
            "result": "No profile found."
        })

    scenario = request.args.get("scenario")

    prompt = f"""

You are an AI behavioral analyst.

User Archetype:
{profile['archetype']}

Behavior Summary:
{profile['summary']}

Simulate how this person would behave in this situation:

{scenario}

Explain in very simple and clear language
that normal people can easily understand.

Return response in clean HTML using:
<h2>
<h3>
<p>
<ul>
<li>

Include:
1. Emotional Response
2. Thinking Pattern
3. Likely Actions
4. Social Behavior
5. Predicted Outcome

Keep the tone smart, modern, and human-friendly.
Avoid futuristic or robotic words.
Limit to 180 words.
"""

    try:

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        return jsonify({
            "result": response.text
        })

    except Exception as e:

        return jsonify({
            "result": str(e)
        })
    
    
if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "1").strip().lower() in {"1", "true", "yes", "on"}
    try:
        port = int(os.getenv("PORT", "5000"))
    except ValueError:
        port = 5000

    app.run(debug=debug, port=port)