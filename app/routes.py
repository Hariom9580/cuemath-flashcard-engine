from datetime import datetime
from typing import Any

from flask import Flask, jsonify, render_template, request

from .db import get_connection
from .flashcard_engine import generate_flashcards
from .pdf_ingestion import extract_text_from_pdf
from .srs import calculate_sm2_update


def error(message: str, code: int = 400):
    return jsonify({"ok": False, "error": message}), code


def fetch_due_cards(db_path: str, deck_id: int, limit: int = 20) -> list[dict[str, Any]]:
    query = """
        SELECT id, question, answer, source_excerpt, next_review_at, repetitions, interval_days, ease_factor
        FROM cards
        WHERE deck_id = ? AND DATE(next_review_at) <= DATE('now')
        ORDER BY DATE(next_review_at) ASC, id ASC
        LIMIT ?
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(query, (deck_id, limit)).fetchall()
    return [dict(row) for row in rows]


def register_routes(app: Flask) -> None:
    @app.get("/")
    def home():
        return render_template("index.html", default_max_cards=app.config["DEFAULT_MAX_CARDS"])

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.post("/api/decks/upload")
    def upload_deck():
        if "pdf" not in request.files:
            return error("Please upload a PDF file.")

        pdf_file = request.files["pdf"]
        if not pdf_file.filename:
            return error("Missing filename for uploaded PDF.")
        if not pdf_file.filename.lower().endswith(".pdf"):
            return error("Only .pdf files are supported.")

        max_cards_raw = request.form.get("max_cards", str(app.config["DEFAULT_MAX_CARDS"]))
        try:
            max_cards = max(5, min(80, int(max_cards_raw)))
        except ValueError:
            return error("max_cards must be a number.")

        file_bytes = pdf_file.read()
        if len(file_bytes) > app.config["MAX_UPLOAD_MB"] * 1024 * 1024:
            return error(f"PDF is too large. Limit is {app.config['MAX_UPLOAD_MB']}MB.")

        if not file_bytes:
            return error("Uploaded file is empty.")

        try:
            text = extract_text_from_pdf(file_bytes)
        except Exception:
            return error("Could not parse this PDF. Please try a standard text-based PDF file.")

        cards = generate_flashcards(text, max_cards=max_cards)

        if not cards:
            return error(
                "Could not generate enough study cards from this PDF. Try a content-rich chapter or notes PDF."
            )

        title = request.form.get("title", "").strip()
        if not title:
            title = pdf_file.filename.rsplit(".", 1)[0]

        now_iso = datetime.utcnow().isoformat(timespec="seconds")
        next_review_at = datetime.utcnow().date().isoformat()
        db_path = app.config["DATABASE_PATH"]

        with get_connection(db_path) as conn:
            cur = conn.execute(
                "INSERT INTO decks(title, source_filename, created_at, card_count) VALUES (?, ?, ?, ?)",
                (title, pdf_file.filename, now_iso, len(cards)),
            )
            deck_id = cur.lastrowid

            conn.executemany(
                """
                INSERT INTO cards(
                    deck_id,
                    question,
                    answer,
                    source_excerpt,
                    created_at,
                    repetitions,
                    interval_days,
                    ease_factor,
                    next_review_at
                ) VALUES (?, ?, ?, ?, ?, 0, 0, 2.5, ?)
                """,
                [
                    (
                        deck_id,
                        card["question"],
                        card["answer"],
                        card.get("source_excerpt", ""),
                        now_iso,
                        next_review_at,
                    )
                    for card in cards
                ],
            )

        return jsonify(
            {
                "ok": True,
                "deck_id": deck_id,
                "title": title,
                "cards_created": len(cards),
            }
        )

    @app.get("/api/decks")
    def list_decks():
        db_path = app.config["DATABASE_PATH"]
        query = """
            SELECT
                d.id,
                d.title,
                d.source_filename,
                d.created_at,
                d.card_count,
                COALESCE(SUM(CASE WHEN DATE(c.next_review_at) <= DATE('now') THEN 1 ELSE 0 END), 0) AS due_cards
            FROM decks d
            LEFT JOIN cards c ON c.deck_id = d.id
            GROUP BY d.id
            ORDER BY d.created_at DESC
        """
        with get_connection(db_path) as conn:
            rows = conn.execute(query).fetchall()
        return jsonify({"ok": True, "decks": [dict(row) for row in rows]})

    @app.get("/api/decks/<int:deck_id>/due")
    def get_due_cards(deck_id: int):
        limit_raw = request.args.get("limit", "20")
        try:
            limit = max(1, min(100, int(limit_raw)))
        except ValueError:
            return error("Invalid limit parameter.")

        cards = fetch_due_cards(app.config["DATABASE_PATH"], deck_id=deck_id, limit=limit)
        return jsonify({"ok": True, "cards": cards, "count": len(cards)})

    @app.get("/api/decks/<int:deck_id>/stats")
    def get_stats(deck_id: int):
        db_path = app.config["DATABASE_PATH"]
        with get_connection(db_path) as conn:
            total = conn.execute("SELECT COUNT(*) AS n FROM cards WHERE deck_id = ?", (deck_id,)).fetchone()["n"]
            due = conn.execute(
                "SELECT COUNT(*) AS n FROM cards WHERE deck_id = ? AND DATE(next_review_at) <= DATE('now')",
                (deck_id,),
            ).fetchone()["n"]
            mastered = conn.execute(
                """
                SELECT COUNT(*) AS n
                FROM cards
                WHERE deck_id = ? AND repetitions >= 3 AND ease_factor >= 2.3
                """,
                (deck_id,),
            ).fetchone()["n"]
            review_rows = conn.execute(
                "SELECT review_count, correct_count, last_score FROM cards WHERE deck_id = ?",
                (deck_id,),
            ).fetchall()

        total_reviews = sum(r["review_count"] for r in review_rows)
        total_correct = sum(r["correct_count"] for r in review_rows)
        last_scores = [r["last_score"] for r in review_rows if r["last_score"] is not None]
        average_score = round(sum(last_scores) / len(last_scores), 2) if last_scores else 0.0
        accuracy = round((total_correct / total_reviews) * 100, 1) if total_reviews else 0.0

        return jsonify(
            {
                "ok": True,
                "stats": {
                    "total_cards": total,
                    "due_cards": due,
                    "mastered_cards": mastered,
                    "total_reviews": total_reviews,
                    "accuracy_percent": accuracy,
                    "average_score": average_score,
                },
            }
        )

    @app.post("/api/cards/<int:card_id>/grade")
    def grade_card(card_id: int):
        payload = request.get_json(silent=True) or {}
        if "score" not in payload:
            return error("Missing score.")
        try:
            score = int(payload["score"])
        except (TypeError, ValueError):
            return error("score must be an integer from 0 to 5.")
        if score < 0 or score > 5:
            return error("score must be between 0 and 5.")

        db_path = app.config["DATABASE_PATH"]
        with get_connection(db_path) as conn:
            card = conn.execute(
                """
                SELECT id, deck_id, repetitions, interval_days, ease_factor, review_count, correct_count
                FROM cards
                WHERE id = ?
                """,
                (card_id,),
            ).fetchone()
            if not card:
                return error("Card not found.", 404)

            update = calculate_sm2_update(
                repetitions=card["repetitions"],
                interval_days=card["interval_days"],
                ease_factor=card["ease_factor"],
                score=score,
            )
            now_iso = datetime.utcnow().isoformat(timespec="seconds")
            review_count = card["review_count"] + 1
            correct_count = card["correct_count"] + (1 if score >= 3 else 0)

            conn.execute(
                """
                UPDATE cards
                SET repetitions = ?,
                    interval_days = ?,
                    ease_factor = ?,
                    next_review_at = ?,
                    review_count = ?,
                    correct_count = ?,
                    last_score = ?,
                    last_reviewed_at = ?
                WHERE id = ?
                """,
                (
                    update["repetitions"],
                    update["interval_days"],
                    update["ease_factor"],
                    update["next_review_at"],
                    review_count,
                    correct_count,
                    score,
                    now_iso,
                    card_id,
                ),
            )

        return jsonify({"ok": True, "card_id": card_id, "update": update})

    @app.get("/api/decks/<int:deck_id>/cards")
    def list_cards(deck_id: int):
        query_text = request.args.get("q", "").strip()
        limit_raw = request.args.get("limit", "50")
        try:
            limit = max(1, min(100, int(limit_raw)))
        except ValueError:
            return error("Invalid limit parameter.")

        db_path = app.config["DATABASE_PATH"]
        if query_text:
            sql = """
                SELECT id, question, answer, source_excerpt, repetitions, next_review_at
                FROM cards
                WHERE deck_id = ?
                    AND (question LIKE ? OR answer LIKE ? OR source_excerpt LIKE ?)
                ORDER BY id DESC
                LIMIT ?
            """
            like_q = f"%{query_text}%"
            params = (deck_id, like_q, like_q, like_q, limit)
        else:
            sql = """
                SELECT id, question, answer, source_excerpt, repetitions, next_review_at
                FROM cards
                WHERE deck_id = ?
                ORDER BY id DESC
                LIMIT ?
            """
            params = (deck_id, limit)

        with get_connection(db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return jsonify({"ok": True, "cards": [dict(row) for row in rows]})
