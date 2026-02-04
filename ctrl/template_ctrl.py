import os

import config
from lib import path_utils


def register_template_helpers(app):
    root_dir = config.ROOT_DIR

    @app.template_global()
    def get_relative_path(path):
        return path_utils.get_relative_path(path, root_dir)

    @app.template_filter('starts_with_port')
    def starts_with_port_filter(name):
        import re
        return bool(re.match(r'^[0-9]{4}_', name))

    @app.template_filter('extract_port')
    def extract_port_filter(name):
        import re
        match = re.match(r'^([0-9]{4})_', name)
        return match.group(1) if match else ''

    @app.template_filter('dirname')
    def dirname_filter(path):
        return os.path.dirname(path)
