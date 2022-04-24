from matplotlib.pyplot import title
import streamlit as st
from triage_model import G, Patient, Process
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

st.sidebar.subheader("Inter-Arrival Times")
G.mean_IAT = st.sidebar.number_input("Inter-Arrival Time", min_value=1, value=8)

with st.sidebar.container():
    st.sidebar.subheader("Resources")
    G.number_of_receptionists = st.sidebar.number_input("How many receptionists?", min_value=1, value=1)
    G.number_of_nurses = st.sidebar.number_input("How many nurses?", min_value=1, value=2)
    G.number_of_doctorsOPD = st.sidebar.number_input("How many doctors - OPD?", min_value=1, value=1)
    G.number_of_doctorsER = st.sidebar.number_input("How many doctors - ER?", min_value=1, value=2)

sim_results = []
for i in range(0, sim_runs):
    p = Process()
    sim_results.append(p.run_once())
df = pd.DataFrame(sim_results)

st.subheader("Single Run")

st.write("A single run generates metrics as follows:")

p = Process()
res = p.run_once()
st.write(res)
st.subheader("Queuing Times")

hQ4R = ggplot(df, aes(x="Queued4Registration")) \
                + geom_histogram(fill="pink", color="deeppink") \
                + ggtitle(f"{G.number_of_receptionists} Receptionists @ REGISTRATION") \
                + xlab("Time in queue @ Reception")

hQ4T = ggplot(df, aes(x="Queued4Triage")) \
                + geom_histogram(fill="pink", color="deeppink") \
                + ggtitle(f"{G.number_of_nurses} Nurses @ TRIAGE") \
                + xlab("Time in queue @ Triage")

container_one = st.container()
col_left, col_right = st.columns(2)

with container_one:
    with col_left:
        st.pyplot(ggplot.draw(hQ4R))
    with col_right:
        st.pyplot(ggplot.draw(hQ4T))

hQ4O = ggplot(df, aes(x="Queued4AssessmentOPD")) \
                + geom_histogram(fill="pink", color="deeppink") \
                + ggtitle(f"{G.number_of_doctorsOPD} Doctors @ OPD") \
                + xlab("Time in queue @ OPD") \
                + geom_vline(xintercept=sum(df.Queued4AssessmentOPD)/len(df.Queued4AssessmentOPD))
hQ4E = ggplot(df, aes(x="Queued4AssessmentER")) \
                + geom_histogram(fill="pink", color="deeppink") \
                + ggtitle(f"{G.number_of_doctorsER} Doctors @ ER") \
                + xlab("Time in queue @ ER") \
                + geom_vline(xintercept=sum(df.Queued4AssessmentER)/len(df.Queued4AssessmentER))

container_two = st.container()
col_left, col_right = st.columns(2)

with container_two:
    with col_left:
        st.pyplot(ggplot.draw(hQ4O))
    with col_right:
        st.pyplot(ggplot.draw(hQ4E))

hTAT = ggplot(df, aes(x="TAT")) \
                + geom_histogram(fill="cyan", color="magenta") \
                + ggtitle(f"LEAD TIME (END-END), IAT {G.mean_IAT}") \
                + xlab("End-End TAT") \
                + geom_vline(xintercept=sum(df.TAT)/len(df.TAT))
hTex = """
### Identifying Bottlenecks
The plots show queueing times.
Steps that have long queues forming
before them are likely choke-points.
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
