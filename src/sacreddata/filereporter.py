import os
import json
import dictor
import datetime
import io
import shutil


def _slurp_json(filename):
    with open(filename) as fp:
        return json.loads(fp.read())


class lazy_property(object):
    def __init__(self, func):
        self._func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __get__(self, obj, klass=None):
        if obj is None:
            return None
        result = obj.__dict__[self.__name__] = self._func(obj)
        return result


class JSONObj(object):
    @classmethod
    def slurp(cls, filename):
        return cls(_slurp_json(filename))

    def __init__(self, json_data):
        self._json = json_data

    def __getitem__(self, value_path):
        return dictor.dictor(self._json, value_path)

    @property
    def raw(self):
        return self._json

    def keys(self):
        return self._json.keys()

    def __repr__(self):
        return "%s %r>" % (super(JSONObj, self).__repr__()[:-1],
                           self.keys())


class FileRun(object):
    def __init__(self, base_directory, run_directory, run_json):
        self._base_directory = base_directory
        self._run_directory = run_directory
        self._run_json = run_json
        self._artifacts = set(self["artifacts"])

    @lazy_property
    def config(self):
        return JSONObj.slurp(os.path.join(self._run_directory, "config.json"))

    @lazy_property
    def metrics(self):
        return JSONObj.slurp(os.path.join(self._run_directory, "metrics.json"))

    def __getitem__(self, value_path):
        return dictor.dictor(self._run_json, value_path)

    def keys(self):
        return self._run_json.keys()

    def info(self):
        str_format = "%Y-%m-%dT%H:%M:%S.%f"
        start_time = datetime.datetime.strptime(self["start_time"], str_format)
        stop_time = datetime.datetime.strptime(self['stop_time'], str_format)
        return dict(
            run_directory=self._run_directory,
            name=self["experiment.name"],
            start_time=start_time,
            duration=stop_time - start_time)

    @property
    def artifacts(self):
        return self._artifacts

    def __artifact_path(self, artifact):
        return os.path.join(self._run_directory, artifact)

    def open(self, artifact, *a):
        assert artifact in self._artifacts
        return io.open(self.__artifact_path(artifact), *a)

    def __repr__(self):
        return "%s info=%r>" % (
            super(FileRun, self).__repr__()[:-1],
            self.info()
        )

    def extract_artifacts(self, output_path, artifacts, create_output_path=True):
        unknown_artifacts = set(artifacts) - self.artifacts
        if unknown_artifacts:
            raise RuntimeError("Unknown artifacts requested: %r" % (sorted(list(unknown_artifacts))))
        if not os.path.exists(output_path) and create_output_path:
            os.makedirs(output_path)
        targets = []
        for artifact in artifacts:
            target_path = os.path.join(output_path, artifact)
            shutil.copyfile(self.__artifact_path(artifact), target_path)
            targets.append(target_path)
        return targets


class FileReporter(object):
    def __init__(self, directory):
        self.base_directory = directory
        self.sources_directory = os.path.join(self.base_directory, "_sources")
        if not os.path.exists(self.sources_directory):
            raise RuntimeError(("_sources directory not found, probably "
                                "not a sacred %r results directory!") %
                               (self.base_directory,))

        self._runs = [run for run in os.listdir(self.base_directory) if run.isdigit()]
        self._runs.sort(key=lambda x: int(x))
        self._run_json = {}
        for run in self._runs:
            self._run_json[run] = _slurp_json(os.path.join(self.base_directory, run, "run.json"))

    def __getitem__(self, run_key):
        return FileRun(self.base_directory, os.path.join(self.base_directory, run_key), self._run_json[run_key])

    def keys(self):
        return self._runs
