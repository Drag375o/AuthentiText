# Trained models

This folder holds trained detector bundles. **Model files are not committed**
(see `.gitignore`): they are build artefacts, and a model trained on data you
cannot redistribute should not be shipped.

A bundle is a joblib file containing:

| Key | What it is |
|---|---|
| `model` | the fitted scikit-learn pipeline (scaler + logistic regression) |
| `feature_names` | the exact feature order the model expects |
| `metrics` | accuracy, precision, recall, ROC AUC and cross-validated accuracy, all measured on held-out data |
| `version` | the string shown in the interface |
| `trained_on` | how many labelled documents, and the class balance |

To train one:

```bash
python manage.py train_detector data/labelled.jsonl
```

Until a bundle exists here, AuthentiText uses the demo detector and says so on
every result.
