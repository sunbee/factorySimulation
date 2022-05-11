import simpy
import random
from numpy import median, trapz
from functools import partial, wraps

def patch_resource(resource, pre=None, post=None):
    """
    Decorates the get/request and put/release methods of Simpy resource
    with features for monitoring, logging resource attributes with timestamp
    when these methods are called.
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

def help_monitor(resource_name, ts):
    if (resource_name in G.utilization_event) \
        and (G.utilization_event.get(resource_name)[-1][0] == ts) \
        and (G.utilization_event.get(resource_name)[-1][-1] > 0):
        item = list(G.utilization_event.get(resource_name).pop(-1))
        item[1] += 1; item[2] -= 1 
        G.utilization_event.get(resource_name).append(tuple(item))

class G:
    """
    Global variable values, including the following:
    - Model parameters e.g. Inter-Arrival Time, etc.
    - Resource allocation
    - Simulation settings e.g. Number of steps in a simulation run, number of simulation runs, etc.
    Use the class attributes without instantiating an object! 
    """
    # Simulation settings
    number_runs = 30
    simulation_horizon = 540
    verbose = False

    # Resourcing
    resource_types = ['receptionist', 'nurse', 'doctorOPD', 'doctorER']
    resource_capacity = {}
    resource_capacity["receptionist"] = 1
    resource_capacity["nurse"] = 2
    resource_capacity["doctorOPD"] = 1
    resource_capacity["doctorER"] = 2
 
    # Model paramters
    mean_IAT = 8
    mean_CT2register = 2
    mean_CT2triage = 5
    mean_CT2assessOPD = 60
    mean_CT2assessER = 30

    # Information gathering
    arrival_ts = []         # Entity arrival times in a single run
    queued = {}             # Queueing times in a single run, step-wise (Use type of resource as key to extract data for that step)
    delta = {}              # Processing times in a single run, step-wise (Use type of resource as key to extract data for that step)

    # Resource Monitoring
    utilization_event = {}  # Data from monkey-patched resource, single run
    utilization_poll = {}   # Data from generator for polling resource stats, single run

class Patient:
    """
    An entity and attributes
    """
    def __init__(self, patient_ID) -> None:
        self.ID = patient_ID

class Process:
    """
    Process model including logic and resources
    """
    def __init__(self) -> None:
        self.env = simpy.Environment()
        self.patient_counter = 0
        self.resources = {}
        for resource_type in G.resource_types:
            self.resources[resource_type] = simpy.Resource(self.env, G.resource_capacity.get(resource_type))

    def monitor_capacity(self):
        for resource_type in self.resources.keys():
            G.utilization_event[resource_type] = []
            mon_callback = get_monitor(G.utilization_event[resource_type])
            patch_resource(self.resources[resource_type], post=mon_callback)
    
    def entity_generator(self):
        G.arrival_ts.clear()
        for resource_type in G.resource_types:
            G.queued[resource_type] = []
            G.delta[resource_type] = []
        G.delta["TAT"] = []  # Accounting for Turn-Around Time (TAT) per entity for end-end process
        while True:
            self.patient_counter += 1
            patient = Patient(self.patient_counter)

            # Send patient onward 
            action = self.activity_generator(patient)
            self.env.process(action)

            # Wait for next arrival
            delta4arrival = random.expovariate(1.0 / G.mean_IAT)
            yield self.env.timeout(delta4arrival)

    def activity_generator(self, patient):      
        arrived = self.env.now
        G.arrival_ts.append(arrived)
        print("{} arrived at {:.2f} [IAT {}]".format(patient.ID, arrived, G.mean_IAT)) if G.verbose else None

        # Request a receptionist for registration
        with self.resources["receptionist"].request() as req_receptionist:
            # Wait until receptionist is available
            yield req_receptionist

            startedRegistration = self.env.now
            help_monitor('receptionist', startedRegistration)
            G.queued["receptionist"].append(startedRegistration - arrived)
            print("{} started registration at {:.2f} after waiting {:.2f} [#Receptionists {}]".format(patient.ID, startedRegistration, startedRegistration - arrived, G.resource_capacity["receptionist"])) if G.verbose else None
            
            deltaRegistration = random.expovariate(1.0 / G.mean_CT2register)
            G.delta["receptionist"].append(deltaRegistration)
            yield self.env.timeout(deltaRegistration)

        arrived4triage = self.env.now

        with self.resources["nurse"].request() as req_nurse:
            # Wait until nurse is available
            yield req_nurse
            
            startedTriage = self.env.now
            help_monitor('nurse', startedTriage)
            G.queued["nurse"].append(startedTriage - arrived4triage)
            print("{} started triage at {:.2f} after waiting {:.2f} [#Nurses {}]".format(patient.ID, startedTriage, startedTriage - arrived4triage, G.resource_capacity["nurse"])) if G.verbose else None

            deltaTriage = random.expovariate(1.0 / G.mean_CT2triage)
            G.delta["nurse"].append(deltaTriage)
            yield self.env.timeout(deltaTriage)

        arrived4assessment = self.env.now

        which_way = random.uniform(0, 1)

        if (which_way < 0.2):
            with self.resources["doctorOPD"].request() as req_doctorOPD:
                # Wait until doctor is available in outpatient care
                yield req_doctorOPD

                startedAssessmentOPD = self.env.now
                help_monitor('doctorOPD', startedAssessmentOPD)
                G.queued["doctorOPD"].append(startedAssessmentOPD - arrived4assessment)
                print("{} started assessment in outpatient care at {:.2f} after waiting {:.2f} [#Doctors OPD {}]".format(patient.ID, startedAssessmentOPD, startedAssessmentOPD - arrived4assessment, G.resource_capacity["doctorOPD"])) if G.verbose else None          

                deltaAssessmentOPD = random.expovariate(1.0 / G.mean_CT2assessOPD)
                G.delta["doctorOPD"].append(deltaAssessmentOPD)
                yield self.env.timeout(deltaAssessmentOPD)
        else:
            with self.resources["doctorER"].request() as req_doctorER:
            # Wait until doctor is available for inpatient care
                yield req_doctorER

                startedAssessmentER = self.env.now
                help_monitor('doctorER', startedAssessmentER)
                G.queued["doctorER"].append(startedAssessmentER - arrived4assessment)
                print("{} started asessment in inpatient care at {:.2f} after waiting {:.2f} [#Doctors ER {}]".format(patient.ID, startedAssessmentER, startedAssessmentER - arrived4assessment, G.resource_capacity["doctorER"])) if G.verbose else None
                
                deltaAssessmentER = random.expovariate(1.0 / G.mean_CT2assessER)
                G.delta["doctorER"].append(deltaAssessmentER)
                yield self.env.timeout(deltaAssessmentER)

                exited = self.env.now    
                G.delta["TAT"].append(exited - arrived)
                print("{} HAD LEAD TIME OF {:.0f} MINUTES.".format(patient.ID,  exited - arrived)) if G.verbose else None

    def run_once(self, proc_monitor=False):
        run_result = {
            "Queued": {},
            "Delta": {},
            "Utilization": {}
        }

        # Make it so
        G_resource = G.utilization_event        
        self.env.process(self.entity_generator())
        if proc_monitor:
            G_resource = G.utilization_poll
            self.env.process(self.poll_capacity())
        self.env.run(until=G.simulation_horizon)

        for resource_type in G.resource_types:
            run_result["Queued"][resource_type] = median(G.queued[resource_type]) 
            run_result["Delta"][resource_type] = median(G.delta[resource_type])
            x, y, _ = list(zip(*G_resource[resource_type]))
            Nr = trapz(y, x)
            Dr = G.resource_capacity[resource_type] * x[-1]
            run_result["Utilization"][resource_type] = Nr / Dr
        run_result["Delta"]["TAT"] = median(G.delta["TAT"])
        
        return run_result
   
    def poll_capacity(self):
        """
        Generator for monitoring process that shares the environment with the main process
        and collects information.
        """
        for resource_type in self.resources.keys():
            G.utilization_poll[resource_type] = []
        while True:
            for k, v in self.resources.items():
                item = (self.env.now,
                        v.count,
                        len(v.queue))
                G.utilization_poll.get(k).append(item)
            yield self.env.timeout(0.25)    



