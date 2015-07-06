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
import re
import sys
import traceback

from bs4 import UnicodeDammit

import dateutil.parser
import dominate
from dominate.tags import *
import pytz
import requests

DEFAULTLOGLEVEL = logging.WARNING
LOCAL = pytz.timezone ("America/Chicago")
RX_PUNCT = re.compile(ur'[\p{P}_\d]+')

def arglogger(func):
    """
    decorator to log argument calls to functions
    """
    @wraps(func)
    def inner(*args, **kwargs): 
        logger = logging.getLogger(func.__name__)
        logger.debug("called with arguments: %s, %s" % (args, kwargs))
        return func(*args, **kwargs) 
    return inner    

def dateout(_datetime):
    try:
        mydt = _datetime.astimezone(pytz.utc)
    except ValueError:
        mydt = pytz.utc.localize(_datetime).astimezone(pytz.utc)
    return mydt.strftime('%d %b %Y %H:%M:%S %z').replace(u'+0000', u'UTC')

@arglogger
def un_camel(x):
    """Convert CamelCase strings to space-delimited

    This function is slightly adapated from an example provided by Teh Tris:
    http://stackoverflow.com/posts/19940888/revisions
    """
    final = ''
    for item in x:
        if item.isupper():
            final += " "+item.lower()
        else:
            final += item
    if final[0] == " ":
        final = final[1:]
    return final

def html_out(doc, filepath):
    logger = logging.getLogger(sys._getframe().f_code.co_name)
    content = unicode(doc)
    content = content.encode('utf-8')
    with open(filepath, 'w') as file_html:
        try:
            file_html.write(content)
        except UnicodeDecodeError, e:
            msg = unicode(e) + u' file: {0}'.format(filepath)
            logger.error(msg)
            raise

def list_entry(parent, rp):
    logger = logging.getLogger(sys._getframe().f_code.co_name)

    _li = parent.add(li())
    title_text = unicode(rp['title'])
    try:
        domain_u = unicode(rp['domain'])
    except UnicodeDecodeError:
        logger.error(rp['domain'])
        raise
    try:
        hash_u = unicode(rp['hash'])
    except UnicodeDecodeError:
        logger.error(rp['hash'])
        raise
    content_href = u'/'.join((u'.', domain_u, hash_u)) + u'.html'
    _li += a(title_text, href=content_href)
    if 'issn' in rp.keys() or 'isbn' in rp.keys():
        _li += u' ('
        if 'issn' in rp.keys():
            _li += u'issn: {0}'.format(rp['issn'])
        if 'issn' in rp.keys() and 'isbn' in rp.keys():
            _li += u', '
        if 'isbn' in rp.keys():
            _li += u'isbn: {0}'.format(rp['isbn'])
        _li += u')'
    return _li

def index_primary(primary, path_dest):
    logger = logging.getLogger(sys._getframe().f_code.co_name)
    doc = dominate.document(title=u'AWOL Index: Top-Level Resources')
    with doc.head:
        link(rel='stylesheet', type='text/css', href='http://yui.yahooapis.com/3.18.1/build/cssreset/cssreset-min.css')
        link(rel='stylesheet', type='text/css', href='http://yui.yahooapis.com/3.18.1/build/cssreset/cssreset-min.css')
        link(rel='stylesheet', type='text/css', href='./index-style.css')
    doc += h1('Index of Top-Level Resources')
    _ul = doc.add(ul())
    for p in sorted([p for p in primary if ' ' not in p['domain']], key=lambda k: k['title'].lower()):
        _li = list_entry(_ul, p)
    html_out(doc, os.path.join(path_dest, 'index-top.html'))

def index_keywords(keywords, path_dest):
    doc = dominate.document(title=u'AWOL Index: Resources by Keywords')
    with doc.head:
        link(rel='stylesheet', type='text/css', href='http://yui.yahooapis.com/3.18.1/build/cssreset/cssreset-min.css')
        link(rel='stylesheet', type='text/css', href='http://yui.yahooapis.com/3.18.1/build/cssreset/cssreset-min.css')
        link(rel='stylesheet', type='text/css', href='./index-style.css')
    doc += h1('Index of Resources by Keywords')
    for kw in sorted(keywords.keys(), key=lambda s: s.lower()):
        _div = doc.add(div(id=kw.lower().replace(u' ', u'-')))
        _div += h2(kw)
        _ul = _div.add(ul())
        for p in sorted([p for p in keywords[kw] if ' ' not in p['domain']], key=lambda k: k['title'].lower()):
            _li = list_entry(_ul, p)
    html_out(doc, os.path.join(path_dest, 'index-keywords.html'))

@arglogger
def main (args):
    """
    main functions
    """
    logger = logging.getLogger(sys._getframe().f_code.co_name)

    path_source = os.path.realpath(args.json[0])
    path_dest = os.path.abspath(args.html[0])
    print('path_dest: {0}'.format(path_dest))
    r = requests.get('https://raw.githubusercontent.com/mattcg/language-subtag-registry/master/data/json/registry.json')
    if r.status_code == 200:
        lang_registry = r.json()
    else:
        # load from file
        pass
    languages = {}
    for lang in lang_registry:
        if lang['Type'] == 'language':
            languages[lang['Subtag']] = lang['Description'][0]

    # statistics and indexes
    quality_primary = 0.0
    quality_subordinate = 0.0
    quantity_primary = 0
    quantity_subordinate = 0
    primary = []
    secondary = []
    domains = []
    keywords = {}
    primary = []
    def grade(ratio):
        if ratio >= 0.9:
            return 'A'
        elif ratio >= 0.8:
            return 'B'
        elif ratio >= 0.7:
            return 'C'
        elif ratio >= 0.6:
            return 'D'
        else:
            return 'F'



    for dir_name, sub_dir_list, file_list in os.walk(path_source):
        this_dir = os.path.basename(dir_name)
        try:
            logger.info(u'converting {0}'.format(this_dir))
        except UnicodeDecodeError:
            try:
                logger.info('converting {0}'.format(this_dir))
            except UnicodeDecodeError:
                try:
                    logger.info(u'converting {0}'.format(UnicodeDammit(this_dir).unicode_markup))
                except UnicodeDecodeError:
                    logger.warning('this directory name is unspeakable evil')

        for file_name_json in file_list:
            with open(os.path.join(dir_name, file_name_json), 'r') as file_json:
                resource = json.load(file_json)
            this_out = os.path.splitext(file_name_json)[0]

            # stats and grades

            rtitle = resource['title']
            rdesc = resource['description']
            if rdesc is not None:
                rdescwords = sorted(set(RX_PUNCT.sub(u'', rdesc).lower().split()))
                rtitlewords = sorted(set(RX_PUNCT.sub(u'', rtitle).lower().split()))
                if rdescwords != rtitlewords:
                    if len(rdescwords) > 6 or resource['volume'] is not None or resource['year'] is not None:
                        quality = 1.0
                    else:
                        quality = 0.5
                else:
                    quality = 0.0
            else:
                quality = 0.0
            pkg = {
                'domain': this_dir,
                'hash': this_out,
                'title': rtitle,
                'url': resource['url']
            }
            issn = None
            isbn = None
            try:
                issn = resource['identifiers']['issn']['electronic'][0]
            except KeyError:
                try:
                    issn = resource['identifiers']['issn']['generic'][0]
                except KeyError:
                    try:
                        isbn = resource['identifiers']['isbn']['electronic'][0]
                    except KeyError:
                        try:
                            isbn = resource['identifiers']['isbn']['generic'][0]
                        except KeyError:
                            pass
            if issn is not None:
                pkg['issn'] = issn
            if isbn is not None:
                pkg['isbn'] = isbn
            if resource['is_part_of'] is not None and len(resource['is_part_of']) > 0:
                quantity_subordinate += 1
                quality_subordinate += quality
            else:
                primary.append(pkg)
                quantity_primary += 1
                quality_primary += quality
            for k in resource['keywords']:
                try:
                    kwlist = keywords[k]
                except KeyError:
                    kwlist = keywords[k] = []
                kwlist.append(pkg)
            # make html
            doc = dominate.document(title=u'AWOL Index: {0}'.format(resource['title']))
            with doc.head:
                link(rel='stylesheet', type='text/css', href='http://yui.yahooapis.com/3.18.1/build/cssreset/cssreset-min.css')
                link(rel='stylesheet', type='text/css', href='http://yui.yahooapis.com/3.18.1/build/cssreset/cssreset-min.css')
                link(rel='stylesheet', type='text/css', href='../item-style.css')
            doc += h1(a(resource['title'], href=resource['url']))
            _dl = doc.add(dl())
            for k in sorted(resource.keys()):
                if k != 'title' and k!= 'provenance' and resource[k] is not None:
                    field = resource[k]
                    if type(field) in [list, dict]:
                        if len(field) > 0:
                            if k == 'identifiers':
                                for ident_type in field.keys():
                                    if type(field[ident_type]) == dict:
                                        for ident_subtype in field[ident_type].keys():
                                            if ident_subtype == 'generic':
                                                _dl += dt(u'{0}: '.format(ident_type))
                                            else:
                                                _dl += dt(u'{0} ({1}): '.format(ident_type, ident_subtype))
                                            _dl += dd(field[ident_type][ident_subtype])
                                    elif type(field[ident_type]) == list:
                                        _dl += dt(u'{0}: '.format(ident_type))
                                        for v in field[ident_type]:
                                            _dl += dt(u'{0}: '.format(v))
                                    else:
                                        raise ValueError('heckito')
                            else:
                                _dl += dt(k.replace(u'_', u' '))
                                if type(field) == list:
                                    if k == 'language':
                                        _dl += dd(languages[resource[k][0]])
                                    elif k in ['subordinate_resources', 'related_resources']:
                                        _ul = _dl.add(ul())
                                        for rr in field:
                                            _ul += li(a(rr['title_full'], href=rr['url']))
                                    else:
                                        _dl += dd(u', '.join(sorted([unicode(thing) for thing in resource[k]])))
                                else:
                                    _ul = ul()
                                    for kk in sorted(field.keys()):
                                        if type(field[kk]) in [unicode, str] and field[kk][0:4] == 'http':
                                                _li = _ul.add(li(u'{0}: '.format(kk)))
                                                _li += a(field[kk], href=field[kk])
                                        else:
                                            _ul += li(u'{0}: {1}'.format(kk, field[kk]))
                                    _dl += dd(_ul)
                    else:
                        _dl += dt(k)
                        if resource[k][0:4] == 'http':
                            _dl += dd(a(resource[k], href=resource[k]))
                        else:
                            _dl += dd(resource[k])

            if 'provenance' in resource.keys():
                _div = doc.add(div(id='provenance'))
                _div += h2('data provenance')
                _dl = _div.add(dl())
                events = sorted([prov for prov in resource['provenance']], key=lambda k: k['when'])
                for event in events:
                    try:
                        _dl += dt(dateout(dateutil.parser.parse(event['when'])))
                    except ValueError:
                        _dl += dt(dateout(LOCAL.localize(dateutil.parser.parse(event['when']))))
                    _dd = _dl.add(dd(u'{0}: '.format(un_camel(event['term'].split(u'/')[-1]).replace(u'cites as ', u''))))
                    rid = event['resource']
                    if rid[0:4] == 'http':
                        _dd += (a(rid.split('://')[1], href=rid))
                    else:
                        _dd += rid
                    try:
                        _dd += u' (last updated: {0})'.format(dateout(dateutil.parser.parse(event['resource_date'])))
                    except KeyError:
                        _dd += u' (last updated not indicated)'

                        
            #print (unicode(doc))
            file_name_html = '.'.join((this_out, 'html'))
            out_path = os.path.join(path_dest, this_dir)
            file_path_html = os.path.join(out_path, file_name_html)
            #print file_path_html
            try:
                os.makedirs(out_path)
            except OSError as exc: # Python >2.5
                if exc.errno == errno.EEXIST and os.path.isdir(out_path):
                    pass
                else: raise
            with open(file_path_html, 'w') as file_html:
                file_html.write(unicode(doc).encode('utf-8'))



        for ignore_dir in ['.git', '.svn', '.hg']:
            if ignore_dir in sub_dir_list:
                sub_dir_list.remove(ignore_dir)

    index_primary(primary, path_dest)
    index_keywords(keywords, path_dest)
    quantity = quantity_primary + quantity_subordinate
    print "quantity: {0}".format(quantity)
    print "   top-level: {0}".format(quantity_primary)
    print "   subordinate: {0}".format(quantity_subordinate)
    qratio = (quality_primary + quality_subordinate) / float(quantity)
    qratio_primary = quality_primary / float(quantity_primary)
    qratio_subordinate = quality_subordinate / float(quantity_subordinate)
    print "quality ratio: {0:.2f}".format(qratio)
    print "   top-level: {0:.2f}".format(qratio_primary)
    print "   subordinate: {0:.2f}".format(qratio_subordinate)
    print "grade: {0}".format(grade(qratio))
    print "   top-level: {0}".format(grade(qratio_primary))
    print "   subordinate: {0}".format(grade(qratio_subordinate))

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
        parser.add_argument('html', type=str, nargs=1, help='html output directory')
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
