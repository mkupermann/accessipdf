"""Streamlit GUI for accessipdf - PDF Accessibility Conversion."""

import tempfile
from pathlib import Path

import pikepdf
import streamlit as st

from accessipdf import __version__
from accessipdf.pipeline import convert
from accessipdf.tagging.walker import walk_page
from accessipdf.templates.loader import identify as identify_template
from accessipdf.templates.loader import load_templates
from accessipdf.validate.verapdf import validate_ua1

# Page configuration
st.set_page_config(
    page_title="accessipdf",
    layout="wide",
    initial_sidebar_state="expanded",
)

# accessipdf's own subject is PDF/UA tags — the structure the tool adds to a
# document. The status language below (`<pass>`, `<identified: …>`) borrows
# that same angle-bracket syntax instead of generic colored alert boxes, so
# the interface reads with the same vocabulary as the thing it's reporting
# on. Fraunces (a document, not a dashboard, deserves a serif) pairs with
# the existing IBM Plex Sans/Mono family already used for the tag chips.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {
        --ink: #1c1a16;
        --ink-soft: #55493c;
        --paper: #faf6ee;
        --paper-raised: #ffffff;
        --rule: #e2d9c8;
        --accent: #2f6f5e;
        --accent-soft: #e7efe9;
        --flag-fail: #a8412f;
        --flag-fail-soft: #f5e6e1;
        --flag-warn: #8a6420;
        --flag-warn-soft: #f4ecd8;
    }

    * { font-family: 'IBM Plex Sans', sans-serif; }

    .stApp, section[data-testid="stSidebar"], .main .block-container {
        background: var(--paper);
        color: var(--ink);
    }

    .stMarkdown, .stMarkdown p, .stMarkdown li { color: var(--ink-soft); }
    /* .stMarkdown p (two selectors) otherwise beats the single-class rules
       below, silently recoloring the header back to body-text ink-soft. */
    .stMarkdown p.main-header { color: var(--ink); }
    .stMarkdown span.eyebrow { color: var(--accent); }

    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        font-family: 'Fraunces', serif;
        color: var(--ink);
        font-weight: 600;
        text-wrap: balance;
    }

    .eyebrow {
        display: block;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        color: var(--accent);
        letter-spacing: 0.02em;
        margin-bottom: 0.35rem;
    }

    .main-header {
        font-family: 'Fraunces', serif;
        font-size: 2.4rem;
        font-weight: 600;
        color: var(--ink);
        margin: 0;
        line-height: 1.1;
    }

    .sub-header {
        font-size: 1rem;
        color: var(--ink-soft);
        margin: 0.4rem 0 1rem;
    }

    .header-rule {
        border: none;
        border-top: 1px dashed var(--rule);
        margin: 0 0 1.75rem;
    }

    /* The tag-chip status language — one visual family for every pass/fail/
       identify/quarantine state the tool reports, in the tool's own syntax. */
    .tag-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.4em;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.9rem;
        padding: 0.55rem 0.9rem;
        border-radius: 3px;
        border: 1px solid transparent;
        margin: 0.6rem 0;
    }
    .tag-chip.tag-ok { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
    .tag-chip.tag-fail { background: var(--flag-fail-soft); border-color: var(--flag-fail); color: var(--flag-fail); }
    .tag-chip.tag-warn { background: var(--flag-warn-soft); border-color: var(--flag-warn); color: var(--flag-warn); }
    .tag-chip.tag-info { background: var(--paper-raised); border-color: var(--rule); color: var(--ink-soft); }

    .stButton > button, .stDownloadButton > button {
        background: var(--paper-raised);
        color: var(--ink);
        border: 1.5px solid var(--ink);
        border-radius: 3px;
        padding: 0.5rem 1.4rem;
        font-size: 0.9rem;
        font-weight: 500;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: var(--accent);
        color: var(--accent);
    }
    .stButton > button[kind="primary"] {
        background: var(--accent);
        color: var(--paper-raised);
        border-color: var(--accent);
    }
    .stButton > button[kind="primary"]:hover {
        background: #24594b;
        color: var(--paper-raised);
    }

    .stFileUploader > div > div > div {
        background: var(--paper-raised);
        border: 1.5px dashed var(--rule);
        border-radius: 3px;
        padding: 2rem;
    }
    .stFileUploader { border: none !important; }

    section[data-testid="stSidebar"] {
        border-right: 1px solid var(--rule);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
        background: transparent;
        padding: 0;
        border-bottom: 1px solid var(--rule);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: var(--ink-soft);
        font-family: 'Fraunces', serif;
        font-size: 1.05rem;
        border-radius: 0;
        padding: 8px 2px 12px;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: var(--ink);
        border-bottom-color: var(--accent);
    }
    /* The visible active-tab underline isn't the tab's own border — it's a
       separate indicator element React Aria draws in Streamlit's default red. */
    .react-aria-SelectionIndicator {
        background: var(--accent) !important;
    }

    .stSelectbox > div > div {
        background: var(--paper-raised);
        border: 1px solid var(--rule);
        border-radius: 3px;
    }

    .streamlit-expanderHeader {
        background: var(--paper-raised);
        border: 1px solid var(--rule);
        border-radius: 3px;
        color: var(--ink);
        font-weight: 500;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def tag_chip(text: str, kind: str = "info") -> str:
    """Render a status as a monospace angle-bracket tag, matching the PDF/UA
    tag vocabulary the tool itself produces, instead of a generic alert box."""
    return f'<div class="tag-chip tag-{kind}">&lt;{text}&gt;</div>'


# Cache template loading
@st.cache_data
def get_templates():
    return load_templates()


TEMPLATES = get_templates()


def main():
    """Main Streamlit application."""
    st.markdown(
        '<span class="eyebrow">&lt;Document&gt;</span>'
        '<p class="main-header">accessipdf</p>'
        '<p class="sub-header">Tags existing PDFs for PDF/UA-1, without touching how they look.</p>'
        '<hr class="header-rule" />',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown('<span class="eyebrow">&lt;Settings&gt;</span>', unsafe_allow_html=True)
        st.markdown(f"**Version:** {__version__}")
        st.markdown("---")
        st.markdown('<span class="eyebrow">&lt;About&gt;</span>', unsafe_allow_html=True)
        st.markdown(
            "accessipdf tags existing PDFs for PDF/UA-1 compliance, template-driven, "
            "pixel-identical to the source."
        )
        st.markdown("---")
        st.markdown('<span class="eyebrow">&lt;Links&gt;</span>', unsafe_allow_html=True)
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
                            tag_chip(f"identified: {template.name}", "ok"), unsafe_allow_html=True
                        )
                        show_template_details(template)
                    else:
                        st.markdown(tag_chip("unidentified", "fail"), unsafe_allow_html=True)
                        st.caption("This PDF does not match any registered template.")
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
                        st.markdown(tag_chip("pass", "ok"), unsafe_allow_html=True)
                        st.caption("This PDF meets all PDF/UA-1 accessibility requirements.")
                    else:
                        st.markdown(
                            tag_chip(f"fail · {len(validation.failed_rules)} rules", "fail"),
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
                st.markdown(tag_chip("unidentified", "fail"), unsafe_allow_html=True)
                st.caption("This PDF does not match any registered template.")
                return

            st.markdown(tag_chip(f"identified: {template.name}", "ok"), unsafe_allow_html=True)

            if st.button("Convert", type="primary"):
                with st.spinner("Converting..."):
                    output_dir = tmpdir_path / "output"
                    output_dir.mkdir()
                    quarantine_dir = tmpdir_path / "quarantine"
                    quarantine_dir.mkdir()

                    result = convert(str(input_pdf), str(output_dir), str(quarantine_dir))
                    output_pdf = output_dir / uploaded_file.name

                    if result.status == "ok" and output_pdf.exists():
                        st.markdown(tag_chip("converted", "ok"), unsafe_allow_html=True)

                        with st.spinner("Validating..."):
                            validation = validate_ua1(str(output_pdf))
                            if validation.passed:
                                st.markdown(tag_chip("pass", "ok"), unsafe_allow_html=True)

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
                        st.markdown(tag_chip("failed", "fail"), unsafe_allow_html=True)
                        st.caption(result.grund)


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
                chip_kind = {"ok": "ok", "quarantaene": "warn", "fehler": "fail"}
                chip_label = {"ok": "ok", "quarantaene": "quarantined", "fehler": "error"}
                for filename, result in results:
                    st.markdown(
                        f"**{filename}** "
                        + tag_chip(chip_label[result.status], chip_kind[result.status]),
                        unsafe_allow_html=True,
                    )

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
