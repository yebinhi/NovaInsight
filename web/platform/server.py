"""Diagnostic platform: project, question bank, tests, metrics, and report."""

import os
import time
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from psycopg.rows import dict_row

from i18n import channel_labels, current_lang, stage_labels, t
from workflow import build_findings, compute_metrics, generate_questions

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nova-platform-dev")
DATABASE_URL = os.environ["DATABASE_URL"]
SCHEMA_PATH = Path(os.environ.get("SCHEMA_PATH", "/app/schema.sql"))


def connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def wait_for_database():
    for _ in range(30):
        try:
            with connect() as connection:
                connection.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            time.sleep(1)
    raise SystemExit("database unavailable")


def apply_schema():
    script = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = []
    buffer = []
    for line in script.splitlines():
        if line.strip().startswith("--"):
            continue
        buffer.append(line)
        if line.rstrip().endswith(";"):
            statements.append("\n".join(buffer))
            buffer = []
    with connect() as connection:
        for statement in statements:
            connection.execute(statement)
        connection.commit()


def website_host(website):
    host = urlparse(website).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def same_site(url, website):
    host = website_host(url if "://" in url else f"https://{url}")
    official = website_host(website if "://" in website else f"https://{website}")
    return bool(host) and host == official


def normalise_website(value):
    text = value.strip()
    if text and "://" not in text:
        text = f"https://{text}"
    return text


def require_text(form, name):
    return form.get(name, "").strip()


def load_project(connection, project_id):
    project = connection.execute(
        "SELECT * FROM projects WHERE id = %s",
        (project_id,),
    ).fetchone()
    if project is None:
        abort(404)
    competitors = connection.execute(
        "SELECT * FROM competitors WHERE project_id = %s ORDER BY id",
        (project_id,),
    ).fetchall()
    return project, competitors


def load_answers(connection, project_id):
    rows = connection.execute(
        """
        SELECT answers.id, answers.body, answers.recommendation_reason,
               answers.cited_official, answers.factual_error, answers.error_note,
               answers.repeat_index, answers.question_id,
               questions.stage, questions.branded, questions.text AS question_text,
               questions.position, test_runs.channel, test_runs.model,
               test_runs.language, test_runs.region, test_runs.web_search
        FROM answers
        JOIN questions ON questions.id = answers.question_id
        JOIN test_runs ON test_runs.id = answers.test_run_id
        WHERE test_runs.project_id = %s
        ORDER BY answers.id
        """,
        (project_id,),
    ).fetchall()
    if not rows:
        return []
    ids = [row["id"] for row in rows]
    brands = connection.execute(
        """
        SELECT * FROM answer_brands
        WHERE answer_id = ANY(%s)
        ORDER BY id
        """,
        (ids,),
    ).fetchall()
    citations = connection.execute(
        """
        SELECT * FROM citations
        WHERE answer_id = ANY(%s)
        ORDER BY id
        """,
        (ids,),
    ).fetchall()
    grouped_brands = {}
    grouped_citations = {}
    for brand in brands:
        grouped_brands.setdefault(brand["answer_id"], []).append(brand)
    for citation in citations:
        grouped_citations.setdefault(citation["answer_id"], []).append(citation)
    answers = []
    for row in rows:
        item = dict(row)
        item["brands"] = grouped_brands.get(row["id"], [])
        item["citations"] = []
        competitor_mentioned = any(
            brand["role"] == "competitor" and brand["mentioned"]
            for brand in item["brands"]
        )
        for citation in grouped_citations.get(row["id"], []):
            stored = dict(citation)
            stored["competitor_mentioned"] = competitor_mentioned
            item["citations"].append(stored)
        answers.append(item)
    return answers


def answer_progress(connection, run_id):
    return connection.execute(
        """
        SELECT questions.id, questions.position, questions.stage, questions.branded,
               questions.text,
               COUNT(answers.id) AS saved
        FROM questions
        LEFT JOIN answers
          ON answers.question_id = questions.id
         AND answers.test_run_id = %s
        WHERE questions.project_id = (
          SELECT project_id FROM test_runs WHERE id = %s
        )
        GROUP BY questions.id
        ORDER BY questions.position
        """,
        (run_id, run_id),
    ).fetchall()


@app.template_filter("pct")
def percent(value):
    if value is None:
        return "—"
    return f"{value * 100:.0f}%"


@app.context_processor
def labels():
    lang = current_lang()
    return {
        "t": t,
        "lang": lang,
        "stage_labels": stage_labels(lang),
        "channel_labels": channel_labels(lang),
    }


@app.get("/language/<lang>")
def set_language(lang):
    if lang not in {"en", "zh"}:
        abort(404)
    target = request.referrer or url_for("home")
    if not target.startswith(request.host_url):
        target = url_for("home")
    response = redirect(target)
    response.set_cookie("nova_lang", lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


@app.get("/")
def home():
    with connect() as connection:
        projects = connection.execute(
            """
            SELECT projects.*,
                   (SELECT COUNT(*) FROM questions WHERE project_id = projects.id) AS question_count,
                   (SELECT COUNT(*) FROM answers
                      JOIN test_runs ON test_runs.id = answers.test_run_id
                     WHERE test_runs.project_id = projects.id) AS answer_count
            FROM projects
            ORDER BY projects.id DESC
            """
        ).fetchall()
    return render_template("project.html", mode="list", projects=projects, project=None)


@app.post("/projects")
def create_project():
    brand = require_text(request.form, "brand_name")
    website = normalise_website(request.form.get("website", ""))
    products = require_text(request.form, "products")
    country = require_text(request.form, "country")
    audience = require_text(request.form, "audience")
    hoped = request.form.get("hoped_questions", "").strip()
    if not all([brand, website, products, country, audience]):
        flash(t("flash.project_required"))
        return redirect(url_for("home"))
    competitor_rows = []
    for line in request.form.get("competitors", "").splitlines():
        line = line.strip()
        if not line:
            continue
        name, _, site = line.partition("|")
        name = name.strip()
        if name:
            competitor_rows.append((name, normalise_website(site) if site.strip() else None))
    with connect() as connection:
        project_id = connection.execute(
            """
            INSERT INTO projects
              (brand_name, website, products, country, language, audience, hoped_questions)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (brand, website, products, country, current_lang(), audience, hoped),
        ).fetchone()["id"]
        for name, site in competitor_rows:
            connection.execute(
                "INSERT INTO competitors (project_id, name, website) VALUES (%s, %s, %s)",
                (project_id, name, site),
            )
        connection.commit()
    return redirect(url_for("project_detail", project_id=project_id))


@app.get("/projects/<int:project_id>")
def project_detail(project_id):
    with connect() as connection:
        project, competitors = load_project(connection, project_id)
        counts = connection.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM questions WHERE project_id = %s) AS questions,
              (SELECT COUNT(*) FROM test_runs WHERE project_id = %s) AS runs,
              (SELECT COUNT(*) FROM answers
                 JOIN test_runs ON test_runs.id = answers.test_run_id
                WHERE test_runs.project_id = %s) AS answers
            """,
            (project_id, project_id, project_id),
        ).fetchone()
    return render_template(
        "project.html",
        mode="detail",
        project=project,
        competitors=competitors,
        counts=counts,
    )


@app.post("/projects/<int:project_id>/questions")
def create_questions(project_id):
    with connect() as connection:
        project, competitors = load_project(connection, project_id)
        existing_answers = connection.execute(
            """
            SELECT 1
            FROM answers
            JOIN test_runs ON test_runs.id = answers.test_run_id
            WHERE test_runs.project_id = %s
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
        if existing_answers:
            flash(t("flash.questions_locked"))
            return redirect(url_for("question_list", project_id=project_id))
        project["language"] = current_lang()
        connection.execute(
            "UPDATE projects SET language = %s WHERE id = %s",
            (project["language"], project_id),
        )
        questions = generate_questions(project, competitors)
        connection.execute("DELETE FROM questions WHERE project_id = %s", (project_id,))
        for item in questions:
            connection.execute(
                """
                INSERT INTO questions (project_id, position, stage, branded, text)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (project_id, item["position"], item["stage"], item["branded"], item["text"]),
            )
        connection.commit()
    flash(t("flash.generated", n=len(questions)))
    return redirect(url_for("question_list", project_id=project_id))


@app.get("/projects/<int:project_id>/questions")
def question_list(project_id):
    with connect() as connection:
        project, competitors = load_project(connection, project_id)
        questions = connection.execute(
            "SELECT * FROM questions WHERE project_id = %s ORDER BY position",
            (project_id,),
        ).fetchall()
    return render_template(
        "questions.html",
        project=project,
        competitors=competitors,
        questions=questions,
    )


@app.post("/projects/<int:project_id>/runs")
def create_run(project_id):
    model = require_text(request.form, "model")
    language = require_text(request.form, "language")
    region = require_text(request.form, "region")
    channel = request.form.get("channel", "")
    web_search = request.form.get("web_search") == "yes"
    if channel not in {"api", "consumer"} or not all([model, language, region]):
        flash(t("flash.run_required"))
        return redirect(url_for("tests", project_id=project_id))
    with connect() as connection:
        load_project(connection, project_id)
        question = connection.execute(
            "SELECT id FROM questions WHERE project_id = %s LIMIT 1",
            (project_id,),
        ).fetchone()
        if question is None:
            flash(t("flash.need_questions"))
            return redirect(url_for("question_list", project_id=project_id))
        run_id = connection.execute(
            """
            INSERT INTO test_runs (project_id, model, language, region, web_search, channel)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (project_id, model, language, region, web_search, channel),
        ).fetchone()["id"]
        connection.commit()
    return redirect(url_for("tests", project_id=project_id, run=run_id))


@app.get("/projects/<int:project_id>/tests")
def tests(project_id):
    run_id = request.args.get("run", type=int)
    question_id = request.args.get("question", type=int)
    repeat_index = request.args.get("repeat", default=1, type=int)
    if repeat_index not in {1, 2, 3}:
        repeat_index = 1
    with connect() as connection:
        project, competitors = load_project(connection, project_id)
        runs = connection.execute(
            "SELECT * FROM test_runs WHERE project_id = %s ORDER BY id DESC",
            (project_id,),
        ).fetchall()
        run = None
        progress = []
        question = None
        answer = None
        brand_flags = {}
        citations = ""
        if run_id:
            run = connection.execute(
                "SELECT * FROM test_runs WHERE id = %s AND project_id = %s",
                (run_id, project_id),
            ).fetchone()
            if run is None:
                abort(404)
            progress = answer_progress(connection, run_id)
            if question_id is None and progress:
                question_id = progress[0]["id"]
            if question_id:
                question = connection.execute(
                    "SELECT * FROM questions WHERE id = %s AND project_id = %s",
                    (question_id, project_id),
                ).fetchone()
                if question is None:
                    abort(404)
                answer = connection.execute(
                    """
                    SELECT * FROM answers
                    WHERE test_run_id = %s AND question_id = %s AND repeat_index = %s
                    """,
                    (run_id, question_id, repeat_index),
                ).fetchone()
                if answer:
                    flags = connection.execute(
                        "SELECT * FROM answer_brands WHERE answer_id = %s",
                        (answer["id"],),
                    ).fetchall()
                    brand_flags = {(item["name"], item["role"]): item for item in flags}
                    saved_citations = connection.execute(
                        "SELECT url FROM citations WHERE answer_id = %s ORDER BY id",
                        (answer["id"],),
                    ).fetchall()
                    citations = "\n".join(item["url"] for item in saved_citations)
    brands = [{"name": project["brand_name"], "role": "client"}]
    brands.extend({"name": item["name"], "role": "competitor"} for item in competitors)
    return render_template(
        "tests.html",
        project=project,
        competitors=competitors,
        runs=runs,
        run=run,
        progress=progress,
        question=question,
        repeat_index=repeat_index,
        answer=answer,
        brands=brands,
        brand_flags=brand_flags,
        citations=citations,
    )


@app.post("/projects/<int:project_id>/answers")
def save_answer(project_id):
    run_id = request.form.get("run_id", type=int)
    question_id = request.form.get("question_id", type=int)
    repeat_index = request.form.get("repeat_index", type=int)
    body = request.form.get("body", "").strip()
    reason = request.form.get("recommendation_reason", "").strip()
    error_note = request.form.get("error_note", "").strip()
    factual_error = request.form.get("factual_error") == "yes"
    urls = []
    for line in request.form.get("citations", "").splitlines():
        line = line.strip()
        if line.startswith("http://") or line.startswith("https://"):
            urls.append(line)
    if not body or run_id is None or question_id is None or repeat_index not in {1, 2, 3}:
        flash(t("flash.answer_empty"))
        return redirect(url_for("tests", project_id=project_id, run=run_id, question=question_id, repeat=repeat_index or 1))
    with connect() as connection:
        project, competitors = load_project(connection, project_id)
        run = connection.execute(
            "SELECT id FROM test_runs WHERE id = %s AND project_id = %s",
            (run_id, project_id),
        ).fetchone()
        question = connection.execute(
            "SELECT id FROM questions WHERE id = %s AND project_id = %s",
            (question_id, project_id),
        ).fetchone()
        if run is None or question is None:
            abort(404)
        cited_official = any(same_site(url, project["website"]) for url in urls)
        answer = connection.execute(
            """
            INSERT INTO answers (
              test_run_id, question_id, repeat_index, body, recommendation_reason,
              cited_official, factual_error, error_note
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (test_run_id, question_id, repeat_index)
            DO UPDATE SET
              body = EXCLUDED.body,
              recommendation_reason = EXCLUDED.recommendation_reason,
              cited_official = EXCLUDED.cited_official,
              factual_error = EXCLUDED.factual_error,
              error_note = EXCLUDED.error_note
            RETURNING id
            """,
            (run_id, question_id, repeat_index, body, reason, cited_official, factual_error, error_note),
        ).fetchone()
        answer_id = answer["id"]
        connection.execute("DELETE FROM citations WHERE answer_id = %s", (answer_id,))
        connection.execute("DELETE FROM answer_brands WHERE answer_id = %s", (answer_id,))
        for url in urls:
            connection.execute(
                "INSERT INTO citations (answer_id, url, is_client_site) VALUES (%s, %s, %s)",
                (answer_id, url, same_site(url, project["website"])),
            )
        brand_rows = [("client", project["brand_name"])]
        brand_rows.extend(("competitor", item["name"]) for item in competitors)
        for role, name in brand_rows:
            key = f"{role}:{name}"
            recommended = request.form.get(f"recommended:{key}") == "yes"
            negative = request.form.get(f"negative:{key}") == "yes"
            mentioned = request.form.get(f"mentioned:{key}") == "yes" or recommended or negative
            if mentioned or recommended or negative:
                connection.execute(
                    """
                    INSERT INTO answer_brands
                      (answer_id, name, role, mentioned, recommended, negative)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (answer_id, name, role, mentioned, recommended, negative),
                )
        connection.commit()
    flash(t("flash.answer_saved"))
    if repeat_index < 3:
        return redirect(url_for(
            "tests",
            project_id=project_id,
            run=run_id,
            question=question_id,
            repeat=repeat_index + 1,
        ))
    with connect() as connection:
        progress = answer_progress(connection, run_id)
    for item in progress:
        if item["saved"] < 3:
            return redirect(url_for(
                "tests",
                project_id=project_id,
                run=run_id,
                question=item["id"],
                repeat=1,
            ))
    return redirect(url_for("tests", project_id=project_id, run=run_id))


@app.get("/projects/<int:project_id>/metrics")
def metrics(project_id):
    with connect() as connection:
        project, competitors = load_project(connection, project_id)
        answers = load_answers(connection, project_id)
    by_channel = {}
    for channel in ("api", "consumer"):
        subset = [item for item in answers if item["channel"] == channel]
        by_channel[channel] = compute_metrics(subset)
    return render_template(
        "metrics.html",
        project=project,
        competitors=competitors,
        by_channel=by_channel,
    )


@app.get("/projects/<int:project_id>/evidence")
def evidence(project_id):
    with connect() as connection:
        project, competitors = load_project(connection, project_id)
        notes = connection.execute(
            "SELECT * FROM evidence WHERE project_id = %s ORDER BY id DESC",
            (project_id,),
        ).fetchall()
    return render_template(
        "evidence.html",
        project=project,
        competitors=competitors,
        notes=notes,
    )


@app.post("/projects/<int:project_id>/evidence")
def create_evidence(project_id):
    kind = request.form.get("kind", "")
    claim_type = request.form.get("claim_type", "")
    observation = request.form.get("observation", "").strip()
    detail = request.form.get("detail", "").strip()
    if kind not in {"site", "external"} or claim_type not in {"fact", "hypothesis"} or not observation:
        flash(t("flash.evidence_required"))
        return redirect(url_for("evidence", project_id=project_id))
    with connect() as connection:
        load_project(connection, project_id)
        connection.execute(
            """
            INSERT INTO evidence (project_id, kind, claim_type, observation, detail)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (project_id, kind, claim_type, observation, detail),
        )
        connection.commit()
    return redirect(url_for("evidence", project_id=project_id))


@app.post("/projects/<int:project_id>/report")
def create_report(project_id):
    with connect() as connection:
        load_project(connection, project_id)
        answers = load_answers(connection, project_id)
        findings = build_findings(answers, current_lang())
        connection.execute("DELETE FROM findings WHERE project_id = %s", (project_id,))
        for item in findings:
            finding_id = connection.execute(
                """
                INSERT INTO findings (project_id, observation, action, basis)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (project_id, item["observation"], item["action"], item["basis"]),
            ).fetchone()["id"]
            for answer_id in item["answer_ids"]:
                connection.execute(
                    "INSERT INTO finding_answers (finding_id, answer_id) VALUES (%s, %s)",
                    (finding_id, answer_id),
                )
        connection.commit()
    flash(t("flash.report_saved"))
    return redirect(url_for("report", project_id=project_id))


@app.get("/projects/<int:project_id>/report")
def report(project_id):
    with connect() as connection:
        project, competitors = load_project(connection, project_id)
        answers = load_answers(connection, project_id)
        notes = connection.execute(
            "SELECT * FROM evidence WHERE project_id = %s ORDER BY id",
            (project_id,),
        ).fetchall()
    question_text = {item["id"]: item["question_text"] for item in answers}
    findings = build_findings(answers, current_lang())
    for item in findings:
        item["links"] = [
            {"answer_id": answer_id, "text": question_text.get(answer_id, "")}
            for answer_id in item["answer_ids"]
        ]
    by_channel = {}
    for channel in ("api", "consumer"):
        subset = [item for item in answers if item["channel"] == channel]
        by_channel[channel] = compute_metrics(subset)
    return render_template(
        "report.html",
        project=project,
        competitors=competitors,
        findings=findings,
        notes=notes,
        by_channel=by_channel,
        has_answers=bool(answers),
    )


@app.get("/health")
def health():
    with connect() as connection:
        connection.execute("SELECT 1")
    return {"ok": True}


if __name__ == "__main__":
    wait_for_database()
    apply_schema()
    app.run(host="0.0.0.0", port=8080)
