# P99 Mob Explorer

A tool for extracting, analyzing, and exploring NPC data from the [Project 1999 Wiki](https://wiki.project1999.com/).

This project allows you to build a local SQLite dataset of NPC statistics (Level, HP, AC, etc.) and provides a Streamlit-based UI to filter and find the "squishiest" mobs for your level.

## Features

- **Wiki Ingestion**: Automatically crawls the P99 Wiki for NPC pages using the MediaWiki API.
- **Template Parsing**: Extracts structured data from wiki templates while preserving raw wikitext for future re-parsing.
- **RSI (Relative Strength Index)**: A custom metric that ranks NPCs by HP percentile within their level, helping you find low-HP targets.
- **Interactive Viewer**: A Streamlit dashboard to search, filter, and inspect NPC data.
- **Data Export**: Export the parsed NPC data to CSV for external analysis.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jasonhdavis/p99-mob-explorer.git
   cd p99-mob-explorer
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Ingest Data
Fetch NPC pages from the wiki and store them in the local database:
```bash
python cli.py ingest --max-pages 100  # Remove --max-pages to fetch all
```

### 2. Parse Data
Extract structured NPC stats from the raw wikitext:
```bash
python cli.py parse
```

### 3. Launch the Viewer
Start the interactive Streamlit dashboard:
```bash
streamlit run viewer.py
```

### 4. Export Data
Export the core NPC table to CSV:
```bash
python cli.py export --out exports/npc_core.csv
```

## Project Structure

- `cli.py`: Command-line interface for ingestion, parsing, and exporting.
- `viewer.py`: Streamlit dashboard for data exploration.
- `ingest.py`: Logic for fetching pages from the MediaWiki API.
- `parse.py`: Logic for extracting template parameters from wikitext.
- `db.py`: SQLite database schema and connection management.
- `normalize.py`: Utilities for cleaning up numeric and text data.

## License

MIT
