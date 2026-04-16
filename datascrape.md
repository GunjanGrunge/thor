# Fitness & Nutrition Data Sources — Structured Overview

## Purpose

Reference document describing selected data sources, including:

* Type of data available
* Structure of content
* Key fields that can be extracted

No processing or training methodology included.

---

## 1. Examine

Source: https://examine.com/

### Content Type

* Evidence-based supplement and nutrition database

### Data Available

* Supplement name
* Benefits / effects
* Dosage recommendations
* Side effects / safety
* Mechanism of action
* Research summaries
* Study references

### Structure

* One page per supplement
* Clearly separated sections (headings-based)
* Semi-structured HTML (lists + paragraphs)

### Notes

* Public + paid content (avoid Examine+)
* JS-heavy pages (dynamic loading possible)
* Primary scrape targets:

  * `/supplements/{name}/`

---

## 2. HuggingFace Dataset — ishaverma/finetuning_dataset

Source: https://huggingface.co/datasets/ishaverma/finetuning_dataset

### Content Type

* Health and nutrition conversational dataset

### Data Available

* User queries (health/nutrition related)
* Assistant responses

### Structure

* Chat format (messages array)
* JSON-like structure

### Notes

* Already aligned with fine-tuning format
* Likely mixed quality (needs inspection)

---

## 3. HuggingFace Dataset — FineCorpus-WorkoutExercise

Source: https://huggingface.co/datasets/padilfm/FineCorpus-WorkoutExercise

### Content Type

* Workout / exercise conversational dataset

### Data Available

* Exercise-related prompts
* Generated responses (instructions, suggestions)

### Structure

* Chat-style (instruction → response)
* Small dataset size

### Notes

* Useful as template-style data
* Limited coverage

---

## 4. MuscleWiki

Source: https://musclewiki.com/

### Content Type

* Exercise database

### Data Available

* Exercise name
* Target muscle group
* Secondary muscles
* Difficulty level
* Step-by-step instructions
* Video embed links (YouTube/CDN)
* Thumbnails

### Structure

* Exercise-based pages
* Semi-structured (labels + instructions + media)

### Notes

* Videos are embedded (not hosted directly)
* Video URLs can be extracted, but storing links is preferred
* JS-based elements may require browser automation

---

## 5. ExRx

Source: https://exrx.net/

### Content Type

* Exercise science and training database

### Data Available

* Exercise descriptions
* Muscle targeting
* Biomechanics explanations
* Exercise variations
* Training concepts

### Structure

* Highly structured HTML pages
* Text-heavy
* Categorized by:

  * muscle group
  * exercise type

### Notes

* Old UI but consistent structure
* No login required
* Strong source for technical exercise data

---

## 6. MyFoodData

Source: https://myfooddata.com/

### Content Type

* Nutrition database (food-level)

### Data Available

* Food name
* Calories
* Macronutrients (protein, carbs, fat)
* Micronutrients (vitamins, minerals)

### Structure

* Structured tables per food item
* Standardized units (typically per 100g)

### Notes

* Clean and scrapeable
* Consistent schema across pages

---

## 7. Open Food Facts

Source: https://world.openfoodfacts.org/data
Dataset: https://huggingface.co/datasets/openfoodfacts/product-database

### Content Type

* Open food product database

### Data Available

* Product name
* Ingredients
* Nutrition values
* Labels (e.g., vegan, organic)
* Categories

### Structure

* Available as:

  * CSV / JSON / ODS
* Large-scale structured dataset

### Notes

* Licensed under Open Database License
* High volume, variable data quality

---

## 8. Verywell Fit

Source: https://verywellfit.com/

### Content Type

* Fitness and nutrition articles

### Data Available

* Workout guides
* Diet explanations
* Fitness concepts
* Beginner-friendly breakdowns

### Structure

* Article-based
* Sectioned with headings
* Narrative text (less structured)

### Notes

* Clean writing style
* Requires transformation to structured format

---

## 9. NIH Office of Dietary Supplements

Source: https://ods.od.nih.gov/

### Content Type

* Government-backed supplement fact sheets

### Data Available

* Supplement overview
* Recommended intake
* Health effects
* Safety and risks
* Scientific references

### Structure

* Structured fact sheets
* Section-based layout

### Notes

* Public and reliable
* Consistent formatting across supplements

---

## 10. PubMed

Source: https://pubmed.ncbi.nlm.nih.gov/

### Content Type

* Biomedical research database

### Data Available

* Study titles
* Abstracts
* Authors
* Keywords
* Study conclusions

### Structure

* Structured entries per paper
* Abstract-based summaries

### Notes

* Abstracts are free
* Full papers may be restricted
* Text is dense and technical

---

## 11. USDA FoodData Central

Source: https://fdc.nal.usda.gov/

### Content Type

* Government nutrition database

### Data Available

* Food items
* Macronutrients
* Micronutrients
* Portion sizes

### Structure

* Structured dataset (API + downloads)
* Standardized schema

### Notes

* Highly reliable
* Suitable for direct data integration

---

## Summary

| Source          | Type         | Structure Level      |
| --------------- | ------------ | -------------------- |
| Examine         | Supplements  | Semi-structured      |
| HF (ishaverma)  | Chat dataset | Structured           |
| HF (FineCorpus) | Chat dataset | Structured           |
| MuscleWiki      | Exercises    | Semi-structured      |
| ExRx            | Exercises    | Structured           |
| MyFoodData      | Nutrition    | Structured           |
| Open Food Facts | Nutrition    | Structured (dataset) |
| Verywell Fit    | Articles     | Unstructured         |
| NIH ODS         | Supplements  | Structured           |
| PubMed          | Research     | Semi-structured      |
| USDA FDC        | Nutrition    | Structured           |

---
