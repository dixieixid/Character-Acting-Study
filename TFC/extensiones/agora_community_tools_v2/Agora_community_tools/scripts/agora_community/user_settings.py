"""Allow user settings to be saved and loaded using JSON.

The values are validated based on the provided defaults:
- when loading from a file at initialization, the invalid values will be ignored
- when setting values, exceptions will be raised for invalid values
- when setting values using a dictionary (either with direct assignment or with `update`),
  the dictionary can contain fewer values than the defaults; the existing values will not be deleted.

Warning: The dictionaries will be converted to `Settings` objects; use `as_dict`.

Usage:
------

# Create an instance of the `Settings` class.
settings = user_settings.Settings('file_name', **DEFAULTS_DICT)
# or ...
settings = user_settings.Settings('file_name', option=value, ...)
# or ...
class Settings(user_settings.Settings):
    class InnerOptions(object):
        option = value
        ...

    inner_options = InnerOptions
    other_option = value
#
settings = Settings('file_name')

# Get/set values using member or dictionary-like access.
settings.name
settings.name = value
settings.name = { ... }
settings.name.inner_name = value
#
settings['name']
settings['name'] = value
settings['name] = { ... }
settings['name']['inner_name'] = value

# Update many settings at once from a dictionary.
settings.update({ ... })

# Call save when needed.
settings.save()

# Call load to update from file.
settings.load()  # rarely needed since it will be called automatically on instantiation

# Retrieve the settings as a dictionary.
settings.as_dict()
"""

import json
import os

from .mayalib import user_directory
from .constants import USER_DIR_NAME, SETTINGS_DIR_NAME

SETTINGS_PATH = os.path.join(user_directory(), USER_DIR_NAME, SETTINGS_DIR_NAME)


class SettingsError(Exception):
    """Base class for all Settings' exceptions."""


class Settings(object):
    "The main class responsible for saving/loading the settings."

    def __init__(self, name, **defaults):
        self._settings = {}

        self._set_defaults(_find_class_default_attributes(self.__class__))
        self._set_defaults(defaults)

        self._validate_restricted_settings()

        if isinstance(name, Settings):
            self._root = name
            self._name = None
            self._file_path = None
        else:
            self._root = None
            self._name = name
            self._file_path = os.path.join(SETTINGS_PATH, self._name + '.json')

            self.load(validate=False)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super(Settings, self).__setattr__(name, value)
        else:
            self.__setitem__(name, value)

    def __getattribute__(self, name):
        if not name.startswith('_') and name in self._settings:
            return self._settings[name]

        try:
            return super(Settings, self).__getattribute__(name)
        except AttributeError:
            raise SettingsError('Setting "{}" not found.'.format(name))

    def __setitem__(self, name, value):
        self._validate_setting(name, value)

        if isinstance(value, dict):
            for dict_key, dict_value in value.items():
                self._settings[name][dict_key] = dict_value
        else:
            self._settings[name] = value

    def __getitem__(self, name):
        try:
            return self._settings[name]
        except KeyError:
            raise SettingsError('Setting "{}" not found.'.format(name))

    def load(self, validate=True):
        """Load the settings from file.

        If `validate` is `True`, an exception will be raised if validation fails.
        If `validate` is `False`, values will be ignored if validation fails.
        """
        if self._root:
            self._root.load()
            return

        if not os.path.exists(self._file_path):
            return

        with open(self._file_path) as file:
            try:
                file_settings = json.load(file)
            except ValueError as error:
                raise SettingsError('Invalid settings file {} | {}'.format(self._file_path, error))

        self.update(file_settings, validate)

    def save(self):
        """Save the settings to file."""
        if self._root:
            self._root.save()
            return

        if not os.path.exists(SETTINGS_PATH):
            os.makedirs(SETTINGS_PATH)

        with open(self._file_path, 'w') as file:
            json.dump(self.as_dict(), file, indent=4)

    def update(self, settings, validate=True):
        """Update the settings from a dictionary.

        If `validate` is `True`, an exception will be raised if validation fails.
        If `validate` is `False`, values will be ignored if validation fails.
        """
        for key, value in settings.items():
            try:
                self._validate_setting(key, value)
            except SettingsError as error:
                if validate:
                    raise SettingsError(error.message)
                else:
                    continue

            if isinstance(self[key], Settings):
                self[key].update(value, validate)
            else:
                self[key] = value

    def as_dict(self):
        """Retrieve the settings as a dictionary."""
        settings_dict = {}

        for name, value in self._settings.items():
            if isinstance(value, Settings):
                settings_dict[name] = value.as_dict()
            else:
                settings_dict[name] = value

        return settings_dict

    def _set_defaults(self, defaults):
        for key, value in defaults.items():
            if isinstance(value, dict):
                self._settings[key] = Settings(self, **value)
            elif _is_custom_class_instance(value):
                self._settings[key] = Settings(
                    self, **_find_class_default_attributes(value.__class__)
                )
            else:
                self._settings[key] = value

    def _validate_setting(self, name, value):
        try:
            setting_value = self._settings[name]
        except KeyError:
            raise SettingsError('Setting "{}" not found.'.format(name))

        if isinstance(setting_value, bool) and not isinstance(value, bool):
            raise SettingsError('Value for "{}" should be a boolean.'.format(name))

        if isinstance(setting_value, (int, float)) and not isinstance(value, (int, float)):
            raise SettingsError('Value for "{}" should be a number.'.format(name))

        if isinstance(setting_value, str) and not isinstance(value, str):
            raise SettingsError('Value for "{}" should be a string.'.format(name))

        if isinstance(setting_value, list) and not isinstance(value, list):
            raise SettingsError('Value for "{}" should be a list.'.format(name))

        if isinstance(setting_value, Settings) and not isinstance(value, dict):
            raise SettingsError('Value for "{}" should be a dictionary.'.format(name))

    def _validate_restricted_settings(self):
        methods = [
            name
            for name, value in Settings.__dict__.items()
            if not name.startswith('_') and callable(value)
        ]

        for name in methods:
            if name in self._settings:
                raise SettingsError('Setting "{}" is restricted.'.format(name))


def _find_class_default_attributes(cls):
    attributes = {}

    for base_class in reversed(cls.__mro__[:-1]):
        for name, value in base_class.__dict__.items():
            is_valid_attribute = (
                not name.startswith('_')
                and not name.isupper()
                and not callable(value)
                and not isinstance(value, property)
                and not isinstance(value, classmethod)
                and not isinstance(value, staticmethod)
            )

            if is_valid_attribute:
                attributes[name] = value

    return attributes


def _is_custom_class_instance(obj):
    return type(obj).__module__ != object.__module__
