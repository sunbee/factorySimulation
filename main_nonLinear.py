'''
Simulate a clinic with triage.
People visit the clinic for registration and triage.
Entity: People arriving at clinic
Generator: Arrivals 
Inter-Arrrival Time: An exponential distribution
Activity: 1. Registration 2. Triage
Activity Time: Both activities present an exponential distribution 
Resources: 1. Receptionist 2. Nurse
Queues: People waiting for each activity 
Sink: Exit after triage

Based on: https://youtu.be/jXDjrWKcu6w
'''

import simpy
import random

def send_arrivals(env, mean_IAT, mean_CT2register, mean_CT2triage, mean_CT2assessInpatient, mean_CT2assessOutpatient, 
                    receptionist, nurse, doctor_inpatient, doctor_outpatient):
    token_number = 0;

    # run indefintely
    while(True):
        # Send an arrival onward
        Consultation = process_me(env, mean_CT2register, mean_CT2triage, mean_CT2assessInpatient, mean_CT2assessOutpatient, 
                                    receptionist, nurse, doctor_inpatient, doctor_outpatient, token_number)
        env.process(Consultation) 

        # Generate new arrival
        time_delta_queue = random.expovariate(1.0 / mean_IAT)
        yield env.timeout(time_delta_queue)

        token_number += 1

def process_me(env, mean_CT2register, mean_CT2triage, mean_CT2assessInpatient, mean_CT2assessOutpatient, 
                                    receptionist, nurse, doctor_inpatient, doctor_outpatient, token_number):
    global queued4registration
    global queued4triage
    global leadTimes

    time_arrived = env.now
    print("{} arrived at {:.2f}".format(token_number, time_arrived))

    # Request a receptionist for registration
    with receptionist.request() as req:
        # Wait until receptionist is available
        yield req

        time_started_registration = env.now
        time_delta_queued4registration = time_started_registration - time_arrived
        print("{} started registration at {:.2f} after waiting {:.2f}".format(token_number, time_started_registration, time_delta_queued4registration))
        queued4registration.append(time_delta_queued4registration)

        time_delta_registration = random.expovariate(1.0 / mean_CT2register)

        yield env.timeout(time_delta_registration)

    time_arrived4triage = env.now

    with nurse.request() as req:
        # Wait until nurse is available
        yield req
        
        time_started_triage = env.now
        time_delta_queued4triage = time_started_triage - time_arrived4triage
        print("{} started triage at {:.2f} after waiting {:.2f}".format(token_number, time_started_triage, time_delta_queued4triage))
        queued4triage.append(time_arrived4triage)

        time_delta_triage = random.expovariate(1.0 / mean_CT2triage)

        yield env.timeout(time_delta_triage)

    time_exited = env.now
    time_delta_start2finish = time_exited - time_arrived
    print("{} HAD LEAD TIME OF {:.0f} MINUTES.".format(token_number, time_delta_start2finish))
    leadTimes.append(time_delta_start2finish)

# Set up the simulation environment
env = simpy.Environment()

# Set up the resources
receptionist = simpy.Resource(env, capacity=1)
nurse = simpy.Resource(env, capacity=2)
doctor_inpatient = simpy.Resource(env, capacity=2)
doctor_outpatient = simpy.Resource(env, capacity=1)

# Configure simulation parameters
mean_IAT = 8
mean_CT2register = 2
mean_CT2triage = 5
mean_CT2assessInpatient = 30
mean_CT2assessOutpatient = 60

# Lists of Globals
queued4registration = []
queued4triage = []
leadTimes = []

# Make it so
env.process(send_arrivals(env, mean_IAT, mean_CT2register, mean_CT2triage, receptionist, nurse))
env.run(until=120)

print(leadTimes)
