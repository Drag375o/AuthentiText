# What testing showed

The shipped detector is a demo with no measured accuracy. Rather than leave it at that, this file records what happened when real documents were run through it. The findings are from a handful of pairs, not a dataset, and are written down because they shaped the design.

## Method

Human documents were paired with AI versions of the same content: a personal essay and a rewrite of it, a paper's methods section and a rewrite, and separately some text generated from a prompt rather than rewritten. Each pair was matched for topic, genre and roughly for length, because unmatched pairs mostly measure genre.

## Finding 1: rewrites invert the signals

An AI asked to **rewrite** a human text scored *lower* than the human original, consistently.

| Signal | Essay pair | Paper pair |
|---|---|---|
| Repeated openings | +0.18 | **−0.56** |
| Sentence opening variety | +0.01 | **−0.12** |
| Personal voice | 0.00 | **−0.12** |
| Neighbour similarity | 0.00 | −0.05 |

(Positive means the AI version scored higher, which is the direction one would hope for.)

The reason is structural. Almost every signal measures some form of repetition or regularity. Natural writing has plenty of it: defined terms get reused, parallel content gets parallel structure ("For the **type** of hate task… For the **target** of hate task"). A rewrite is instructed to vary wording, so it repeats itself *less* than the original, and the heuristics read "less repetitive" as "more human". On one pair, vocabulary diversity (MTLD) rose from 74.6 to 156.8 in the AI version.

This matches the published finding that paraphrasing defeats detectors. It cannot be fixed by flipping a weight: doing so would rate careless, repetitive human writing as more machine-like, which is worse.

## Finding 2: generated text behaves differently from rewritten text

Text generated from a prompt, with no human original to follow, scored 66% with most sentences marked. Generated-from-nothing prose does reach for stock phrases and repeated structures; a rewrite inherits a human structure and changes only the surface. **The two cases are not the same problem**, and a tool that works on one may fail completely on the other.

## Finding 3: register dominates on academic prose

Two signals, contractions and personal voice, reach their maximum for any formal academic text, because papers do not use contractions or first-person casually. Every academic document therefore starts with an elevated score before anything about authorship is considered. The signal descriptions say this, but the number still moves.

## Finding 4: document structure can outweigh the text

Two measurement bugs were found this way, and both moved numbers more than the effect being studied:

- A heading counted as a sentence shifted burstiness by 0.16, which was larger than the difference between the two documents being compared. Headings are now detected and reported separately.
- Text pasted from a PDF arrives hard-wrapped, which split sentences at line breaks and invented one-word sentences. Wrapped text now measures identically to the same text unwrapped.

## What follows from this

- The demo detector is labelled a demo everywhere it appears, and reports confidence and uncertainty separately from its estimate.
- Texts under 150 words return "Insufficient evidence" with no number at all.
- Signals that reflect register carry low weight and say so in their caveats.
- The sentence heatmap says when a document's signal comes from patterns across the whole text rather than from any one sentence.
- `python manage.py train_detector` exists because the only real fix is a model trained on labelled pairs, including rewritten ones.

## What would make this rigorous

Fifty or more matched pairs per condition (rewritten, generated, human-only), held-out evaluation, and per-genre breakdowns. Until then, these are observations that shaped the design, not measured accuracy.
