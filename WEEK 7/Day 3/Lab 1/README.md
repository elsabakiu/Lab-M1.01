# Lab Evaluation Dashboard — Elsa Bakiu

## Tool
Tableau Public

## Dashboard overview

**Title:** World Happiness & Health — Global Performance Dashboard 2024

This dashboard explores the 2024 World Happiness Report across 143 countries, enriched with WHO life expectancy data for 138 of those countries. It is designed for a non-technical stakeholder audience and answers three core questions:

- How are happiness scores distributed globally and by region?
- Which regions perform best and worst on happiness?
- Does a country's health (life expectancy) predict its happiness score?

The dashboard contains five interactive worksheets:

| Worksheet | Chart type | Data source(s) |
|---|---|---|
| World happiness score — 2024 | Choropleth map | Happiness |
| Average happiness score by region | Ranked horizontal bar | Happiness |
| How are happiness scores distributed? | Stacked histogram | Happiness |
| Score spread within each world region | Box-and-whisker plot | Happiness |
| Does life expectancy predict happiness? | Scatter plot with trend line | Happiness + WHO |

Four global filter controls sit above all charts: **Score Bucket** (High / Medium / Low), **Regional indicator** (10 world regions), **Development Status** (Developed / Developing, applied to the scatter only) and **Country** (all countries present in the dataset). Filter actions are configured so clicking any country on the map or any bar in the region comparison chart cross-filters all other worksheets.

## Data source notes

- `world-happiness-2024.csv` — WHR 2024 data with `Regional indicator` column added manually. 143 countries.
- `WHO_clean.csv` — WHO Life Expectancy dataset filtered to 2015, country names standardised to match the Happiness file. 138 countries.
- Both files are included in this submission folder.
- The dashboard was published to Tableau Public. The `.twb` file references these local CSV files — to open it locally, place both CSVs in the same directory as the `.twb` file and re-connect if prompted.

## Files in this folder

| File | Description |
|---|---|
| `evaluation_score_dashboard.twb` | Tableau workbook file |
| `dashboard_screenshot.png` | Screenshot of the final dashboard |
| `data_source.md` | Data source documentation |
| `reflection.md` | Reflection on design decisions |
| `world-happiness-2024.csv` | Cleaned happiness dataset (143 countries) |
| `WHO_clean.csv` | Cleaned WHO life expectancy dataset (138 countries) |
| `README.md` | This file |
