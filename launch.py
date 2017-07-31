#!/usr/bin/env python

import argparse
import logging
import sys

import app


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', default=False)
    args = parser.parse_args()
    logging.basicConfig(level='INFO')

    app.app.run(debug=args.debug)

if __name__ == '__main__':
    sys.exit(run())
