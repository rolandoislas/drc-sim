import configparser
import os


class Config:

    def __init__(self):
        self.path = ""
        self.config = configparser.ConfigParser(allow_no_value=True)

    def load(self, path):
        self.path = os.path.expanduser(path)
        self.config.read(self.path)

    def get_boolean(self, section, option, default, comment=""):
        try:
            value = self.config.getboolean(section, option)
            self.add_value(section, option, value, comment, default=default)
            return value
        except (ValueError, configparser.NoSectionError, configparser.NoOptionError):
            self.add_value(section, option, default, comment, default=default)
            return default

    def add_value(self, section, option, value, comment, min_val="", max_val="", default=""):
        value = str(value)
        min_val = str(min_val) if min_val else None
        max_val = str(max_val) if max_val else None
        default = str(default)
        if not self.config.has_section(section):
            self.config.add_section(section)

        if comment:
            self.config.set(section, "# " + comment.replace("\n", "\n# "))
        comment_str = "min: " + min_val + " " if min_val else ""
        comment_str += "max: " + max_val + " " if max_val else ""
        comment_str += "default: " + default + " " if default else ""
        self.config.set(section, "# " + comment_str)

        if self.config.has_option(section, option):
            self.config.remove_option(section, option)
        self.config.set(section, option, value)

    def get_float(self, section, option, min_val, max_val, default, comment=""):
        try:
            value = self.config.getfloat(section, option)
            self.add_value(section, option, value, comment, min_val, max_val, default)
            return self.get_min_max(value, min_val, max_val)
        except (ValueError, configparser.NoSectionError, configparser.NoOptionError):
            self.add_value(section, option, default, comment, min_val, max_val, default)
            return default

    def get_int(self, section, option, min_val, max_val, default, comment=""):
        try:
            value = self.config.getint(section, option)
            self.add_value(section, option, value, comment, min_val, max_val, default)
            return self.get_min_max(value, min_val, max_val)
        except (ValueError, configparser.NoSectionError, configparser.NoOptionError):
            self.add_value(section, option, default, comment, min_val, max_val, default)
            return default

    @staticmethod
    def get_min_max(value, min_val, max_val):
        if min_val and value < min_val:
            return min_val
        elif max_val and value > max_val:
            return max_val
        else:
            return value

    def save(self):
        path_parts = os.path.split(self.path)
        path = ""
        for index in range(0, len(path_parts)):
            if index < len(path_parts) - 1:
                path += os.path.sep + path_parts[index]
        if os.name == "nt":
            path = path.replace(os.path.sep, "", 1)
        path = os.path.abspath(path)
        if not os.path.exists(path):
            os.makedirs(path)
        file_out = open(self.path, "w")
        self.config.write(file_out)
        file_out.close()
