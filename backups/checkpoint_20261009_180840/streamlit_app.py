"""Stable Streamlit entry point: ``streamlit run streamlit_app.py``.

Streamlit reruns this file for every browser session.  A normal ``import client``
only executes once because Python caches imported modules, which left later
sessions with a blank page. ``run_path`` executes the UI script on every rerun.
"""
from pathlib import Path
import runpy


runpy.run_path(str(Path(__file__).with_name("client.py")), run_name="__main__")
