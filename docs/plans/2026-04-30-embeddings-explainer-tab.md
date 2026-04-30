# About Embeddings tab — explainer/manual

Context: the Similar Games page has an **Explore Embeddings** tab that
renders a PCA scatter of the game-embedding space (currently colored by
geek rating, complexity, etc., with a handful of recognizable games
pinned as default highlights). Users see a dot blob and have to infer
what they're looking at. This plan covers adding a sibling **About**
tab whose job is to explain the embeddings to a layperson.

## Goal

A static, scrollable explainer that turns "what am I looking at?" into
"oh, I get it." Audience: someone who's never heard of an embedding,
PCA, or a feature vector. Plain language, concrete examples, a few
supporting visuals. Not a research paper.

## Approach

Add a 5th tab to `src/layouts/game_similarity.py` next to Explore
Embeddings. Render the prose with `dcc.Markdown`. Embed a couple of
supporting visuals via Dash components alongside the markdown.

Deliberately **not** Quarto for v1: in-app Markdown keeps everything in
one repo with one deploy story, the dark theme stays consistent, and
visuals can pull from the same data layer the rest of the app uses
(`get_game_coordinates`, etc.). If the document grows past ~2 pages of
prose or someone wants to embed code blocks / footnotes / TOC, revisit
Quarto + iframe at that point.

## Suggested structure

Each section is one prose chunk + (optionally) one small supporting
visual. Keep the writing tight — no headings deeper than h3, no
multi-paragraph rambles.

### 1. What's an embedding? (intro)

One paragraph. "Every game on BGG has features — complexity, mechanics,
categories, descriptions. We turn these into a list of numbers — an
*embedding* — that captures what kind of game it is. Games with similar
embeddings are similar games."

No visual. Lead with the punchline.

### 2. Why does this matter? (the scatter)

The same PCA scatter from the Explore tab, smaller, read-only, with the
default landmarks (Ticket to Ride, Azul, Codenames, Chess, Twilight
Struggle, Brass: Birmingham, Blood on the Clocktower, Crokinole,
Gloomhaven). Caption: "Games near each other in this space play
similarly."

Reuse `EXPLORE_DEFAULT_HIGHLIGHTS` from `similarity_callbacks.py`.

### 3. How is this used? (worked example)

"Pick Catan. Here are its 5 closest neighbors — these are what we'd
recommend." A simple table of names + similarity scores. Link to the
Game Neighbors tab as the "try it yourself" entry point.

Pulls from the same similarity client used elsewhere; pre-computed for
one specific game so it loads instantly.

### 4. What's actually in the embedding? (optional)

For one specific game (probably Gloomhaven, since it's at an axis
extreme), a horizontal bar chart of its top contributing features. This
is the "open the hood" section — it grounds the abstraction in concrete
features (categories, mechanics, complexity) rather than leaving it as
a black box.

Skip if it's hard to compute cleanly. The other sections stand on their
own without it.

### 5. Limitations

One paragraph. "It's only as good as the features. It doesn't know
about play feel, artwork, humor, the way your group plays. It's a
starting point, not a final answer."

This matters — sets expectations and prevents the embedding from being
treated as authoritative.

## Audience constraints

- No "PCA," "SVD," "dimensionality reduction." Use *coordinates* and
  *similar*.
- No "vector," no "64-dimensional." Use *list of numbers* if you have
  to and skip it otherwise.
- Concrete examples over abstractions. "Catan and Carcassonne are
  close together because both reward steady building over many turns,"
  not "their cosine distance is small."
- One technical word per section, max.

## Implementation notes

- Add the tab to `src/layouts/game_similarity.py` after
  `tab-explore`. Use `tab_id="tab-about"`.
- Wire `tab-about-content` into the existing `switch_tab_content`
  callback (`src/callbacks/similarity_callbacks.py`) so it
  show/hides like the other tabs.
- Hide the shared "Select a Game" search card on the About tab (same
  pattern as Explore — already wired via the callback's
  `selector_style` output).
- Prose lives in a Python string passed to `dcc.Markdown`. If it grows
  past a screen of code, lift it to a separate `.md` file under
  `src/content/` (new dir) and read it at startup. Don't templatize.
- Visuals: prefer reusing existing functions over duplicating
  rendering logic. The mini scatter in section 2 should call the same
  figure-building code as the Explore tab, just with controls fixed
  and `dcc.Graph` config set to non-interactive.

## Out of scope (for v1)

- Predictive-model explainer. Keep this scoped to embeddings only —
  the predictive models are a different conversation.
- Scrollytelling / sticky-plot interactions. Plain prose with embedded
  visuals between paragraphs is enough.
- Localization, multiple language versions.
- Embedding the rendered Quarto report — revisit if the explainer
  grows past two screens of content.

## Open questions when picking this up

- Is this still the right scope, or has the Explore tab itself evolved
  enough that the explainer should change shape?
- Do landmark games still look right, or have model retrains changed
  what the axis extremes mean? (Re-eyeball before writing prose about
  "Gloomhaven sits at the heavy end.")
- Should the limitations section flag the recent embedding-model fix
  (real 64-d SVD output now, not the 493-d preprocessed feature row
  the dashboard used to show), or is that internal trivia? Probably
  the latter.

## Related context

- `src/callbacks/similarity_callbacks.py` — `EXPLORE_DEFAULT_HIGHLIGHTS`
  list and the explorer's plot-building code, which the About tab's
  mini-scatter should reuse.
- `src/data/bigquery_client.py:get_game_coordinates` — pulls
  `pca_1`/`pca_2` from `bgg_game_coordinates`. Source-of-truth for the
  scatter.
- `bgg-data-warehouse.predictions.bgg_game_coordinates` — the warehouse
  view backing all of this. PCA was broken until 2026-04-30; explainer
  prose should not assume any particular axis interpretation without
  re-checking.
