"""Financial Intelligence Studio Streamlit entry point."""
from pathlib import Path
import runpy


runpy.run_path(str(Path(__file__).with_name("product_ui.py")), run_name="__main__")
