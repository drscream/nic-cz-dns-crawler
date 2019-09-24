import yaml
from os import path


def load_config(filename):
    pwd = path.dirname(__file__)
    with open(path.join(pwd, filename), "r") as conf_file:
        config = yaml.load(conf_file, Loader=yaml.BaseLoader)
    return config
