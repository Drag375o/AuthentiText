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

## What a result never means

A result describes measured characteristics of the text. It does not prove authorship, AI use, plagiarism, academic misconduct or intent. Every pattern the system looks for appears in human writing as well. Use a result as a reason to read more closely, or to start a conversation, never as a verdict.
