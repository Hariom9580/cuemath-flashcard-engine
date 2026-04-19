import re
from collections import Counter


STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "have",
    "they",
    "your",
    "will",
    "their",
    "about",
    "into",
    "when",
    "what",
    "where",
    "which",
    "while",
    "been",
    "being",
    "also",
    "than",
    "then",
    "them",
    "were",
    "such",
    "could",
    "should",
    "would",
    "there",
    "these",
    "those",
    "through",
    "because",
    "using",
    "used",
}


def split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+", text)
    return [c.strip() for c in chunks if len(c.strip()) > 25]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def infer_keyword(sentence: str) -> str | None:
    words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", sentence)
    filtered = [
        w
        for w in words
        if w.lower() not in STOPWORDS and not w[0].islower() and len(w) > 4
    ]
    if filtered:
        return max(filtered, key=len)

    fallback = [w for w in words if w.lower() not in STOPWORDS]
    if not fallback:
        return None
    return max(fallback, key=len)


def top_terms(text: str, limit: int = 40) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-]{4,}", text.lower())
    counts = Counter(w for w in words if w not in STOPWORDS)
    return [word for word, _ in counts.most_common(limit)]


def generate_flashcards(text: str, max_cards: int = 30) -> list[dict[str, str]]:
    text = normalize_text(text)
    if len(text) < 120:
        return []

    cards: list[dict[str, str]] = []
    seen_questions: set[str] = set()
    sentences = split_sentences(text)

    definition_patterns = [
        re.compile(
            r"^(?P<term>[A-Z][A-Za-z0-9\-\s]{2,70})\s+is\s+(?P<definition>[^.]{20,260})[.]?$"
        ),
        re.compile(
            r"^(?P<term>[A-Z][A-Za-z0-9\-\s]{2,70})\s+are\s+(?P<definition>[^.]{20,260})[.]?$"
        ),
        re.compile(
            r"^(?P<term>[A-Z][A-Za-z0-9\-\s]{2,70}):\s*(?P<definition>[^.]{20,260})[.]?$"
        ),
    ]

    for sentence in sentences:
        compact = sentence.strip()
        for pattern in definition_patterns:
            match = pattern.match(compact)
            if not match:
                continue

            term = match.group("term").strip()
            definition = match.group("definition").strip()
            question = f"What is {term}?"
            if question in seen_questions:
                continue

            cards.append(
                {
                    "question": question,
                    "answer": definition,
                    "source_excerpt": compact[:280],
                }
            )
            seen_questions.add(question)
            break

        if len(cards) >= max_cards:
            return cards[:max_cards]

    ranked_terms = top_terms(text)
    if ranked_terms:
        term_index = {term: idx for idx, term in enumerate(ranked_terms)}
        scored_sentences = []
        for sentence in sentences:
            score = 0
            sentence_words = set(re.findall(r"[A-Za-z][A-Za-z\-]{4,}", sentence.lower()))
            for word in sentence_words:
                if word in term_index:
                    score += max(0, 40 - term_index[word])
            if score > 0:
                scored_sentences.append((score, sentence))

        scored_sentences.sort(key=lambda t: t[0], reverse=True)
        sentence_candidates = [s for _, s in scored_sentences]
    else:
        sentence_candidates = sentences

    for sentence in sentence_candidates:
        if len(cards) >= max_cards:
            break
        if len(sentence) < 35 or len(sentence) > 240:
            continue

        keyword = infer_keyword(sentence)
        if not keyword:
            continue

        masked_sentence = re.sub(
            rf"\b{re.escape(keyword)}\b",
            "______",
            sentence,
            count=1,
        )
        if masked_sentence == sentence:
            continue

        question = f"Fill in the blank: {masked_sentence}"
        if question in seen_questions:
            continue

        cards.append(
            {
                "question": question,
                "answer": keyword,
                "source_excerpt": sentence[:280],
            }
        )
        seen_questions.add(question)

    return cards[:max_cards]
