import resource
import simpy
import random
from numpy import median, trapz, asarray
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
    Usage: Call after 'yield' statement following request for resource
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
    resource_utilization = {}   # Data from generator for process monitoring (polled)
    resource_monitor = {}       # Data from monkey-patching some of a resource's methods (event-driven)

    def clear_accumulators():   # Call in method 'run_once()' of class 'Consultation'
        G.arrived.clear()
        G.queued.clear()
        G.lead.clear()

class Patient:
    """
    An entity and attributes
    """
    def __init__(self, patient_ID) -> None:
        self.ID = patient_ID
        self.priority = 3

class Consultation:
    def __init__(self, shift_length=None) -> None:
        self.env = simpy.Environment()
        self.dietician = simpy.PriorityResource(self.env, G.number_of_dieticians)
        self.patient_counter = 0
        self.shift_length = shift_length
        self.break4shift = False
        self.resume_shift = self.env.event()
        
    def monitor_resource(self):
        """
        USE THE MONKEY-PATCHED RESOURCE FOR MONITORING RESOURCE UTILIZATION
        Gets the callback with 'get_monitor()' 
        and executes monkey-patching resource with 'patch_resource()`
        Usage: Call in method 'run_once()' of this class
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

            if self.shift_length and self.break4shift:
                print("Shift over, tools down at {:.2f}".format(self.env.now))
                yield self.env.timeout(self.shift_length)
                print("Resuming new shift at {:.2f}".format(self.env.now))
                self.break4shift = False
                self.resume_shift.succeed()
                self.resume_shift = self.env.event()

    def generate_consultation(self, patient):
        arrived_at = self.env.now
        G.arrived.append(arrived_at)
        print("Patient {} entered the queue at {:.2f}".format(patient.ID, arrived_at))

        delta = random.expovariate(1.0 / G.mean_CT)
        while delta > 0:
            with self.dietician.request(priority=patient.priority) as req:
                # Wait until the dietician is available
                yield req

                started_at = self.env.now
                help_monitor('dietician', started_at)
                queued_for = started_at - arrived_at
                G.queued.append(queued_for)
                print("Patient {} entered consultation at {:.2f}, having waited {:.2f}".format(patient.ID, started_at, queued_for))

                #delta = random.expovariate(1.0 / G.mean_CT)
                try:
                    yield self.env.timeout(delta)
                    delta = 0
                except simpy.Interrupt as interrupt:
                    by = interrupt.cause.by
                    usage = self.env.now - interrupt.cause.usage_since
                    delta -= usage
                    patient.priority -= 0.1  # Bump up priority to treat interrupted patient upon resumption
                    print("{} got pre-empted by {} after {}".format(patient.ID, by, usage))

        exited_at = self.env.now
        TAT = exited_at - arrived_at
        G.lead.append(TAT)
        print("Patient {} exited at {:.2f}, having spent {:.2f} in clinic.".format(patient.ID, exited_at, TAT))
                
    def run_once(self, proc_monitor=False):
        G.clear_accumulators()  # Clear history
        self.monitor_resource() # Monkey-patch the dietician
        run_averages = {        # Template to gather CTQs from single run
            "queued": None,
            "lead": None,
            "utilization": None
        }
        
        self.env.process(self.generate_patient())
        if proc_monitor:
            self.env.process(self.monitor_process(['dietician']))
        if self.shift_length:
            self.shift_process = self.env.process(self.go_home_now())          
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
        Usage: Call in method `run_once()` of this class, checking if method's arg. 'proc_monitor' is True
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

    def go_home_now(self):
        while True:
            yield self.env.timeout(self.shift_length)
            print("Stopping shift at {:.2f}".format(self.env.now))
            self.break4shift = True
            yield self.resume_shift
            print("Resumed shift at {:.2f}".format(self.env.now))

class Break4Lunch:
    """
    Usage: Create an instance after setting up the clinic for simulation.
    Note:
    The constructor does the work. Rubber hits the road in method 'run_once()' of class Consultation
    where the simulation is run.
    """
    def __init__(self, env, worker, break_at, break_interval=20) -> None:
        self.env = env
        self.worker = worker                    # Must be a resource of pre-emptive  type
        self.break_at = break_at                # Start of break of fixed duration 
                                                # in no. of simulation steps from start of shift
        self.break_interval = break_interval    # Duration of break
        
        [self.env.process(self.generate_lunch()) for i in range(G.number_of_dieticians)]

    def generate_lunch(self):
        """
        Usage: Call in the constructor of this class for as many times as the resource capacity.
        Note:
        Only one break at a time can be scheduled this way. That means, one simpy process
        per simpy resource per break. May seem wasteful, but follows from the fact that 
        a simpy resource is an undifferentiated bulk.
        """
        herenow = self.env.now
        until_lunch = self.break_at - herenow  # How long till we break for lunch?
        if until_lunch > 0:
            yield self.env.timeout(until_lunch)             # Keep going until lunch break
        with self.worker.request(priority=1) as req:        # Break for lunch
            yield req
            print("Gone to lunch at {:.2f}, break hour is {:.2f}.".format(self.env.now, self.break_at))
            yield self.env.timeout(self.break_interval)     # Gobble-gobble
            print("Back from lunch at {:.2f} and open for business.".format(self.env.now))

class Break2Schedule:
    """
    Usage: Create an instance after setting up the clinic for simulation.
    Note:
    Constructor does the work. Rubber hits the road in method 'run_once()' of class Consultation
    where the simulation is run.
    """
    def __init__(self, env, worker, scheduled_breaks) -> None:
        self.env = env
        self.worker = worker
        self.scheduled_breaks = scheduled_breaks

        self.generate_breaks()
    
    def break_generator(self, break_start, break_interval):
        print(f"{break_start} : {break_interval}")
        until_break = break_start - self.env.now
        if until_break > 0:
            yield self.env.timeout(until_break)
        with self.worker.request(priority=1) as req:
            yield req
            print("Gone on break at {:.2f} for scheduled break at {:.2f}".format(self.env.now, break_start))
            yield self.env.timeout(break_interval)
            print("Break ended, back in business at {:.2f}.".format(self.env.now))

    def generate_breaks(self):
        for this_break in self.scheduled_breaks:  # Handle one break in one iteration of for loop
            break_start, break_interval = this_break
            # Give each dietician this break! 
            [self.env.process(self.break_generator(break_start, break_interval)) for i in range(G.number_of_dieticians)]


