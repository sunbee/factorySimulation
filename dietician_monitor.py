import resource
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

    # Decorate original get/put or request/release methods
    for name in ['get', 'put', 'request', 'release']:
        if hasattr(resource, name):
            setattr(resource, name, get_wrapper(getattr(resource, name)))    

def get_monitor(data):
    """
    Query the attributes of the target resource with this callback.
    Passed to patch_resource as argument pre= or post=, depending on
    whether to execute the callback before or after the resource's
    get/put or request/release method calls.
    """
    def monitor(resource):
        data.append((
            resource._env.now,      # simulation timestamp
            resource.count,         # number of consumers
            len(resource.queue)     # number of queued processes 
        ))
    return monitor

def help_monitor(resource_name, ts):
    """
    Fix the gap with monkey-patching missing to record capacity allocated
    to an entity that is served after a delay. This happens when an entity
    is waiting in queue while another entity is being processed. 
    Modifies the list that where data are logged from the monkey-patched 
    resource. Call this function right after capacity is allocated,
    i.e. right after 'yield req'. Compares the timestamp of capacity allocation 
    with the timestamp of the most recent element on the list and if same, 
    pops the item and puts it back after modification. 
    """
    if (resource_name in G.resource_monitor) \
        and (G.resource_monitor.get(resource_name)[-1][0] == ts) \
        and (G.resource_monitor.get(resource_name)[-1][-1] > 0):
        item = list(G.resource_monitor.get(resource_name).pop(-1))
        item[1] += 1; item[2] -= 1 
        G.resource_monitor.get(resource_name).append(tuple(item))

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
    lead = []

    # Monitoring
    resource_utilization = {}  # Data from genertor for process monitoring 
    resource_monitor = {}      # Data from monkey-patching some of a resource's methods 

    def clear_accumulators():
        G.arrived.clear()
        G.queued.clear()
        G.lead.clear()

class Patient:
    """
    An entity and attributes
    """
    def __init__(self, patient_ID) -> None:
        self.ID = patient_ID

class Consultation:
    def __init__(self) -> None:
        self.env = simpy.Environment()
        self.dietician = simpy.PreemptiveResource(self.env, 1)
        self.patient_counter = 0

    def monitor_resource(self):
        """
        USE THE MONKEY-PATCHED RESOURCE FOR MONITORING RESOURCE UTILIZATION
        Gets the callback with 'get_monitor()' 
        and executes monkey-patching resource with 'patch_resource()`
        """
        resource_names=['dietician']
        for name in resource_names:
            if hasattr(self, name):
                G.resource_monitor[name] = []
                mon_callback = get_monitor(G.resource_monitor[name])
                patch_resource(getattr(self, name), post=mon_callback)

    def generate_patient(self):
        # run indefintely
        while(True):
            # Generate next arrival
            self.patient_counter += 1
            patient = Patient(self.patient_counter)

            # Send an arrival onward
            Consultation = self.generate_consultation(patient)
            self.env.process(Consultation) 

            # Await new arrival
            deltaIAT = random.expovariate(1.0 / G.mean_IAT)
            yield self.env.timeout(deltaIAT)

    def generate_consultation(self, patient):
        arrived_at = self.env.now
        G.arrived.append(arrived_at)
        print("Patient {} entered the queue at {:.2f}".format(patient.ID, arrived_at))

        with self.dietician.request() as req:
            # Wait until the dietician is available
            yield req

            started_at = self.env.now
            help_monitor('dietician', started_at)
            queued_for = started_at - arrived_at
            G.queued.append(queued_for)
            print("Patient {} entered consultation at {:.2f}, having waited {:.2f}".format(patient.ID, started_at, queued_for))

            delta = random.expovariate(1.0 / G.mean_CT)
            yield self.env.timeout(delta)

            exited_at = self.env.now
            TAT = exited_at - arrived_at
            G.lead.append(TAT)
            print("Patient {} exited at {:.2f}, having spent {:.2f} in clinic.".format(patient.ID, exited_at, TAT))
            
    def run_once(self, proc_monitor=False):
        G.clear_accumulators() # Clear history

        run_averages = {
            "queued": None,
            "lead": None,
            "utilization": None
        }
        
        self.env.process(self.generate_patient())
        if proc_monitor:
            self.env.process(self.monitor_process(['dietician']))
        self.env.run(until=G.simulation_horizon)

        run_averages["queued"] = sum(G.queued) / len(G.queued) if len(G.queued) > 0 else None
        run_averages["lead"] = sum(G.lead) / len(G.lead) if len(G.lead) > 0 else None
        G_resource = G.resource_monitor
        if proc_monitor:
            G_resource = G.resource_utilization  
        x_r, y_r, _ = list(zip(*G_resource['dietician']))    
        run_averages["utilization"] = trapz(y_r, x_r) / (G.number_of_dieticians * x_r[-1])

        return run_averages

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

class Break4Lunch:
    """
    Usage: Create an instance after setting up the clinic for simulation,
    then run in the same environment as the clinic.
    """
    def __init__(self, env, worker, break_hour) -> None:
        self.env = env
        self.worker = worker            # Must be a resource of pre-emptive  type
        self.break_hour = break_hour    # Start of break of fixed duration 
                                        # in no. of simulation steps from start of shift
        self.length_of_shift = 480      # 8 hours x 60 min

    def generate_lunch(self):
        """
        Assume:
        - Simulation step size is 1 minute
        - 480 minutes in one shift
        - One shift ends and another starts
        - Break time will repeat once every shift 
        - Break time is 60 minutes
        """
        herenow = self.env.now
        until_lunch = self.break_hour - herenow  # How long till we break for lunch?
        while True:
            if until_lunch > 0:
                yield self.env.timeout()        # Keep going until lunch break
            print("Gone to lunch at {:.2f}, break hour is {:.2f}.".format(self.here.now, self.break_hour))
            with self.worker.request(priority=-99) as req:  # Break for lunch
                yield 60                        # Gobble-gobble
            print("Back from lunch at {:.2f} and open for business.".format(self.env.now))
            self.break_hour += self.length_of_shift 
            until_lunch = self.break_hour - self.env.now

    def do_lunch(self):
        self.env.process(self.generate_lunch())
        self.env.run(until=G.simulation_horizon)



