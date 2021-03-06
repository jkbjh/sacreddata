from gym_recording import playback
import tempfile
import os
import itertools
import numpy as np


def scan_recorded_traces(run, callback, tmp_directory=None):
    if tmp_directory is None:
        tmp_directory = tempfile.mkdtemp(prefix="sacristan_tmp")
    trace_artifacts = [x for x in run.artifacts if x.startswith("openaigym.trace")]
    tmp_files = run.extract_artifacts(tmp_directory, trace_artifacts)
    playback.scan_recorded_traces(tmp_directory, callback)
    for f in tmp_files:
        os.remove(f)


class AllTraces(object):
    @classmethod
    def all_traces_from_run(cls, run):
        all_traces = AllTraces()
        scan_recorded_traces(run, all_traces.add_trace)

    def __init__(self):
        self.i = 0
        self._observations = []
        self._actions = []
        self._rewards = []
        self.rewards = None
        self.observations = None
        self.observations1 = None
        self.returns = None
        self.episode_lengths = None
        self.actions = None
        self.last_incomplete = None

    def stack(self):
        """vstack the data (potentially excluding the last episode if it is incomplete)"""
        if (len(self._observations) >= 1) and (self._observations[-1].shape != self._observations[-2].shape):
            self.last_incomplete = True
        else:
            self.last_incomplete = False

        stacker = lambda data: np.concatenate(data, axis=0)
        self.observations = stacker([o[:-1] for o in self._observations])
        self.actions = stacker(self._actions)
        self.rewards = stacker(self._rewards)
        self.observations1 = stacker([o[1:] for o in self._observations])
        self.returns = np.array([np.sum(x) for x in self._rewards])
        self.episode_lengths = np.array([len(x) for x in self._rewards])

    def add_trace(self, observations, actions, rewards):
        observations, actions, rewards = map(np.array, (observations, actions, rewards))
        if not (rewards.size and actions.size and observations.size):
            return
        self._observations.append(observations)
        self._actions.append(actions)
        self._rewards.append(rewards)
        self.i += 1
