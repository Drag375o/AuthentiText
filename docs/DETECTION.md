# Detection

AuthentiText estimates whether a text shows characteristics associated with AI-generated writing. It does not identify authorship, and it cannot.

## Three numbers, kept separate

| | Meaning |
|---|---|
| **Probability** | the estimated AI-associated signal, 0-100% |
| **Confidence** | how much the evidence supports that estimate |
| **Uncertainty** | 1 - confidence, shown alongside it |

A 60% signal with 30% confidence and a 60% signal with 90% confidence are very different results, so both are always shown. Confidence falls when the text is short, when signals could not be measured, and when signal families disagree with one another.

## Labels

`Likely human`, `Possibly AI-assisted`, `Likely AI-associated`, `Uncertain` (confidence too low to place a band), `Insufficient evidence` (under `ANALYSIS_MIN_WORDS`, 150 by default, where no probability is reported at all).

## The two detectors

**`DemoDetector`** is the default and is labelled `DEMO ANALYSIS — not a real prediction` wherever it appears. It combines ten hand-chosen signals (`analyzer/services/signals.py`), each scaling one measured feature between two documented anchors. It is deterministic: the same text always gives the same result, and no random numbers are used anywhere. **It has no measured accuracy, because it was never trained or evaluated on labelled data.** Its purpose is to exercise the full interface honestly until a trained model exists.

**`TrainedDetector`** loads a scikit-learn bundle from `ml/models/baseline.joblib`. It reports the version and the metrics measured on held-out data at training time. If no bundle exists, it is simply unavailable and the demo is used instead; nothing is faked.

`DETECTOR_BACKEND` selects: `auto` (default), `trained` (fail loudly if missing), `demo`.

## Training a real model

```bash
python manage.py train_detector data/labelled.jsonl
```

The file holds one JSON object per line: `{"text": "...", "label": "human"}` or `"ai"`. Training extracts features with the application's own pipeline, so training and inference cannot drift apart. It refuses fewer than 20 examples or badly unbalanced classes, splits off a test set, measures accuracy, precision, recall and ROC AUC, cross-validates, and saves those metrics inside the bundle.

Collecting that data honestly is the hard part, and it is the part that decides whether any of this works. Documents should be matched for topic, genre and length; otherwise the model learns to tell lab reports from diaries.

## What the signals are worth

Testing on one human/AI paraphrase pair (same section of a paper, one rewritten by a model) showed:

- **Semantic diversity and neighbour similarity separated the pair clearly**, but only with sentence-transformers embeddings; TF-IDF saw no difference.
- **Repeated three-word sequences separated the pair backwards:** the human academic text reused its defined terms ("the type of hate task"), while the paraphrase avoided repetition.
- **Sentence-length regularity, burstiness and formulaic phrases separated nothing** once headings were excluded from the rhythm measures.

One pair proves nothing, but it is enough to show why thresholds picked by hand are a poor foundation, and why the demo is labelled as a demo.

## Sentence-level scores

Each sentence is marked relative to the document's own score, so the heatmap can never contradict the headline. Its evidence is what can be seen in one sentence, or the sentence's own part in a document-wide pattern: stock phrases and discourse markers, repetition within the sentence, ordinary vocabulary, an opening shared with other sentences, resemblance to its closest neighbour, and (only when the document's lengths are unusually even) a length matching the average. A sentence carrying more of that evidence than its neighbours sits above the document score; one carrying less sits below. Every mark lists its reasons, and a sentence with none says so plainly: "Marked at the document's overall level: nothing in this sentence itself stands out."

**When the evidence is not local at all.** Several signals belong to the whole set rather than to any sentence: how evenly lengths are spread, how far meanings travel, whether contractions appear anywhere. When most of a document's score comes from those, the heatmap says so instead of spreading the blame evenly:

> Most of this document's signal comes from patterns across the whole text (vocabulary spread, contractions, sentence openings) rather than from anything inside a particular sentence.

The three bands are low (under 34%), medium (34-60%) and high (above 60%). In both exported heatmaps each band has a tint **and** a different underline, so the marks never depend on colour alone: in the PDF, high signal is a red tint with a double underline, medium a grey tint with a single underline, and low is left plain; the Word file uses highlight colours with dotted and dashed underlines.

## What a result never means

A result describes measured characteristics of the text. It does not prove authorship, AI use, plagiarism, academic misconduct or intent. Every pattern the system looks for appears in human writing as well. Use a result as a reason to read more closely, or to start a conversation, never as a verdict.
