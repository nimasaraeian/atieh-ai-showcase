# Atieh Scheduling Engine - Data Loader

Core data loader layer for the Atieh scheduling engine. Processes 4 Excel files containing doctor shifts, services, unfinished treatments, and insurance priority data.

## Project Structure

```
atieh/
├── app/
│   ├── loaders/
│   │   ├── excel_io.py          # Robust Excel I/O with merged cell handling
│   │   └── atieh_loader.py      # Main parsers and CLI entry point
│   └── utils/
│       └── fa_normalize.py      # Persian text normalization
├── data/
│   ├── inputs/                  # Place Excel files here
│   │   ├── __نوبت دهی 17 دی_.xlsx
│   │   ├── درمانهای نا تمام.xlsx
│   │   ├── خدمات اقای سرایی.xlsx
│   │   └── تاریخ پرداختی بیمه ها.xlsx
│   └── outputs/                 # Generated CSV files
│       ├── doctor_shifts.csv
│       ├── services_catalog.csv
│       ├── unfinished_treatments.csv
│       └── insurance_priority.csv
├── tests/
│   └── test_loaders.py
├── requirements.txt
└── README.md
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Place input Excel files in `data/inputs/` directory.

## Usage

### Generate all CSV outputs

```bash
python -m app.loaders.atieh_loader
```

This will:
- Parse all 4 Excel files
- Apply Persian text normalization
- Generate 4 CSV files in `data/outputs/`

### Run tests

```bash
pytest tests/test_loaders.py -v
```

Or run tests directly:
```bash
python tests/test_loaders.py
```

## Output Files

### 1. doctor_shifts.csv
Doctor shift schedule by weekday.

**Columns:**
- `weekday_fa`: Persian weekday (شنبه...جمعه)
- `shift_code`: D (day/morning), E (evening), N (night)
- `doctor_name_raw`: Original doctor name from Excel
- `doctor_name_norm`: Normalized doctor name
- `tags`: Extracted tags (e.g., اطفال)

### 2. services_catalog.csv
Available dental services with duration and complexity estimates.

**Columns:**
- `category`: Service category
- `service_name`: Original service name
- `service_name_norm`: Normalized service name
- `default_duration_min`: Estimated duration in minutes
- `complexity_weight`: Complexity score (0.0-1.0)

### 3. unfinished_treatments.csv
Backlog of unfinished treatments with urgency weights.

**Columns:**
- `backlog_title`: Treatment title
- `urgency_weight`: Urgency score (0.0-1.0)

### 4. insurance_priority.csv
Insurance payment priority mapping.

**Columns:**
- `insurance_name`: Insurance company name
- `priority_score`: Priority score (1.0=highest, 0.2=lowest)

## Features

### Persian Text Normalization
- Converts Arabic characters (ي, ك) to Persian (ی, ک)
- Converts Persian/Arabic digits to ASCII
- Removes zero-width characters
- Trims and collapses whitespace

### Robust Excel Reading
- Handles merged cells (forward-fills values)
- Tolerant to messy formatting
- Normalizes text automatically
- Finds header rows intelligently

### Heuristic Estimation
- **Service duration/complexity**: Based on keywords (surgery, implant, filling, etc.)
- **Treatment urgency**: Based on treatment type
- **Insurance priority**: Based on payment timing buckets

## Development

### Adding new parsers

1. Add parsing function in `app/loaders/atieh_loader.py`
2. Add test in `tests/test_loaders.py`
3. Call from `main()` function
4. Update this README

### Modifying normalization rules

Edit `app/utils/fa_normalize.py` to adjust Persian text processing.

## License

Internal use only.
