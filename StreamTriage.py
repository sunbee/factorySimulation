import streamlit as st
import triage_model
import pandas as pd

st.title("Simply Simpy!")

st.header("Simulation for Production Planning and Process Improvement")

st.markdown("""
Refer to Jupyter Notebooks for process models used in simulation here.
- **generator**.ipynb - use a generator function to meet concurrency needs of process simulation
- **dietician**.ipynb - simulate a one-step process of dietary consultation
- **clinic**.ipyb - simulate a multi-step process of consultation in a medical clinic
- **triage**.ipynb - simulate a non-linear process of clinic with triage""")

p = triage_model.Process()
res = p.run_once()
st.write(res)

sim_runs = 30
sim_results = []
for i in range(0, sim_runs):
    p = triage_model.Process()
    sim_results.append(p.run_once())
st.dataframe(pd.DataFrame(sim_results))

st.sidebar.slider("How many runs?", 30, 100)

