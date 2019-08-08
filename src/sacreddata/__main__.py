import argparse
import os

from . import filereporter


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("directory")

    args = ap.parse_args()
    print(args)
    print(args.directory)
    sacristan = filereporter.FileReporter(args.directory)
    print(sacristan)

    import numpy as np
    import sacreddata.gym_recording_playback
    import matplotlib.pyplot as plt
    # fr = sacristan['11']
    # all_traces = sacreddata.gym_recording_playback.AllTraces()
    # sacreddata.gym_recording_playback.scan_recorded_traces(fr, all_traces.add_trace)
    print("loaded into 'sacristan'")
    import sys
    sys.argv = sys.argv[:1]
    import IPython;
    IPython.start_ipython(user_ns=dict(sacristan=sacristan))

