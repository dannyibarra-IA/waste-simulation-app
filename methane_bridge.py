"""Adapter to RMI SWEET: final disposed mass, not generated mass."""
import numpy as np
import pandas as pd

COMPONENTS = ("food","green","wood","paper_cardboard","textiles","plastic","metal","glass","rubber","other")

def run_site(baseline, scenario, composition_baseline, composition_scenario, *,
             precipitation, temperature, implement_year, open_year, close_year,
             capture_baseline=0., capture_scenario=0., landfill_type=0):
    """Inputs: annual disposed tonnes and matching residual composition DataFrames.
    Both series must include the complete operating history through closure.
    Returns annual landfill methane in tonnes, not a full life-cycle inventory.
    """
    from SWEET_python.advanced_dst import AdvancedDSTRequest, run_advanced_dst
    from SWEET_python.constants import GWP100_CH4
    years = list(range(open_year, close_year+1))
    if not open_year <= implement_year <= close_year:
        raise ValueError("Implementation year outside operating history")
    def validate(mass, composition):
        if list(mass.index) != years or list(composition.index) != years:
            raise ValueError("Supply every operating year, including historical deposits")
        m = mass.to_numpy(dtype=float)
        f = composition.loc[:, list(COMPONENTS)].to_numpy(dtype=float)
        if not np.isfinite(m).all() or (m<0).any() or not np.isfinite(f).all() or (f<0).any() or not np.allclose(f.sum(axis=1),1):
            raise ValueError("Invalid mass or residual composition")
        return dict(zip(years,m.tolist())), dict(zip(years,f.tolist()))
    b,bf=validate(baseline,composition_baseline)
    s,sf=validate(scenario,composition_scenario)
    if any(not 0<=x<=1 for x in (capture_baseline,capture_scenario)):
        raise ValueError("Capture must be between zero and one")
    if not np.isfinite([precipitation,temperature]).all() or precipitation<0:
        raise ValueError("Invalid climate")
    def v(b,s=None): return {"baseline":b,"scenario":s}
    req=AdvancedDSTRequest(precipitation=precipitation,temperature=temperature,
        implement_year=implement_year,waste_mass=v(b,s),waste_fractions=v(bf,sf),
        landfill_type=v(landfill_type),landfill_open_close=v((open_year,close_year)),
        gas_capture_efficiency=v({y:capture_baseline for y in years},{y:capture_scenario for y in years}))
    result=run_advanced_dst(req)
    out=pd.DataFrame({"baseline_t_CH4":result["baseline"]["total"],"scenario_t_CH4":result["scenario"]["total"]})
    out["avoided_t_CH4"]=out.baseline_t_CH4-out.scenario_t_CH4
    out["avoided_t_CO2e"]=out.avoided_t_CH4*GWP100_CH4
    return out
