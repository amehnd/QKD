import yaml


class ConfigManager:

    @staticmethod
    def load(filename):

        with open(filename, "r") as f:

            return yaml.safe_load(f)

    @staticmethod
    def save(filename, data):

        with open(filename, "w") as f:

            yaml.dump(data, f)
