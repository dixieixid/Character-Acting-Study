"""Custom types."""

from .exceptions import AnimLocatorError


class CtrlType(object):
    """The animation control type."""

    LOCATOR = 1
    CIRCLE = 2
    SPHERE = 3
    CUBE = 4
    PYRAMID = 5

    @classmethod
    def all(cls):
        """Retrieve all control types."""
        ctrl_types = []

        for attr_name, attr_value in cls.__dict__.items():
            if not attr_name.startswith('_') and isinstance(attr_value, int):
                ctrl_types.append(attr_value)

        ctrl_types.sort()

        return ctrl_types

    @classmethod
    def name(cls, ctrl_type):
        """Retrieve the name of the control type."""
        for attr_name, attr_value in cls.__dict__.items():
            if (
                not attr_name.startswith('_')
                and isinstance(attr_value, int)
                and attr_value == ctrl_type
            ):
                return attr_name.lower()

        raise AnimLocatorError('Invalid control type "{}".'.format(ctrl_type))


class ConstraintType(object):
    """The animation contraint type."""

    PARENT = 1
    POSITION = 2
    ROTATION = 3

    @classmethod
    def is_position(cls, constraint_type):
        """Check if the `constraint_type` is a position constraint."""
        return constraint_type in (cls.PARENT, cls.POSITION)

    @classmethod
    def is_rotation(cls, constraint_type):
        """Check if the `constraint_type` is a rotation constraint."""
        return constraint_type in (cls.PARENT, cls.ROTATION)


class OperationType(object):
    """The multi-step operation type."""

    NONE = 0
    PIVOT = 1
    AIM = 2
