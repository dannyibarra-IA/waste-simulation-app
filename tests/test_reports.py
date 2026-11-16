import io
import json
import zipfile

import pandas as pd

from core.data import Repository
from core.simulation_engine import run_scenarios
from reports.report_generator import build_manifest, excel_bytes, pdf_report, zip_package


def test_exports_complete_and_traceable():
    r = Repository()
    codes = ["05001", "97001"]
    scen = ["BAU", "S2", "S7", "S9"]
    df, meta = run_scenarios(r, codes, scen)
    man = build_manifest(r, codes, scen, {"t_impl": 2027}, {"05001": {"s_rec": 0.25}}, 42, "3.0.0")
    for k in ("run_id", "ciudades", "escenarios", "horizonte", "parametros", "fuentes", "fecha_ejecucion", "code_version", "data_version", "semilla_montecarlo"):
        assert k in man
    assert man["parametros"]["05001"]["s_rec"] == {"valor": 0.25, "origen": "ajustado por el usuario"}
    x = pd.ExcelFile(io.BytesIO(excel_bytes(r, df, man)))
    assert {"manifiesto", "resultados", "parametros", "fuentes", "poblacion_DANE"} <= set(x.sheet_names)
    z = zipfile.ZipFile(io.BytesIO(zip_package(r, df, man)))
    assert {"manifest.json", "resultados.csv", "rerun.py", "data/processed/poblacion.csv"} <= set(z.namelist())
    assert json.loads(z.read("manifest.json"))["run_id"] == man["run_id"]
    pdf = pdf_report(r, df, meta, man, "05001")
    assert pdf[:4] == b"%PDF" and len(pdf) > 20000


def test_rerun_reproduces(tmp_path):
    r = Repository()
    df, meta = run_scenarios(r, ["05001"], ["BAU", "S7"], {"t_impl": 2027}, {"05001": {"s_rec": 0.25}})
    df2, _ = run_scenarios(r, ["05001"], ["BAU", "S7"], {"t_impl": 2027}, {"05001": {"s_rec": 0.25}})
    pd.testing.assert_frame_equal(df, df2)
