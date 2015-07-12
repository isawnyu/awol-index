#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
create HTML from isaw.awol JSON
"""

import argparse
import errno
from functools import wraps
import json
import logging
import os
from pprint import pprint
import sys
import traceback

from bs4 import UnicodeDammit

DEFAULTLOGLEVEL = logging.WARNING


def main (args):
    """
    main functions
    """
    logger = logging.getLogger(sys._getframe().f_code.co_name)

    path_source = os.path.realpath(args.json[0])

    fields = []
    files = 0

    for dir_name, sub_dir_list, file_list in os.walk(path_source):
        this_dir = os.path.basename(dir_name)
        try:
            dirname = unicode(this_dir)
        except UnicodeDecodeError:
            try:
                dirname = UnicodeDammit(this_dir).unicode_markup
            except UnicodeDecodeError:
                logger.warning('this directory name is unspeakable evil')
                dirname = u'[[[EVIL]]]'

        for file_name_json in file_list:
            files += 1
            with open(os.path.join(dir_name, file_name_json), 'r') as file_json:
                resource = json.load(file_json)
            for field in resource.keys():
                if field not in fields:
                    fields.append(field)
            pprint(resource)
            del resource
            if files % 250 == 0:
                logger.debug(u'parsed {0} files: {1} fields at {2}'.format(files, len(fields), dirname))

    for field in sorted(fields):
        print (field)


if __name__ == "__main__":
    log_level = DEFAULTLOGLEVEL
    log_level_name = logging.getLevelName(log_level)
    logging.basicConfig(level=log_level)

    try:
        parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument ("-l", "--loglevel", type=str, help="desired logging level (case-insensitive string: DEBUG, INFO, WARNING, ERROR" )
        parser.add_argument ("-v", "--verbose", action="store_true", default=False, help="verbose output (logging level == INFO")
        parser.add_argument ("-vv", "--veryverbose", action="store_true", default=False, help="very verbose output (logging level == DEBUG")
        parser.add_argument('json', type=str, nargs=1, help='json source directory')
        args = parser.parse_args()
        if args.loglevel is not None:
            args_log_level = re.sub('\s+', '', args.loglevel.strip().upper())
            try:
                log_level = getattr(logging, args_log_level)
            except AttributeError:
                logging.error("command line option to set log_level failed because '%s' is not a valid level name; using %s" % (args_log_level, log_level_name))
        if args.veryverbose:
            log_level = logging.DEBUG
        elif args.verbose:
            log_level = logging.INFO
        log_level_name = logging.getLevelName(log_level)
        logging.getLogger().setLevel(log_level)
        if log_level != DEFAULTLOGLEVEL:
            logging.warning("logging level changed to %s via command line option" % log_level_name)
        else:
            logging.info("using default logging level: %s" % log_level_name)
        logging.debug("command line: '%s'" % ' '.join(sys.argv))
        main(args)
        sys.exit(0)
    except KeyboardInterrupt, e: # Ctrl-C
        raise e
    except SystemExit, e: # sys.exit()
        raise e
    except Exception, e:
        print "ERROR, UNEXPECTED EXCEPTION"
        print str(e)
        traceback.print_exc()
        os._exit(1)
