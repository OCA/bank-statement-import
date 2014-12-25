# -*- coding: utf-8 -*-
"""Handy utilities to use in parsing bank statement import files."""
##############################################################################
#
#    Copyright (C) 2009 EduSense BV (<http://www.edusense.nl>).
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import unicodedata

__all__ = ['str2date', 'date2str', 'date2date', 'to_swift']

try:
    from datetime import datetime
except AttributeError:
    from mx import DateTime as datetime


def str2date(datestr, fmt='%d/%m/%y'):
    """Convert a string to a datatime object"""
    return datetime.strptime(datestr, fmt)


def date2str(date, fmt='%Y-%m-%d'):
    """Convert a datetime object to a string"""
    return date.strftime(fmt)


def date2date(datestr, fromfmt='%d/%m/%y', tofmt='%Y-%m-%d'):
    """
    Convert a date in a string to another string, in a different
    fmt
    """
    return date2str(str2date(datestr, fromfmt), tofmt)

_SWIFT = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
          "/-?:().,'+ ")


def to_swift(astr, schemes=None):
    """
    Reduce a string to SWIFT fmt
    """
    schemes = schemes or ['utf-8', 'latin-1', 'ascii']
    if not isinstance(astr, unicode):
        for scheme in schemes:
            try:
                astr = unicode(astr, scheme)
                break
            except UnicodeDecodeError:
                pass
        if not isinstance(astr, unicode):
            return astr

    swift_string = [
        x in _SWIFT and x or ' '
        for x in unicodedata.normalize('NFKD', astr).encode('ascii', 'ignore')
    ]
    return ''.join(swift_string)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
