import logging
import os
import subprocess
import sys
import time

logger = logging.getLogger(__name__)


class NeedReload(Exception):
    pass


class ReloadWatcher(object):
    def __init__(self):
        super(ReloadWatcher, self).__init__()
        self.launch_time = time.time()

    def __call__(self):
        self.reload_if_needed()

    def reload_if_needed(self):
        changed_files = []
        for module in sys.modules.values():
            if module is None or '__file__' not in module.__dict__:
                continue

            if os.stat(module.__file__).st_mtime > self.launch_time:
                changed_files.append(module.__file__)

        if changed_files:
            raise NeedReload('Reloading due changes in:\n' +
                             '\n'.join(' - ' + path for path in changed_files))


def launch(command):
    logger.info('Launching: %s', ' '.join(repr(part) for part in command))
    return subprocess.call(command)


def run(command):
    while launch(command):
        logger.info('Waiting for 1 second before relaunch...')
        time.sleep(1)
