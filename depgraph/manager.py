import multiprocessing
import queue
import sys
import time
import threading

from concurrent.futures import ThreadPoolExecutor, wait

from . import MISSING, PARENTNEWER

def supervisor(target, steps, signals, sleep=0.1):
    submitted = {}

    while True:

        try:
            msg = signals.get_nowait()
            if msg == "quit":
                break
        except queue.Empty:
            pass

        steps_outstanding = 0
        new_steps_submitted = 0
        for dep, reason in target.buildnext():
            steps_outstanding += 1
            if dep not in submitted:
                steps.put((dep, reason))
                submitted[dep] = True
                new_steps_submitted += 1

        if steps_outstanding == 0:
            break

        if new_steps_submitted == 0:
            time.sleep(sleep)

    if not target.exists:
        steps.put((target, MISSING))

    elif any(target.is_older_than(p) for p in target.parents(0)):
        steps.put((target, PARENTNEWER))

    steps.put((None, None)) # signal completion
    return

def worker(fn, target, reason, ehandler, max_attempts=1):
    success = False
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        try:
            success = fn(target, reason)
        except Exception as e:
            ehandler(e)
    return success


def raise_exc(e):
    raise e

def execute(delegator):
    """ Decorator to be used for constructing build managers.

    Wraps
    -----
    A delegator function (f(target, reason)) that given a build target and a
    reason, attempts to build the target

    Returns
    -------
    A function that takes a target Dataset and repeatedly calls the delegator
    with the correct sequence of intermediate Datasets to develop the target.

    Additional keyword arguments of the returned function are *max_attempts*,
    which is an integer indicating how many times a Dataset should be
    attempted, and a string *onfailure* that may be one of ("raise", "print",
    "ignore"), indicating how to handle exceptions during the build.

    Example
    -------
    ::
        @buildmanager(max_attempts=3, onfailure='print')
        def run_build(dependency, reason):
            # performs actions to build *dependency*
            # ...
            return exitcode

        # Calling `run_build` now enters a loop that builds all dependencies
        run_build(target, max_attempts=1)
    """

    def manager(target, max_attempts=1, onfailure="raise", nprocs=None):
        """ Perform action to build a target.

        Parameters
        ----------
        target : Dataset
            terminal dataset to build
        max_attempts : int, optional
            maximum number of times a dependency build should be attempted
        onfailure : str
            if "raise" then propagate failures
            if "print" then print traceback and continue
            if "ignore" then continue silently
        nprocs : int
            number of worker processes to use
        supervisor_sleep : int
            milliseconds that the supervisor should wait before recomputing
            dependencies. Increasing this on large graphs can mean fewer
            cycles wasted on planning.
        """

        if onfailure == 'raise':
            ehandler = raise_exc
        elif onfailure == "print":
            ehandler = lambda e: sys.stderr.write("{}\n".format(e))
        elif onfailure == "ignore":
            ehandler = lambda e: None
        else:
            raise ValueError("invalid value for onfailure: '{}'"
                             .format(onfailure))

        signals = queue.Queue()
        steps = queue.Queue()
        if nprocs is None:
            nprocs = multiprocessing.cpu_count()

        th_supervisor = threading.Thread(None, supervisor, args=(target, steps, signals))
        th_supervisor.start()

        pending = []
        with ThreadPoolExecutor(max_workers=2) as executor:

            while True:

                # handle outstanding futures:
                donemap = [fut.done() for fut in pending]
                completed = [fut for (fut, done) in zip(pending, donemap) if done]
                pending = [fut for (fut, done) in zip(pending, donemap) if not done]

                if False in (fut.result() for fut in completed):
                    break


                if len(pending) > 5*nprocs:
                    # backpressure on submissions
                    time.sleep(1.0)

                else:
                    try:
                        dep, reason = steps.get(True, 0.1)
                        if dep is None:
                            # supervisor says job finished
                            break

                        fut = executor.submit(worker, delegator, dep, reason,
                                              ehandler,
                                              max_attempts=max_attempts)
                        pending.append(fut)
                    except queue.Empty:
                        pass

            wait(pending)

        signals.put("quit")
        th_supervisor.join()

        return
    return manager
