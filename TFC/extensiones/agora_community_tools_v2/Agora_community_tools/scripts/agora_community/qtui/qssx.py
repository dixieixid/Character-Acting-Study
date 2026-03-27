"""QSS Preprocessor."""

import re
import math


VAR_PATTERN = r'\$(\w+): *([$\w"\'#*/+-.,( )]+);'
CALC_PATTERN = r'(calc|round|floor|ceil)\(((?:[\d.]|[*/+-]|[( )]|px)+)\)'


def parse(styleSheet, variables=None):
    """Parse the style sheet."""
    variables = dict(variables) if variables else {}
    variables.update(extractVariables(styleSheet))

    for name in variables:
        variables[name] = evaluateVariables(str(variables[name]), variables)
        variables[name] = evaluateCalculations(
            variables[name],
            extractCalculations(variables[name]),
        )

    styleSheet = removeVariableDeclarations(styleSheet)
    styleSheet = evaluateVariables(styleSheet, variables)

    calculations = extractCalculations(styleSheet)

    styleSheet = evaluateCalculations(styleSheet, calculations)

    return styleSheet


def extractVariables(styleSheet):
    """Extract variables from style sheet."""
    variables = {}

    for data in re.findall(VAR_PATTERN, styleSheet):
        name = data[0]
        value = data[1]

        variables[name] = value

    return variables


def extractCalculations(styleSheet):
    """Extract calculations from style sheet."""
    calculations = []

    for data in re.findall(CALC_PATTERN, styleSheet):
        name = data[0]
        expression = data[1]

        calculations.append((name, expression))

    return calculations


def removeVariableDeclarations(styleSheet):
    """Remove variable declarations from style sheet."""
    return re.sub(r'[ \t]*{}\n?'.format(VAR_PATTERN), '', styleSheet)


def evaluateVariables(styleSheet, variables):
    """Replace variables in style sheet with their values."""
    for name in variables:
        styleSheet = re.sub(r'\${}\b'.format(name), str(variables[name]), styleSheet)

    return styleSheet


def evaluateCalculations(styleSheet, calculations):
    """Replace calculations in style sheet with their result."""
    for name, expression in calculations:
        parsedExpression = expression
        pxUnit = False

        if 'px' in parsedExpression:
            parsedExpression = parsedExpression.replace('px', '')
            pxUnit = True

        try:
            result = eval(parsedExpression)  # pylint: disable=eval-used
        except Exception:
            raise Exception('QSS: Wrong calculation: {}({})'.format(name, expression))

        if name == 'round':
            result = int(result + 0.5)  # round half up
        elif name == 'floor':
            result = math.floor(result)
        elif name == 'ceil':
            result = math.ceil(result)

        if pxUnit:
            result = '{}px'.format(str(round(float(result), 2)).rstrip('0').rstrip('.'))

        styleSheet = styleSheet.replace('{}({})'.format(name, expression), str(result))

    return styleSheet
