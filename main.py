'''
Simulate a process of dietary consultation.
People visit the clinic and see the consultant.
Entity: People arriving for dietary consultation
Generator: Arrivals for dietary consultation 
Inter-Arrrival Time: An exponential distribution
Activity: Consultation with dietician
Activity Time: Consultation time, exponential distribution
Resources: Dietician (1)
Queues: People waiting for consultation 
Sink: Exit after consultation

Based on: https://youtu.be/jXDjrWKcu6w
'''
import simpy
import random
import configuration

def send_arrivals(env, mean_IAT, mean_CT, dietician):
    token_number = 0;

    # run indefintely
    while(True):
        # Send an arrival onward
        Consultation = consult_me(env, mean_CT, dietician, token_number)
        env.process(Consultation) 

        # Generate new arrival
        time_delta_queue = random.expovariate(1.0 / mean_IAT)
        yield env.timeout(time_delta_queue)

        token_number += 1

def consult_me(env, mean_CT, dietician, token_number):
    time_arrived = env.now
    print("Patient {} entered the queue at {:.2f}".format(token_number, time_arrived))

    with dietician.request() as req:
        # Wait until the dietician is available
        yield req

        time_consultation_started = env.now
        time_delta_queued = time_consultation_started - time_arrived

        time_delta_consultation = random.expovariate(1.0 / mean_CT)
        print("Patient {} entered consultation at {:.2f}, having waited {:.2f}".format(token_number, time_arrived, time_delta_queued))
        yield env.timeout(time_delta_consultation)

# Set up the simulation environment
env = simpy.Environment()

# Set up the resources
dietician = simpy.Resource(env, 1)

# Configure simulation parameters
mean_IAT = 5
mean_CT = 6

# Make it so!
env.process(send_arrivals(env, mean_IAT, mean_CT, dietician))
env.run(until=540)