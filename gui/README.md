# accessipdf Streamlit GUI

A beautiful web interface for the accessipdf PDF accessibility conversion tool.

## Features

- **Convert PDF**: Upload a PDF and convert it to PDF/UA-1 compliant accessible format
- **Identify Layout**: Determine which template a PDF matches
- **Check PDF/UA-1**: Validate a PDF against the accessibility standard
- **Batch Convert**: Process multiple PDFs at once and download as ZIP

## Running the GUI

### Locally

```bash
# Install dependencies
pip install -e '.[dev]'

# Run Streamlit
streamlit run gui/app.py
```

The app will be available at `http://localhost:8501`

### With Docker

```bash
# Build the image
docker-compose build

# Run the GUI
docker-compose up accessipdf-gui
```

The app will be available at `http://localhost:8501`

## Screenshots

### Main Interface
The GUI provides a clean, intuitive interface for all accessipdf functions.

### Convert PDF
- Upload any PDF file
- Automatically identifies the layout template
- Shows conversion progress
- Validates with veraPDF
- Download the accessible PDF

### Batch Processing
- Upload multiple PDFs
- Process all at once
- Download all results as a ZIP archive
- See success/error counts

## Requirements

- Python 3.12+
- Streamlit 1.30+
- All accessipdf dependencies (pikepdf, pypdfium2, PyYAML, Pillow)
- veraPDF CLI (for validation)

## Customization

The GUI can be extended by modifying `gui/app.py`:

- Add new pages for additional functionality
- Customize the styling in the CSS section
- Add more PDF processing options
- Integrate with external storage (S3, database, etc.)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAMLIT_SERVER_PORT` | 8501 | Port to run the server on |
| `STREAMLIT_SERVER_ADDRESS` | 0.0.0.0 | Address to bind to |
| `PYTHONUNBUFFERED` | 1 | Ensure Python output is not buffered |

## Architecture

```
gui/
├── __init__.py      # Package init
├── app.py           # Main Streamlit application
└── README.md        # This file
```

The GUI imports directly from the `accessipdf` package, so all core functionality is shared between CLI and web interface.
