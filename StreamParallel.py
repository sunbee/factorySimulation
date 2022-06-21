import imp
from joblib import Parallel, delayed
from triage_model import G, Process, Patient
import time

def simsome(poll=False):
    G.verbose = False
    p = Process()
    return p.run_once(proc_monitor=poll)

def test_rig(n=19):
    tic = time.time()
    outres = Parallel(n_jobs=-1)(delayed(simsome)(poll=True) for i in range(n))
    toc = time.time()
    print("Took about {:.2f} secs for {} simulation runs".format(toc-tic, n))
    return outres

out19 = test_rig(19)
out199 = test_rig(199)
out1999 = test_rig(1999)
out19999 = test_rig(19999)

print(out19[0])

#name_of_resource = 'receptionist'
#name_of_resource = 'nurse'
name_of_resource = 'doctorOPD'
#name_of_resource = 'doctorER'

#name_of_metric = 'Queued'
#name_of_metric = 'Delta'
name_of_metric = 'Utilization'

docOPD_u = [out.get(name_of_metric).get(name_of_resource) for out in out19999]
docOPD_ua = sum(docOPD_u)/len(docOPD_u)
print("Got {} of {} as {:.2f}".format(name_of_metric, name_of_resource, docOPD_ua))