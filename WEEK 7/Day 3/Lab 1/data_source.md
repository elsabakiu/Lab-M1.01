# Data Source Documentation

This dashboard uses two datasets joined on `Country name`:

1. **World Happiness Report 2024** — sourced from Kaggle ([jainaru/world-happiness-report-2024-yearly-updated](https://www.kaggle.com/datasets/jainaru/world-happiness-report-2024-yearly-updated)). Contains 143 countries with Ladder score (0–10 happiness scale), sub-factor scores (GDP, social support, freedom, generosity, corruption), and a manually added `Regional indicator` column mapping each country to one of 10 world regions as defined by the WHR methodology.

2. **WHO Life Expectancy (updated)** — sourced from Kaggle ([lashagoch/life-expectancy-who-updated](https://www.kaggle.com/datasets/lashagoch/life-expectancy-who-updated)). Filtered to year 2015 (most recent complete year in the dataset), yielding 138 countries. Pre-processing applied: renamed `Country` column to `Country name` for join compatibility, standardised 12 country names to match the Happiness file (e.g. `Russian Federation` → `Russia`, `Cote d'Ivoire` → `Ivory Coast`), and created a calculated field `Development Status` converting the binary `Developed` column (0/1) to readable labels. Five countries in the Happiness file have no WHO equivalent (Hong Kong, Kosovo, South Korea, State of Palestine, Taiwan) and return null on WHO-joined charts.
