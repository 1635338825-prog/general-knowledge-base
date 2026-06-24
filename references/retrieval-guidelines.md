# Retrieval Guidelines

Retrieval quality now depends on `digest.json` and the rendered minimal pages, not on heuristic keyword scaffolding.

## Source Pages

Source pages should be written for four distinct retrieval intents:

- `背景`: why the material matters
- `方法`: how the work is done
- `结果`: what it finds
- `细节`: what is worth citing, reusing, or checking later

Rules:

- one bullet or sentence cluster should serve one intent
- do not repeat the same abstract sentence across sections
- write in a way that is directly useful for later paper writing
- keep form notices, table-of-contents fragments, citation strings, and OCR debris out of the page

## Topic Pages

Topic pages are mini reviews, not index dumps.

They should answer:

- what this topic is about
- what methods the literature uses
- what result patterns the literature reports

Do not turn topic pages into keyword lists or source-link piles.

## Entity Pages

Entity pages are short practical concept cards.

They should answer:

- what the concept is
- how it is measured, estimated, or appears in a model
- why it matters for interpretation or identification

## Term Selection

Keep:

- `ATT(g,t)`
- `TWFE bias`
- `conditional parallel trends`
- `not-yet-treated`
- `融资约束`
- `数字化转型`
- `资源错配`

Remove:

- author names
- months
- `and`
- `big`
- `china`
- `aggregate`
- DOI and journal issue strings
- section-title pseudo-entities
- OCR fragments

## Query Output

When wrapping qmd hits, annotate them with the closest rendered section where possible:

- `source:背景`
- `source:方法`
- `source:结果`
- `source:细节`
- `topic:背景`
- `topic:方法脉络`
- `topic:结果脉络`
- `entity:定义`
- `entity:方法/测度`
- `entity:结果意义`

This is for later agents and report consumers. It does not mean those labels need extra prose in the page body.
