# coding=utf-8
"""
The config object provides a simplified to access Sopel's configuration file.
The sections of the file are attributes of the object, and the keys in the
section are attributes of that. So, for example, the ``eggs`` attribute in the
``[spam]`` section can be accessed from ``config.spam.eggs``.

Section definitions (see "Section configuration sections" below) can be added
to the config object with ``define_section``. When this is done, only the
defined keys will be available. A section can not be given more than one
definition. The ``[core]`` section is defined with ``CoreSection`` when the
object is initialized.

.. versionadded:: 6.0.0
"""
# Copyright 2012-2015, Elsie Powell, embolalia.com
# Copyright © 2012, Elad Alfassa <elad@fedoraproject.org>
# Licensed under the Eiffel Forum License 2.

from __future__ import unicode_literals, absolute_import, print_function, division

import os
import sys

from sopel import tools
from . import core_section, types

if sys.version_info.major < 3:
    import ConfigParser
else:
    basestring = str
    import configparser as ConfigParser


DEFAULT_HOMEDIR = os.path.join(os.path.expanduser('~'), '.sopel')


class ConfigurationError(Exception):
    """Exception type for configuration errors"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'ConfigurationError: %s' % self.value


class ConfigurationNotFound(ConfigurationError):
    """Configuration file not found."""
    def __init__(self, filename):
        self.filename = filename
        """Path to the configuration file not found"""

    def __str__(self):
        return 'Unable to find the configuration file %s' % self.filename


class Config(object):
    def __init__(self, filename, validate=True):
        """The bot's configuration.

        The given filename will be associated with the configuration, and is
        the file which will be written if write() is called. If load is not
        given or True, the configuration object will load the attributes from
        the file at filename.

        A few default values will be set here if they are not defined in the
        config file, or a config file is not loaded. They are documented below.
        """
        self.filename = filename
        self.basename = os.path.basename(filename).rsplit('.', 1)[0]
        """The config object's associated file, as noted above."""
        self.parser = ConfigParser.RawConfigParser(allow_no_value=True)
        self.parser.read(self.filename)
        self.define_section('core', core_section.CoreSection,
                            validate=validate)
        self.get = self.parser.get

    @property
    def homedir(self):
        """An alias to config.core.homedir"""
        # Technically it's the other way around, so we can bootstrap filename
        # attributes in the core section, but whatever.
        configured = None
        if self.parser.has_option('core', 'homedir'):
            configured = self.parser.get('core', 'homedir')
        if configured:
            return configured
        else:
            return os.path.dirname(self.filename)

    def save(self):
        """Save all changes to the config file."""
        cfgfile = open(self.filename, 'w')
        self.parser.write(cfgfile)
        cfgfile.flush()
        cfgfile.close()

    def add_section(self, name):
        """Add a section to the config file.

        Returns ``False`` if already exists.
        """
        try:
            return self.parser.add_section(name)
        except ConfigParser.DuplicateSectionError:
            return False

    def define_section(self, name, cls_, validate=True):
        """Define the available settings in a section.

        ``cls_`` must be a subclass of ``StaticSection``. If the section has
        already been defined with a different class, ValueError is raised.

        If ``validate`` is True, the section's values will be validated, and an
        exception raised if they are invalid. This is desirable in a module's
        setup function, for example, but might not be in the configure function.
        """
        if not issubclass(cls_, types.StaticSection):
            raise ValueError("Class must be a subclass of StaticSection.")
        current = getattr(self, name, None)
        current_name = str(current.__class__)
        new_name = str(cls_)
        if (current is not None and not isinstance(current, self.ConfigSection) and
                not current_name == new_name):
            raise ValueError(
                "Can not re-define class for section from {} to {}.".format(
                    current_name, new_name)
            )
        setattr(self, name, cls_(self, name, validate=validate))

    class ConfigSection(object):

        """Represents a section of the config file.

        Contains all keys in thesection as attributes.

        """

        def __init__(self, name, items, parent):
            object.__setattr__(self, '_name', name)
            object.__setattr__(self, '_parent', parent)
            for item in items:
                value = item[1].strip()
                if not value.lower() == 'none':
                    if value.lower() == 'false':
                        value = False
                    object.__setattr__(self, item[0], value)

        def __getattr__(self, name):
            return None

        def __contains__(self, name):
            return name in vars(self)

        def __setattr__(self, name, value):
            object.__setattr__(self, name, value)
            if type(value) is list:
                value = ','.join(value)
            self._parent.parser.set(self._name, name, value)

        def get_list(self, name):
            value = getattr(self, name)
            if not value:
                return []
            if isinstance(value, basestring):
                value = value.split(',')
                # Keep the split value, so we don't have to keep doing this
                setattr(self, name, value)
            return value

    def __getattr__(self, name):
        if name in self.parser.sections():
            items = self.parser.items(name)
            section = self.ConfigSection(name, items, self)  # Return a section
            setattr(self, name, section)
            return section
        else:
            raise AttributeError("%r object has no attribute %r"
                                 % (type(self).__name__, name))

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __contains__(self, name):
        return name in self.parser.sections()

    def option(self, question, default=False):
        """Ask "y/n" and return the corresponding boolean answer.

        Show user in terminal a "y/n" prompt, and return true or false based on
        the response. If default is passed as true, the default will be shown
        as ``[y]``, else it will be ``[n]``. ``question`` should be phrased as
        a question, but without a question mark at the end.

        """
        d = 'n'
        if default:
            d = 'y'
        ans = tools.get_input(question + ' (y/n)? [' + d + '] ')
        if not ans:
            ans = d
        return ans.lower() == 'y'
