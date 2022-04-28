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

    # Resourcing
    number_of_receptionists = 1
    number_of_nurses = 2
    number_of_doctorsOPD = 1
    number_of_doctorsER = 2

    # Model paramters
    mean_IAT = 8
    mean_CT2register = 2
    mean_CT2triage = 5
    mean_CT2assessOPD = 60
    mean_CT2assessER = 30

    # Information gathering
    arrived4process = []
    queued4registration = []    
    delta4registration = []
    queued4triage = []
    delta4triage = []
    queued4assessmentOPD = []
    delta4assessmentOPD = []
    queued4assessmentER = []
    delta4assessmentER = []
    leadTimes = []

    # Monitoring
    resource_monitor = {}       # Data from monkey-patched resource 
    resource_utilization = {}   # Data from generator for monitoring process

    def clear_accumulators():
        G.arrived4process.clear()
        G.queued4registration.clear()    
        G.delta4registration.clear()
        G.queued4triage.clear()
        G.delta4triage.clear()
        G.queued4assessmentOPD.clear()
        G.delta4assessmentOPD.clear()
        G.queued4assessmentER.clear()
        G.delta4assessmentER.clear()
        G.leadTimes.clear()

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
        self.receptionist = simpy.Resource(self.env, capacity=G.number_of_receptionists)
        self.nurse = simpy.Resource(self.env, capacity=G.number_of_nurses)
        self.doctorOPD = simpy.Resource(self.env, capacity=G.number_of_doctorsOPD)
        self.doctorER = simpy.Resource(self.env, capacity=G.number_of_doctorsER)

    def monitor_resource(self, resource_names):
        for name in resource_names:
            if hasattr(self, name):
                G.resource_monitor[name] = []
                mon_callback = get_monitor(G.resource_monitor[name])
                patch_resource(getattr(self, name), post=mon_callback)
        
    def entity_generator(self):
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
        G.arrived4process.append(arrived)
        print("{} arrived at {:.2f} [IAT {}]".format(patient.ID, arrived, G.mean_IAT))

        # Request a receptionist for registration
        with self.receptionist.request() as req_receptionist:
            # Wait until receptionist is available
            yield req_receptionist

            startedRegistration = self.env.now
            queuedRegistration = startedRegistration - arrived
            G.queued4registration.append(queuedRegistration)
            print("{} started registration at {:.2f} after waiting {:.2f} [#Receptionists {}]".format(patient.ID, startedRegistration, queuedRegistration, G.number_of_receptionists))
            
            deltaRegistration = random.expovariate(1.0 / G.mean_CT2register)
            yield self.env.timeout(deltaRegistration)

        arrived4triage = self.env.now

        with self.nurse.request() as req_nurse:
            # Wait until nurse is available
            yield req_nurse
            
            startedTriage = self.env.now
            queuedTriage = startedTriage - arrived4triage
            G.queued4triage.append(queuedTriage)
            print("{} started triage at {:.2f} after waiting {:.2f} [#Nurses {}]".format(patient.ID, startedTriage, queuedTriage, G.number_of_nurses))

            deltaTriage = random.expovariate(1.0 / G.mean_CT2triage)
            yield self.env.timeout(deltaTriage)

        arrived4assessment = self.env.now

        which_way = random.uniform(0, 1)

        if (which_way < 0.2):
            with self.doctorOPD.request() as req_doctorOPD:
                # Wait until doctor is available in outpatient care
                yield req_doctorOPD

                startedAssessmentOPD = self.env.now
                queuedAssessmentOPD = startedAssessmentOPD - arrived4assessment
                G.queued4assessmentOPD.append(queuedAssessmentOPD)
                print("{} started assessment in outpatient care at {:.2f} after waiting {:.2f} [#Doctors OPD {}]".format(patient.ID, startedAssessmentOPD, queuedAssessmentOPD, G.number_of_doctorsOPD))            

                deltaAssessmentOPD = random.expovariate(1.0 / G.mean_CT2assessOPD)
                yield self.env.timeout(deltaAssessmentOPD)
        else:
            with self.doctorER.request() as req_doctorER:
            # Wait until doctor is available for inpatient care
                yield req_doctorER

                startedAssessmentER = self.env.now
                queuedAssessmentER = startedAssessmentER - arrived4assessment
                G.queued4assessmentER.append(queuedAssessmentER)
                print("{} started asessment in inpatient care at {:.2f} after waiting {:.2f} [#Doctors ER {}]".format(patient.ID, startedAssessmentER, queuedAssessmentER, G.number_of_doctorsER))
                
                deltaAssessmentER = random.expovariate(1.0 / G.mean_CT2assessER)
                yield self.env.timeout(deltaAssessmentER)

                exited = self.env.now    
                TAT = exited - arrived
                G.leadTimes.append(TAT)
                print("{} HAD LEAD TIME OF {:.0f} MINUTES.".format(patient.ID, TAT))

    def run_once(self, proc_monitor=False):
        # G's class-level attributes of type array will need to be reinitialized to clear history
        G.clear_accumulators()

        run_result = {
            "TAT": None,
            "Queued4Registration": None,
            "Queued4Triage": None,
            "Queued4AssessmentOPD": None,
            "Queued4AssessmentER": None
        }

        # Make it so
        self.env.process(self.entity_generator())
        if proc_monitor:
            self.env.process(self.monitor_process(['receptionist', 'nurse', 'doctorOPD', 'doctorER']))
        self.env.run(until=G.simulation_horizon)

        run_result["TAT"] = sum(G.leadTimes) / len(G.leadTimes)
        run_result["Queued4Registration"] = sum(G.queued4registration) / len(G.queued4registration)
        run_result["Queued4Triage"] = sum(G.queued4triage) / len(G.queued4triage)
        run_result["Queued4AssessmentOPD"] = sum(G.queued4assessmentOPD) / len(G.queued4assessmentOPD)
        run_result["Queued4AssessmentER"] = sum(G.queued4assessmentER) / len(G.queued4assessmentER)

        return run_result
   
    def monitor_process(self, resource_names):
        """
        Generator for monitoring process that shares the environment with the main process
        and collects information.
        """
        resources = []
        for name in resource_names:
            if hasattr(self, name) and isinstance(getattr(self, name), simpy.resources.resource.Resource):
                G.resource_utilization[name] = []
                resources.append((name, getattr(self, name)))
        while True:
            for rname, r in resources:
                item = (self.env.now,
                        r.count,
                        len(r.queue))
                G.resource_utilization.get(rname).append(item)
            yield self.env.timeout(0.25)    



