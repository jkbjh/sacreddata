import os
try:
    import ujson as json
except ImportError:
    import json
import dictor
import datetime
import io
import shutil
import pandas as pd
import warnings


class BuildCommandMixin(object):
    def build_command(self):
        vals = dict(self.run["experiment"])
        vals.update(self.run["meta"])
        vals = {k: v for k, v in vals.items() if v}
        vals["options"] = {k: v for k, v in vals["options"].items() if v}
        update = vals["options"].pop("UPDATE", {})
        updater = ""
        if vals["options"].pop("with", False):
            updater += " with "
            updater += " ".join(update)
        options = vals.pop("options", {})
        option_str = " ".join(["%s %s" % (k, v) for k, v in options.items()])
        vals["use_options"] = option_str
        vals["cfg_updates"] = updater
        command = "{base_dir}/{mainfile} {command} {use_options} {cfg_updates}".format(**vals)
        return command


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

    def items(self):
        return self._json.items()

    def __repr__(self):
        return "%s %r>" % (super(JSONObj, self).__repr__()[:-1],
                           self.keys())


class FileRun(BuildCommandMixin, object):
    def __init__(self, base_directory, run_directory, run_json):
        self._base_directory = os.path.expanduser(base_directory)
        self._run_directory = os.path.expanduser(run_directory)
        self._run_json = run_json
        self._artifacts = set(self["artifacts"])

    @lazy_property
    def config(self):
        return JSONObj.slurp(os.path.join(self._run_directory, "config.json"))

    @lazy_property
    def metrics(self):
        return JSONObj.slurp(os.path.join(self._run_directory, "metrics.json"))

    @property
    def run(self):
        return JSONObj(self._run_json)

    def __getitem__(self, value_path):
        return dictor.dictor(self._run_json, value_path)

    def keys(self):
        return self._run_json.keys()

    def info(self):
        str_format = "%Y-%m-%dT%H:%M:%S.%f"
        start_time = datetime.datetime.strptime(self["start_time"], str_format)
        stop_time = datetime.datetime.strptime(self['stop_time'], str_format) if self['stop_time'] else None
        return dict(
            run_directory=self._run_directory,
            name=self["experiment.name"],
            start_time=start_time,
            duration=(stop_time - start_time) if stop_time is not None else None)

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
        self.base_directory = os.path.expanduser(directory)
        self.sources_directory = os.path.join(self.base_directory, "_sources")
        if not os.path.exists(self.sources_directory):
            raise RuntimeError(("_sources directory not found, probably "
                                "not a sacred %r results directory!") %
                               (self.base_directory,))
        self._run_json = {}
        self.update()

    def update(self):
        self._runs = [run for run in os.listdir(self.base_directory) if run.isdigit()]
        self._runs.sort(key=lambda x: int(x))
        old_json = self._run_json
        self._run_json = {}
        for run in self._runs:
            if run in old_json:
                self._run_json[run] = old_json[run]  # use already loaded version

    def _get_run_json(self, run):
        assert run in self._runs
        json_filename = os.path.join(self.base_directory, run, "run.json")
        if os.path.exists(json_filename):
            self._run_json[run] = _slurp_json(json_filename)
        return self._run_json[run]

    def __getitem__(self, run_key):
        if not isinstance(run_key, str):
            conv_key = str(run_key)
            warnings.warn("Got item %r as run_key but expected a string, will be converted to: %r" % (run_key, conv_key))
            run_key = conv_key
        return FileRun(self.base_directory, os.path.join(self.base_directory, run_key), self._get_run_json(run_key))

    def keys(self):
        return self._runs

    def as_df(self, keyfilter=None):
        result = []
        keys = self.keys()
        if keyfilter is not None:
            keys = keyfilter(keys)
        for key in keys:
            tr = self[key]
            info = tr.info()
            values = dict(run_key=key,
                name=info["name"],
                status=tr["status"],
                start_time=info["start_time"],
                duration=info["duration"],

                )
            values.update(dict(tr.config.items()))
            result.append(values)
        return pd.DataFrame(result)
