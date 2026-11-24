# Waste Simulation Lab V5 — Danny Ibarra, Ph.D.
Experimental branch; existing Streamlit application preserved.

## Upstream
RMI SWEET_python, pinned commit 631325f268798755c117621602c12a05b0facc7d.
https://github.com/RMI/SWEET_python
Install: pip install -r requirements-v5.txt
The adapter imports upstream rather than copying its source. Preserve upstream license notices in distributions.

## Scientific boundary
Use the existing results_df Landfilled_t output, not Generated_t, with separately documented residual composition by ten materials and historical site deposits. The single-site API avoids applying diversion yields twice. For shared facilities aggregate city contributions once, and for multiple facilities allocate by observed site shares. Uncollected waste and treatment emissions are excluded. No inferred climate or composition is silently substituted.

## Web architecture
Retain Streamlit for the first integration to minimize regressions. Planned navigation: overview, geographic explorer, urban simulation, landfill methane, uncertainty, methodology. A separate React/API migration is deferred until parity is demonstrated.

## Acceptance gates
Run upstream tests; test adapter against identical scenarios, zero deposits, capture changes and historical carryover. Validate against site observations and document uncertainty. Do not publish estimates as measured emissions. The existing app is not yet wired to this adapter; this is a development scaffold.
