const state = {
  currentDeckId: null,
  dueCards: [],
  currentCard: null,
};

const deckSelect = document.getElementById("deck-select");
const deckMeta = document.getElementById("deck-meta");
const statusEl = document.getElementById("status");
const statsEl = document.getElementById("stats");
const reviewEmptyEl = document.getElementById("review-empty");
const reviewPanelEl = document.getElementById("review-panel");
const questionEl = document.getElementById("card-question");
const answerEl = document.getElementById("card-answer");
const answerBlockEl = document.getElementById("answer-block");
const searchResultsEl = document.getElementById("search-results");

function setStatus(message, type = "muted") {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    const errorMessage = data.error || "Request failed.";
    throw new Error(errorMessage);
  }
  return data;
}

function formatDate(iso) {
  if (!iso) return "-";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

function renderReviewCard() {
  if (!state.currentCard) {
    reviewPanelEl.classList.add("hidden");
    reviewEmptyEl.classList.remove("hidden");
    reviewEmptyEl.textContent = state.currentDeckId
      ? "No cards due right now. Great progress."
      : "Pick a deck to start reviewing.";
    return;
  }

  reviewEmptyEl.classList.add("hidden");
  reviewPanelEl.classList.remove("hidden");
  answerBlockEl.classList.add("hidden");
  questionEl.textContent = state.currentCard.question;
  answerEl.textContent = state.currentCard.answer;
}

async function refreshStats() {
  if (!state.currentDeckId) {
    statsEl.textContent = "Pick a deck to see progress.";
    statsEl.className = "stats muted";
    return;
  }

  const data = await api(`/api/decks/${state.currentDeckId}/stats`);
  const s = data.stats;
  statsEl.className = "stats";
  statsEl.innerHTML = `
    <div>Total cards: <strong>${s.total_cards}</strong></div>
    <div>Due now: <strong>${s.due_cards}</strong></div>
    <div>Mastered: <strong>${s.mastered_cards}</strong></div>
    <div>Total reviews: <strong>${s.total_reviews}</strong></div>
    <div>Accuracy: <strong>${s.accuracy_percent}%</strong></div>
    <div>Average score: <strong>${s.average_score}</strong></div>
  `;
}

async function loadDueCards() {
  if (!state.currentDeckId) return;
  const data = await api(`/api/decks/${state.currentDeckId}/due?limit=30`);
  state.dueCards = data.cards || [];
  state.currentCard = state.dueCards.shift() || null;
  renderReviewCard();
}

async function loadDecks(selectDeckId = null) {
  const data = await api("/api/decks");
  const decks = data.decks || [];
  const prev = selectDeckId || state.currentDeckId;

  deckSelect.innerHTML = `<option value="">Select a deck...</option>`;
  for (const deck of decks) {
    const option = document.createElement("option");
    option.value = String(deck.id);
    option.textContent = `${deck.title} (${deck.due_cards} due / ${deck.card_count} total)`;
    if (prev && Number(prev) === deck.id) option.selected = true;
    deckSelect.appendChild(option);
  }

  if (prev) {
    state.currentDeckId = Number(prev);
    const selected = decks.find((d) => d.id === Number(prev));
    if (selected) {
      deckMeta.textContent = `Source: ${selected.source_filename} • Created: ${formatDate(selected.created_at)}`;
      await Promise.all([refreshStats(), loadDueCards(), runSearch()]);
    } else {
      state.currentDeckId = null;
      deckMeta.textContent = "";
      renderReviewCard();
      await refreshStats();
    }
  } else {
    deckMeta.textContent = "";
    renderReviewCard();
    await refreshStats();
  }
}

async function handleUpload(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);

  setStatus("Generating flashcards from PDF...", "muted");
  try {
    const result = await api("/api/decks/upload", {
      method: "POST",
      body: formData,
    });
    setStatus(`Deck "${result.title}" created with ${result.cards_created} cards.`, "success");
    form.reset();
    await loadDecks(result.deck_id);
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function handleDeckChange(event) {
  const deckId = Number(event.target.value);
  if (!deckId) {
    state.currentDeckId = null;
    deckMeta.textContent = "";
    searchResultsEl.innerHTML = "";
    renderReviewCard();
    await refreshStats();
    return;
  }

  state.currentDeckId = deckId;
  const selectedText = deckSelect.options[deckSelect.selectedIndex]?.textContent || "";
  deckMeta.textContent = selectedText;

  try {
    await Promise.all([refreshStats(), loadDueCards(), runSearch()]);
    setStatus("Deck loaded.", "success");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

function revealAnswer() {
  if (!state.currentCard) return;
  answerBlockEl.classList.remove("hidden");
}

async function submitScore(score) {
  if (!state.currentCard) return;
  try {
    await api(`/api/cards/${state.currentCard.id}/grade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ score }),
    });
    setStatus(`Saved score ${score}.`, "success");
    state.currentCard = state.dueCards.shift() || null;
    if (!state.currentCard) {
      await loadDueCards();
    } else {
      renderReviewCard();
    }
    await refreshStats();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function runSearch(event = null) {
  if (event) event.preventDefault();
  searchResultsEl.innerHTML = "";

  if (!state.currentDeckId) {
    searchResultsEl.innerHTML = "<li class='muted'>Select a deck to search cards.</li>";
    return;
  }

  const query = document.getElementById("search-query").value.trim();
  const endpoint = query
    ? `/api/decks/${state.currentDeckId}/cards?q=${encodeURIComponent(query)}&limit=50`
    : `/api/decks/${state.currentDeckId}/cards?limit=20`;

  try {
    const result = await api(endpoint);
    const cards = result.cards || [];
    if (!cards.length) {
      searchResultsEl.innerHTML = "<li class='muted'>No cards found.</li>";
      return;
    }

    for (const card of cards) {
      const li = document.createElement("li");
      const q = document.createElement("div");
      q.className = "q";
      q.textContent = card.question;

      const a = document.createElement("div");
      a.className = "a";
      a.textContent = card.answer;

      const meta = document.createElement("div");
      meta.className = "muted";
      meta.textContent = `Repetitions: ${card.repetitions} • Next review: ${card.next_review_at}`;

      li.appendChild(q);
      li.appendChild(a);
      li.appendChild(meta);
      searchResultsEl.appendChild(li);
    }
  } catch (err) {
    setStatus(err.message, "error");
  }
}

document.getElementById("upload-form").addEventListener("submit", handleUpload);
document.getElementById("search-form").addEventListener("submit", runSearch);
deckSelect.addEventListener("change", handleDeckChange);
document.getElementById("reveal-answer").addEventListener("click", revealAnswer);
document.querySelectorAll(".score-btn").forEach((button) => {
  button.addEventListener("click", () => submitScore(Number(button.dataset.score)));
});

loadDecks().catch((err) => setStatus(err.message, "error"));
