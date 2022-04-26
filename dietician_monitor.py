import simpy
import random
from numpy import median
from functools import partial, wraps

def patch_resource(resource, pre=None, post=None):
    """
    Decorates the get/request and put/release methods of Simpy resource
    with features for monitoring, logging the attributes with timestamp.
    Implementation implements and extends the decorator pattern as follows:
    1. Define a wrapper that wraps the call to resource get/put or request/release method in pre and/or post callables. 
    2. Return the wrapper function. Note that pre and post take resource as the only argument.
    3. Replace the resource's original methods with the decorated versions. Treat methods as attributes and get/set to update.
    """
    def get_wrapper(func): # func can be get/put or request/release
        @wraps(func)
        def wrapper(*args, **kwargs):
            if pre:
                pre(resource)
            
            ret = func(*args, **kwargs) # Perform get/put or request/release operation

            if post:
                post(resource)

            return ret
        return wrapper

    # Decorate original  get/put or request/release methods
    for name in ['get', 'put', 'request', 'release']:
        if hasattr(resource, name):
            setattr(resource, name, get_wrapper(getattr(resource, name)))    

def get_monitor(data):
    def monitor(resource):
        data.append((
            resource._env.now,      # simulation timestamp
            resource.count,         # number of consumers
            len(resource.queue)     # number of queued processes 
        ))
    return monitor

class G:
    # Simulation settings
    number_of_runs = 30
    simulation_horizon = 120

    # Resourcing
    number_of_dieticians = 1

    # Model parameters
    mean_IAT = 5 
    mean_CT = 6

    # Information gathering
    arrived = []
    queued = []

    # Monitoring
    dietician_utilization = []  # From process
    dietician_count = []        # From monkey-patching some of a resource's methods 

class Patient:
    """
    An entity and attributes
    """
    def __init__(self, patient_ID) -> None:
        self.ID = patient_ID

class Consultation:
    def __init__(self) -> None:
        self.env = simpy.Environment()
        self.dietician = simpy.Resource(self.env, 1)
        self.patient_counter = 0

    def generate_patient(self):
        # run indefintely
        while(True):
            # Generate next arrival
            self.patient_counter += 1
            patient = Patient(self.patient_counter)

            # Send an arrival onward
            Consultation = self.generate_consultation(self, patient)
            self.env.process(Consultation) 

            # Await new arrival
            deltaIAT = random.expovariate(1.0 / G.mean_IAT)
            yield self.env.timeout(deltaIAT)

    def generate_consultation(self, patient):
        arrived = self.env.now
        G.arrived.append(arrived)
        print("Patient {} entered the queue at {:.2f}".format(patient.ID, time_arrived))

        with self.dietician.request() as req:
            # Wait until the dietician is available
            yield req

            started = self.env.now
            queued = started - arrived

            G.queued.append(queued)

            delta = random.expovariate(1.0 / self.mean_CT)
            print("Patient {} entered consultation at {:.2f}, having waited {:.2f}".format(patient.ID, arrived, queued))
            yield self.env.timeout(delta)
            
    def run_once(self):
        self.env.process(self.generate_patient())
        self.env.run(until=30)