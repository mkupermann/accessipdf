"""Streamlit GUI for accessipdf - PDF Accessibility Conversion."""

import os
import tempfile
from pathlib import Path

import streamlit as st

from accessipdf import __version__
from accessipdf.pipeline import convert
from accessipdf.templates.loader import identify as identify_template, load_templates
from accessipdf.tagging.walker import walk_page
from accessipdf.validate.verapdf import validate_ua1

import pikepdf


# Page configuration
st.set_page_config(
    page_title="accessipdf",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional CSS
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');
    
    * { font-family: 'IBM Plex Sans', sans-serif; }
    
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 1rem;
    }
    
    .sub-header {
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .stCard {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
    }
    
    .stButton > button {
        background: #1967d2;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1.5rem;
        font-size: 0.875rem;
        font-weight: 500;
        letter-spacing: 0.02857em;
        text-transform: uppercase;
    }
    
    .stButton > button:hover {
        background: #1557b0;
    }
    
    .stFileUploader > div > div > div {
        background: #f5f5f5;
        border: 2px dashed #cccccc;
        border-radius: 4px;
        padding: 2rem;
    }
    
    section[data-testid="stSidebar"] {
        background: #f8f9fa;
        border-right: 1px solid #e0e0e0;
    }
    
    .success-box {
        background: #e8f5e9;
        padding: 1rem;
        border-radius: 4px;
        border-left: 4px solid #2e7d32;
        color: #1b5e20;
        margin: 1rem 0;
    }
    
    .error-box {
        background: #ffebee;
        padding: 1rem;
        border-radius: 4px;
        border-left: 4px solid #c62828;
        color: #b71c1c;
        margin: 1rem 0;
    }
    
    .info-box {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 4px;
        border-left: 4px solid #1565c0;
        color: #0d47a1;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: #fff3e0;
        padding: 1rem;
        border-radius: 4px;
        border-left: 4px solid #e65100;
        color: #bf360c;
        margin: 1rem 0;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #f5f5f5;
        padding: 0;
        border-bottom: 1px solid #e0e0e0;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #555;
        border-radius: 0;
        padding: 12px 24px;
        font-weight: 500;
        border-bottom: 2px solid transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: #ffffff;
        color: #1967d2;
        border-bottom-color: #1967d2;
    }
    
    .stSelectbox > div > div {
        background: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 4px;
    }
    
    .stDownloadButton > button {
        background: #1967d2;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
    }
    
    .streamlit-expanderHeader {
        background: #f5f5f5;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        color: #1a1a1a;
        font-weight: 500;
    }
    
    .stMarkdown {
        color: #333;
    }
    
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        color: #1a1a1a;
        font-weight: 600;
    }
    
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    
    .stFileUploader {
        border: none !important;
    }
    
    .stApp {
        padding-top: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Cache template loading
@st.cache_data
def get_templates():
    return load_templates()


TEMPLATES = get_templates()


def main():
    """Main Streamlit application."""
    st.markdown('<p class="main-header">accessipdf</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">PDF Accessibility Conversion - PDF/UA-1 Compliance</p>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("## Settings")
        st.markdown(f"**Version:** {__version__}")
        st.markdown("---")
        st.markdown("## About")
        st.markdown(
            "accessipdf converts existing PDFs to PDF/UA-1 compliant accessible documents."
        )
        st.markdown(
            "The conversion is template-driven, ensuring pixel-perfect output."
        )
        st.markdown("---")
        st.markdown("## Links")
        st.markdown("[GitHub Repository](https://github.com/mkupermann/accessipdf)")
        st.markdown("[PDF/UA Standard](https://www.pdfa.org/standard/pdfua/)")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Single PDF", "Folder", "Identify Layout", "Validate", "Batch"]
    )

    with tab1:
        page_single()
    with tab2:
        page_folder()
    with tab3:
        page_identify()
    with tab4:
        page_validate()
    with tab5:
        page_batch()


def page_single():
    """Convert a single PDF file."""
    st.markdown("## Convert Single PDF")
    st.markdown("Upload a PDF file to convert it to an accessible PDF/UA-1 compliant version.")

    uploaded_file = st.file_uploader(
        "Select PDF file",
        type=["pdf"],
        key="single_upload",
        help="Select a PDF file to convert",
    )

    if uploaded_file:
        process_upload(uploaded_file)


def page_folder():
    """Convert all PDFs in a folder."""
    st.markdown("## Convert PDF Folder")
    st.markdown("Select multiple PDF files from a folder for batch conversion.")

    uploaded_files = st.file_uploader(
        "Select PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="folder_upload",
        help="Select one or more PDF files",
    )

    if uploaded_files:
        st.info(f"{len(uploaded_files)} PDF(s) selected")
        if st.button("Convert All", type="primary"):
            process_batch(uploaded_files)


def page_identify():
    """Identify PDF layout."""
    st.markdown("## Identify PDF Layout")
    st.markdown("Upload a PDF to identify which template it matches.")

    uploaded_file = st.file_uploader(
        "Select PDF file",
        type=["pdf"],
        key="identify_upload",
    )

    if uploaded_file:
        with st.spinner("Analyzing..."):
            with tempfile.TemporaryDirectory() as tmpdir:
                pdf_path = Path(tmpdir) / uploaded_file.name
                with open(pdf_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                try:
                    with pikepdf.open(pdf_path) as pdf:
                        ops = [walk_page(pdf, page) for page in pdf.pages]
                    template = identify_template(ops, TEMPLATES)

                    if template:
                        st.markdown(
                            '<div class="success-box">'
                            f"Layout identified: <strong>{template.name}</strong>"
                            "</div>",
                            unsafe_allow_html=True,
                        )
                        show_template_details(template)
                    else:
                        st.markdown(
                            '<div class="error-box">'
                            "Could not identify layout. This PDF does not match any registered template."
                            "</div>",
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    st.error(f"Error: {str(e)}")


def page_validate():
    """Validate PDF/UA-1 compliance."""
    st.markdown("## Validate PDF/UA-1 Compliance")
    st.markdown("Check if a PDF meets the PDF/UA-1 accessibility standard.")

    uploaded_file = st.file_uploader(
        "Select PDF file",
        type=["pdf"],
        key="validate_upload",
    )

    if uploaded_file:
        with st.spinner("Validating..."):
            with tempfile.TemporaryDirectory() as tmpdir:
                pdf_path = Path(tmpdir) / uploaded_file.name
                with open(pdf_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                try:
                    validation = validate_ua1(str(pdf_path))

                    if validation.passed:
                        st.markdown(
                            '<div class="success-box">'
                            "PDF/UA-1 VALIDATION PASSED"
                            "</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown("This PDF meets all PDF/UA-1 accessibility requirements.")
                    else:
                        st.markdown(
                            '<div class="error-box">'
                            f"PDF/UA-1 VALIDATION FAILED ({len(validation.failed_rules)} rules)"
                            "</div>",
                            unsafe_allow_html=True,
                        )
                        with st.expander("Failed Rules"):
                            for rule in validation.failed_rules:
                                st.code(rule)
                except Exception as e:
                    st.error(f"Error: {str(e)}")


def page_batch():
    """Batch convert multiple PDFs."""
    st.markdown("## Batch Convert PDFs")
    st.markdown("Upload multiple PDFs for batch conversion.")

    uploaded_files = st.file_uploader(
        "Select PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="batch_upload",
    )

    if uploaded_files:
        st.info(f"{len(uploaded_files)} file(s) selected")
        if st.button("Convert All", type="primary"):
            process_batch(uploaded_files)


def process_upload(uploaded_file):
    """Process single PDF upload."""
    with st.spinner("Identifying layout..."):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_pdf = tmpdir_path / uploaded_file.name
            with open(input_pdf, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with pikepdf.open(input_pdf) as pdf:
                ops = [walk_page(pdf, page) for page in pdf.pages]
            template = identify_template(ops, TEMPLATES)

            if not template:
                st.markdown(
                    '<div class="error-box">'
                    "Could not identify layout. This PDF does not match any registered template."
                    "</div>",
                    unsafe_allow_html=True,
                )
                return

            st.markdown(
                '<div class="success-box">'
                f"Layout: {template.name}"
                "</div>",
                unsafe_allow_html=True,
            )

            if st.button("Convert", type="primary"):
                with st.spinner("Converting..."):
                    output_dir = tmpdir_path / "output"
                    output_dir.mkdir()
                    quarantine_dir = tmpdir_path / "quarantine"
                    quarantine_dir.mkdir()

                    result = convert(str(input_pdf), str(output_dir), str(quarantine_dir))
                    output_pdf = output_dir / uploaded_file.name

                    if result.status == "ok" and output_pdf.exists():
                        st.markdown(
                            '<div class="success-box">'
                            "Conversion successful!"
                            "</div>",
                            unsafe_allow_html=True,
                        )

                        with st.spinner("Validating..."):
                            validation = validate_ua1(str(output_pdf))
                            if validation.passed:
                                st.markdown(
                                    '<div class="success-box">'
                                    "PDF/UA-1 VALID"
                                    "</div>",
                                    unsafe_allow_html=True,
                                )

                        st.markdown("### Download")
                        col1, col2 = st.columns(2)
                        with col1:
                            with open(output_pdf, "rb") as f:
                                st.download_button(
                                    "Download Accessible PDF",
                                    f,
                                    file_name=f"accessible_{uploaded_file.name}",
                                    mime="application/pdf",
                                )
                        with col2:
                            with open(input_pdf, "rb") as f:
                                st.download_button(
                                    "Download Original",
                                    f,
                                    file_name=uploaded_file.name,
                                    mime="application/pdf",
                                )
                    else:
                        st.markdown(
                            '<div class="error-box">'
                            f"Conversion failed: {result.grund}"
                            "</div>",
                            unsafe_allow_html=True,
                        )


def process_batch(uploaded_files):
    """Process batch PDF conversion."""
    with st.spinner("Processing..."):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            output_dir = tmpdir_path / "output"
            output_dir.mkdir()
            quarantine_dir = tmpdir_path / "quarantine"
            quarantine_dir.mkdir()

            results = []
            output_files = []

            for uploaded_file in uploaded_files:
                input_pdf = tmpdir_path / uploaded_file.name
                with open(input_pdf, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                result = convert(str(input_pdf), str(output_dir), str(quarantine_dir))
                results.append((uploaded_file.name, result))

                if result.status == "ok":
                    output_pdf = output_dir / uploaded_file.name
                    if output_pdf.exists():
                        output_files.append(output_pdf)

            ok_count = sum(1 for _, r in results if r.status == "ok")
            quar_count = sum(1 for _, r in results if r.status == "quarantaene")
            err_count = sum(1 for _, r in results if r.status == "fehler")

            st.markdown("### Results")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Successful", ok_count)
            with col2:
                st.metric("Quarantined", quar_count)
            with col3:
                st.metric("Errors", err_count)

            with st.expander("Details"):
                for filename, result in results:
                    status = {"ok": "OK", "quarantaene": "Quarantined", "fehler": "Error"}[result.status]
                    st.markdown(f"**{filename}**: {status}")

            if output_files:
                import zipfile

                zip_path = tmpdir_path / "accessible_pdfs.zip"
                with zipfile.ZipFile(zip_path, "w") as zipf:
                    for output_file in output_files:
                        zipf.write(output_file, arcname=output_file.name)

                with open(zip_path, "rb") as f:
                    st.download_button(
                        "Download All as ZIP",
                        f,
                        file_name="accessible_pdfs.zip",
                        mime="application/zip",
                    )


def show_template_details(template):
    """Display template details."""
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Name:** {template.name}")
        st.write(f"**Language:** {template.sprache}")
    with col2:
        st.write(f"**Title Pattern:** {template.titel_muster}")
        st.write(f"**Unknown Role:** {template.unbekannt_als}")
    if template.zonen:
        st.write(f"**Zones:** {len(template.zonen)}")


if __name__ == "__main__":
    main()
