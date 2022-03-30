import streamlit as st
import triage_model
import pandas as pd
from plotnine import *

st.title("Simply Simpy!")

st.header("Simulation for Production Planning and Process Improvement")

st.markdown("""
Refer to Jupyter Notebooks for process models used in simulation here.
- **generator**.ipynb - use a generator function to meet concurrency needs of process simulation
- **dietician**.ipynb - simulate a one-step process of dietary consultation
- **clinic**.ipyb - simulate a multi-step process of consultation in a medical clinic
- **triage**.ipynb - simulate a non-linear process of clinic with triage""")

sim_runs = st.sidebar.slider("How many runs?", 30, 100)
sim_results = []
for i in range(0, sim_runs):
    p = triage_model.Process()
    sim_results.append(p.run_once())
df = pd.DataFrame(sim_results)

st.subheader("Single Run")

st.write("A single run generates metrics as follows:")

p = triage_model.Process()
res = p.run_once()
st.write(res)
st.subheader("Queuing Times")

hQ4R = ggplot(df, aes(x="Queued4Registration")) + geom_histogram(fill="pink", color="deeppink")
hQ4T = ggplot(df, aes(x="Queued4Triage")) + geom_histogram(fill="pink", color="deeppink")

container_one = st.container()
col_left, col_right = st.columns(2)

with container_one:
    with col_left:
        st.pyplot(ggplot.draw(hQ4R))
    with col_right:
        st.pyplot(ggplot.draw(hQ4T))

hQ4O = ggplot(df, aes(x="Queued4AssessmentOPD")) + geom_histogram(fill="pink", color="deeppink")
hQ4E = ggplot(df, aes(x="Queued4AssessmentER")) + geom_histogram(fill="pink", color="deeppink")

container_two = st.container()
col_left, col_right = st.columns(2)

with container_two:
    with col_left:
        st.pyplot(ggplot.draw(hQ4O))
    with col_right:
        st.pyplot(ggplot.draw(hQ4E))

hTAT = ggplot(df, aes(x="TAT")) + geom_histogram(fill="cyan", color="magenta")
hTex = """
### OK
Good for you.
Hare Krishna, Hare Krisha,
Krishna, Krishna, Hare, Hare.
Hare Rama, Hare Rame,
Rama, Rama, Hare, Hare
"""
container_three = st.container()
col_left, col_right = st.columns(2)

with container_three:
    with col_left:
        st.pyplot(ggplot.draw(hTAT))
    with col_right:
        st.write(hTex)

st.subheader("Raw Data")

st.dataframe(df)
