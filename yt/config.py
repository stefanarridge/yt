import os
import warnings

# TODO: import tomllib from the standard library instead in Python >= 3.11
import tomli as tomllib
import tomli_w
from more_itertools import always_iterable

from yt.utilities.configuration_tree import ConfigLeaf, ConfigNode

ytcfg_defaults = {}

ytcfg_defaults["yt"] = dict(
    serialize=False,
    only_deserialize=False,
    time_functions=False,
    colored_logs=False,
    suppress_stream_logging=False,
    stdout_stream_logging=False,
    log_level=20,
    inline=False,
    num_threads=-1,
    store_parameter_files=False,
    parameter_file_store="parameter_files.csv",
    maximum_stored_datasets=500,
    skip_dataset_cache=True,
    load_field_plugins=False,
    plugin_filename="my_plugins.py",
    parallel_traceback=False,
    pasteboard_repo="",
    reconstruct_index=True,
    test_storage_dir="/does/not/exist",
    test_data_dir="/does/not/exist",
    enzo_db="",
    notebook_password="",
    answer_testing_tolerance=3,
    answer_testing_bitwise=False,
    gold_standard_filename="gold311",
    local_standard_filename="local001",
    answer_tests_url="http://answers.yt-project.org/{1}_{2}",
    sketchfab_api_key="None",
    imagebin_api_key="e1977d9195fe39e",
    imagebin_upload_url="https://api.imgur.com/3/image",
    imagebin_delete_url="https://api.imgur.com/3/image/{delete_hash}",
    curldrop_upload_url="http://use.yt/upload",
    thread_field_detection=False,
    ignore_invalid_unit_operation_errors=False,
    chunk_size=1000,
    xray_data_dir="/does/not/exist",
    supp_data_dir="/does/not/exist",
    default_colormap="cmyt.arbre",
    ray_tracing_engine="embree",
    internals=dict(
        within_testing=False,
        within_pytest=False,
        parallel=False,
        strict_requires=False,
        global_parallel_rank=0,
        global_parallel_size=1,
        topcomm_parallel_rank=0,
        topcomm_parallel_size=1,
        command_line=False,
    ),
)


def config_dir():
    config_root = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")
    )
    conf_dir = os.path.join(config_root, "yt")

    if not os.path.exists(conf_dir):
        try:
            os.makedirs(conf_dir)
        except OSError:
            warnings.warn("unable to create yt config directory")
    return conf_dir


# For backward compatibility, do not use these vars internally in yt
CONFIG_DIR = config_dir()


class YTConfig:
    def __init__(self, defaults=None):
        if defaults is None:
            defaults = {}
        self.config_root = ConfigNode(None)

    def get(self, section, *keys, callback=None):
        node_or_leaf = self.config_root.get(section, *keys)
        if isinstance(node_or_leaf, ConfigLeaf):
            if callback is not None:
                return callback(node_or_leaf)
            return node_or_leaf.value
        return node_or_leaf

    def get_most_specific(self, section, *keys, **kwargs):
        use_fallback = "fallback" in kwargs
        fallback = kwargs.pop("fallback", None)
        try:
            return self.config_root.get_deepest_leaf(section, *keys)
        except KeyError as err:
            if use_fallback:
                return fallback
            else:
                raise err

    def update(self, new_values, metadata=None):
        if metadata is None:
            metadata = {}
        self.config_root.update(new_values, metadata)

    def has_section(self, section):
        try:
            self.config_root.get_child(section)
            return True
        except KeyError:
            return False

    def add_section(self, section):
        self.config_root.add_child(section)

    def remove_section(self, section):
        if self.has_section(section):
            self.config_root.remove_child(section)
            return True
        else:
            return False

    def set(self, *args, metadata=None):
        section, *keys, value = args
        if metadata is None:
            metadata = {"source": "runtime"}
        self.config_root.upsert_from_list(
            [section] + list(keys), value, extra_data=metadata
        )

    def remove(self, *args):
        self.config_root.pop_leaf(args)

    def read(self, file_names):
        file_names_read = []
        for fname in always_iterable(file_names):
            if not os.path.exists(fname):
                continue
            metadata = {"source": f"file: {fname}"}
            with open(fname, "rb") as fh:
                data = tomllib.load(fh)
            self.update(data, metadata=metadata)
            file_names_read.append(fname)

        return file_names_read

    def write(self, file_handler):
        value = self.config_root.as_dict()
        config_as_str = tomli_w.dumps(value)

        try:
            # Assuming file_handler has a write attribute
            file_handler.write(config_as_str)
        except AttributeError:
            # Otherwise we expect a path to a file
            with open(file_handler, mode="w") as fh:
                fh.write(config_as_str)

    @staticmethod
    def get_global_config_file():
        return os.path.join(config_dir(), "yt.toml")

    @staticmethod
    def get_local_config_file():
        return os.path.join(os.path.abspath(os.curdir), "yt.toml")

    def __setitem__(self, args, value):
        section, *keys = always_iterable(args)
        self.set(section, *keys, value, metadata=None)

    def __getitem__(self, key):
        section, *keys = always_iterable(key)
        return self.get(section, *keys)

    def __contains__(self, item):
        return item in self.config_root

    # Add support for IPython rich display
    # see https://ipython.readthedocs.io/en/stable/config/integrating.html
    def _repr_json_(self):
        return self.config_root._repr_json_()


_global_config_file = YTConfig.get_global_config_file()
_local_config_file = YTConfig.get_local_config_file()

if not os.path.exists(_global_config_file):
    cfg = {"yt": {}}  # type: ignore
    try:
        with open(_global_config_file, mode="wb") as fd:
            tomli_w.dump(cfg, fd)
    except OSError:
        warnings.warn("unable to write new config file")


# Load the config
ytcfg = YTConfig()
ytcfg.update(ytcfg_defaults, metadata={"source": "defaults"})

# Try loading the local config first, otherwise fall back to global config
if os.path.exists(_local_config_file):
    ytcfg.read(_local_config_file)
elif os.path.exists(_global_config_file):
    ytcfg.read(_global_config_file)
