import resource
from statistics import median
import matplotlib.pyplot as plt
import streamlit as st
from triage_model import G, Patient, Process, gggauge, patch_resource, get_monitor
import pandas as pd
from plotnine import *

st.title("Simply Simpy!")

st.header("Simulation for Production Planning and Process Improvement")

st.markdown("""
Refer to Jupyter Notebooks for process models used in simulation here.
- **generator**.ipynb - use a generator function to meet concurrency needs of process simulation
- **dietician**.ipynb - simulate a one-step process of dietary consultation
- **clinic**.ipyb - simulate a multi-step process of consultation in a medical clinic
- **triage**.ipynb - simulate a non-linear process of clinic with triage
- **dietician_monitor**.ipynb - simulate a one-step process with monitoring using package **dietician_monitor.py**""")

st.sidebar.subheader("Inter-Arrival Times")
G.mean_IAT = st.sidebar.number_input("Inter-Arrival Time", min_value=1, value=8)
#G.verbose = True

with st.sidebar.container():
    st.sidebar.subheader("Resources")
    G.resource_capacity["receptionist"] = st.sidebar.number_input("How many receptionists?", min_value=1, value=1)
    G.resource_capacity["nurse"] = st.sidebar.number_input("How many nurses?", min_value=1, value=2)
    G.resource_capacity["doctorOPD"] = st.sidebar.number_input("How many doctors - OPD?", min_value=1, value=1)
    G.resource_capacity["doctorER"] = st.sidebar.number_input("How many doctors - ER?", min_value=1, value=2)

st.subheader("Single Run: Summary")

p = Process()
p.monitor_capacity()
res = p.run_once(proc_monitor=True)
st.write(res)

st.subheader("Single Run: Resource Monitor")

st.write(G.utilization_event)
st.write(G.utilization_poll)

x_doctorOPD_, y_doctorOPD_, _ = list(zip(*G.utilization_event.get("doctorOPD")))
x_doctorER_,  y_doctorER_, _  = list(zip(*G.utilization_event.get("doctorER")))

UDoctorOPD_ = ggplot(aes(x=x_doctorOPD_, y=y_doctorOPD_)) \
                + geom_step() \
                + ggtitle("Doctor - OPD")

UDoctorER_ = ggplot(aes(x=x_doctorER_, y=y_doctorER_)) \
                + geom_step() \
                + ggtitle("Doctor - ER")

container_B = st.container()
col_BL, col_BR = st.columns(2)

with container_B:
    with col_BL:
        st.pyplot(ggplot.draw(UDoctorOPD_))
    with col_BR:
        st.pyplot(ggplot.draw(UDoctorER_))

x_doctorOPD, y_doctorOPD, _ = list(zip(*G.utilization_poll.get("doctorOPD")))
x_doctorER,  y_doctorER, _  = list(zip(*G.utilization_poll.get("doctorER")))

UDoctorOPD = ggplot(aes(x=x_doctorOPD, y=y_doctorOPD)) \
                + geom_step() \
                + ggtitle("Doctor - OPD")

UDoctorER = ggplot(aes(x=x_doctorER, y=y_doctorER)) \
                + geom_step() \
                + ggtitle("Doctor - ER")

container_A = st.container()
col_AL, col_AR = st.columns(2)

with container_A:
    with col_AL:
        st.pyplot(ggplot.draw(UDoctorOPD))
    with col_AR:
        st.pyplot(ggplot.draw(UDoctorER))

sim_runs = st.sidebar.slider("How many runs?", 30, 100)

st.subheader("Multiple Runs: Performance Indicators")

sim_results = []
for i in range(0, sim_runs):
    p = Process()
    p.monitor_capacity()
    sim_results.append(p.run_once())

Capacity_Utilization = {}
ggg_plots = []
for resource_type in G.resource_types:
        Capacity_Utilization[resource_type] = median([sim_result["Utilization"][resource_type] for sim_result in sim_results])
        ggg_plots.append(gggauge(Capacity_Utilization.get(resource_type)*100))
print(Capacity_Utilization)

with st.container():
    ggg_panels = st.columns(4)
    for i in range(4):
        with ggg_panels[i]:
            st.pyplot(ggplot.draw(ggg_plots[i]))

st.markdown("""___""")

Queued = {}
for resource_type in G.resource_types:
    Queued[resource_type] = [sim_result["Queued"][resource_type] for sim_result in sim_results]
Queued["TAT"] = [sim_result["Delta"]["TAT"] for sim_result in sim_results]
df = pd.DataFrame(Queued)

hQ4R = ggplot(df, aes(x="receptionist")) \
                + geom_histogram(fill="pink", color="deeppink") \
                + ggtitle("{} Receptionists @ REGISTRATION".format(G.resource_capacity["receptionist"])) \
                + xlab("Time in queue @ Reception")

hQ4T = ggplot(df, aes(x="nurse")) \
                + geom_histogram(fill="pink", color="deeppink") \
                + ggtitle("{} Nurses @ TRIAGE".format(G.resource_capacity["nurse"])) \
                + xlab("Time in queue @ Triage")

container_one = st.container()
col_left, col_right = st.columns(2)

with container_one:
    with col_left:
        st.pyplot(ggplot.draw(hQ4R))
    with col_right:
        st.pyplot(ggplot.draw(hQ4T))

hQ4O = ggplot(df, aes(x="doctorOPD")) \
                + geom_histogram(fill="pink", color="deeppink") \
                + ggtitle("{} Doctors @ OPD".format(G.resource_capacity["doctorOPD"])) \
                + xlab("Time in queue @ OPD") \
                + geom_vline(xintercept=sum(df.doctorOPD)/len(df.doctorOPD))
hQ4E = ggplot(df, aes(x="doctorER")) \
                + geom_histogram(fill="pink", color="deeppink") \
                + ggtitle("{} Doctors @ ER".format(G.resource_capacity["doctorER"])) \
                + xlab("Time in queue @ ER") \
                + geom_vline(xintercept=sum(df.doctorER)/len(df.doctorER))

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


