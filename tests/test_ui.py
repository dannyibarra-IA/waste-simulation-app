"""Prueba funcional: cada módulo de la interfaz se ejecuta sin excepciones (Streamlit AppTest)."""
import pytest
from streamlit.testing.v1 import AppTest

PAGES = ["pages_a.page_national", "pages_a.page_profile", "pages_a.page_trends", "pages_a.page_composition", "pages_b.page_dynamics", "pages_b.page_scenarios",
         "pages_b.page_flows", "pages_b.page_compare", "pages_c.page_risks", "pages_c.page_uncertainty", "pages_c.page_methods", "pages_c.page_downloads"]

SCRIPT = """
import sys; sys.path.insert(0, {root!r})
import streamlit as st
from ui.common import CSS, sidebar
from ui.{mod} import {fn}
st.session_state.setdefault('lang', {lang!r})
sidebar()
{fn}()
"""


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("lang", ["es", "en"])
def test_page_runs(page, lang):
    import pathlib
    root = str(pathlib.Path(__file__).resolve().parents[1])
    mod, fn = page.split(".")
    at = AppTest.from_string(SCRIPT.format(root=root, mod=mod, fn=fn, lang=lang), default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]


def test_main_app_runs():
    import pathlib
    at = AppTest.from_file(str(pathlib.Path(__file__).resolve().parents[1] / "app.py"), default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
