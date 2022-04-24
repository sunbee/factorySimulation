import simpy
import random
from numpy import median
import warnings

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
        with self.receptionist.request() as req:
            # Wait until receptionist is available
            yield req

            startedRegistration = self.env.now
            queuedRegistration = startedRegistration - arrived
            G.queued4registration.append(queuedRegistration)
            print("{} started registration at {:.2f} after waiting {:.2f} [#Receptionists {}]".format(patient.ID, startedRegistration, queuedRegistration, G.number_of_receptionists))
            
            deltaRegistration = random.expovariate(1.0 / G.mean_CT2register)
            yield self.env.timeout(deltaRegistration)

        arrived4triage = self.env.now

        with self.nurse.request() as req:
            # Wait until nurse is available
            yield req
            
            startedTriage = self.env.now
            queuedTriage = startedTriage - arrived4triage
            G.queued4triage.append(queuedTriage)
            print("{} started triage at {:.2f} after waiting {:.2f} [#Nurses {}]".format(patient.ID, startedTriage, queuedTriage, G.number_of_nurses))

            deltaTriage = random.expovariate(1.0 / G.mean_CT2triage)
            yield self.env.timeout(deltaTriage)

        arrived4assessment = self.env.now

        which_way = random.uniform(0, 1)

        if (which_way < 0.2):
            with self.doctorOPD.request() as req:
                # Wait until doctor is available in outpatient care
                yield req

                startedAssessmentOPD = self.env.now
                queuedAssessmentOPD = startedAssessmentOPD - arrived4assessment
                G.queued4assessmentOPD.append(queuedAssessmentOPD)
                print("{} started assessment in outpatient care at {:.2f} after waiting {:.2f} [#Doctors OPD {}]".format(patient.ID, startedAssessmentOPD, queuedAssessmentOPD, G.number_of_doctorsOPD))            

                deltaAssessmentOPD = random.expovariate(1.0 / G.mean_CT2assessOPD)
                yield self.env.timeout(deltaAssessmentOPD)
        else:
            with self.doctorER.request() as req:
            # Wait until doctor is available for inpatient care
                yield req

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

    def run_once(self):
        run_result = {
                "TAT": None,
                "Queued4Registration": None,
                "Queued4Triage": None,
                "Queued4AssessmentOPD": None,
                "Queued4AssessmentER": None
        }

        # Make it so
        self.env.process(self.entity_generator())
        self.env.run(until=G.simulation_horizon)

        run_result["TAT"] = sum(G.leadTimes) / len(G.leadTimes)
        run_result["Queued4Registration"] = sum(G.queued4registration) / len(G.queued4registration)
        run_result["Queued4Triage"] = sum(G.queued4triage) / len(G.queued4triage)
        run_result["Queued4AssessmentOPD"] = sum(G.queued4assessmentOPD) / len(G.queued4assessmentOPD)
        run_result["Queued4AssessmentER"] = sum(G.queued4assessmentER) / len(G.queued4assessmentER)

        return run_result



