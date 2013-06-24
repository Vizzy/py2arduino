#!/usr/bin/env python3.3

import ast, os
from argparse import ArgumentParser
from warnings import warn

import ardlib

VAR_NEW = '{indent}{type} {name} = {value}'
VAR_REDEFINED = '{indent}{name} = {value}'
FUNC_DEF = '{type} {name}({args})\n{{}}'
FUNC_CALL = '{indent}{name}({args})'
BIN_OP = '{indent}{left} {op} {right}'

types = {
    'int': 'int',
    'float': 'float',
    'str': 'string',
    'None': 'void',
    'NoneType': 'void',
    'bool': 'boolean'
}

calc_indent = lambda obj: ' ' * obj.col_offset

class UnsupportedSemanticsError(Exception):
    pass

class TranslationWarning(Warning):
    pass

def convert_value(value):
    if type(value) is bool:
        if value:
            value = 'true'
        else:
            value = 'false'
    
    return value


def get_type(value):
    valtype = type(value)

    if valtype is str:
        return '{}[{}]'.format('string', len(value))
    else:
        return types[valtype.__name__]

def get_op(op):
    if isinstance(op, ast.Add):
        return '+'

    if isinstance(op, ast.Sub):
        return '-'

    if isinstance(op, ast.Mult):
        return '*'

    if isinstance(op, ast.Div):
        return '/'

def retrieve_info(obj):
    if isinstance(obj, list):
        yield [retrieve_info(x) for x in obj]

    if isinstance(obj, ast.Name):
        yield obj.id

    if isinstance(obj, ast.Num):
        yield obj.n

def to_arduino(obj, result={}):

    if obj == [] or obj is None:
        return result

    if isinstance(obj, list):
        result = to_arduino(obj[0], result)
        obj.pop(0)
        result = to_arduino(obj, result)

    elif isinstance(obj, ast.Module):
        result = to_arduino(obj.body, result)

    elif isinstance(obj, ast.FunctionDef):
        func_name = obj.name
        func_args = set()

        for arg in obj.args.args:
            arg_name = arg.arg
            arg_type = next(retrieve_info(arg.annotation))
            func_args.add((arg_name, arg_type))

        args_code = ''

        for n, arg in enumerate(func_args):
            if n + 1 < len(func_args):
                args_code += '{} {}, '.format(arg[1], arg[0])
            else:
                args_code += '{} {}'.format(arg[1], arg[0])

        if obj.returns is None:
            func_type = 'void'
        else:
            func_type = types[obj.returns.id]

        temp_result = result.copy()
        temp_result['code'] = ''
        to_arduino(obj.body, temp_result)
        body_code = temp_result['code']

        temp_code = FUNC_DEF.format(type=func_type, name=func_name,
                                args=args_code)

        partitioned = temp_code.partition('{')
        code = (partitioned[0] + partitioned[1]
                 + '\n' + body_code + partitioned[2])

        result['funcs'].add(func_name)
        result['var_names']['local'] = set()
        result['code'] += '\n' + code

    elif isinstance(obj, ast.Assign):
        var_name = obj.targets[0].id
        var_value = convert_value(next(retrieve_info(obj.value)))
        var_type = get_type(var_value)

        if obj.col_offset > 0:
            if (var_name in result['var_names']['local']
                or var_name in result['var_names']['global']):

                code = VAR_REDEFINED.format(indent=calc_indent(obj), name=var_name,
                 value=var_value)
            else:
                code = VAR_NEW.format(indent=calc_indent(obj), type=var_type,
                 name=var_name, 
                    value=var_value)
                result['var_names']['local'].add(var_name)
            
        else:
            if var_name in result['var_names']['global']:
                code = VAR_REDEFINED.format(indent=calc_indent(obj), name=var_name,
                 value=var_value)
            else:
                code = VAR_NEW.format(indent=calc_indent(obj), type=var_type,
                 name=var_name, 
                    value=var_value)
                result['var_names']['global'].add(var_name)

        result['code'] += code

    elif isinstance(obj, ast.Expr):
        return to_arduino(obj.value, result)

    elif isinstance(obj, ast.Call):
        func_name = next(retrieve_info(obj.func))

        if (func_name not in result['funcs']
            and not hasattr(ardlib, func_name)):
            warn('function {} (line {}) is not defined'.format(func_name,
                obj.lineno), TranslationWarning)

        args = next(retrieve_info(obj.args))

        # make them useable
        args = map(next, args)
        args = map(str, args)
        args = list(args)

        args_code = ''
        for n, arg in enumerate(args):
            if n + 1 < len(args):
                args_code += arg + ', '
            else:
                args_code += arg

        code = FUNC_CALL.format(indent=calc_indent(obj), name=func_name, args=args_code)
        result['code'] += code

    elif isinstance(obj, ast.Return):
        ret_value = to_arduino(obj.value, {'code': ''})
        result['code'] += calc_indent(obj) + 'return ' + ret_value['code'].lstrip()

    elif isinstance(obj, ast.BinOp):
        left = next(retrieve_info(obj.left))
        right = next(retrieve_info(obj.right))
        op = get_op(obj.op)

        code = BIN_OP.format(indent=calc_indent(obj),
            left=left, right=right, op=op)
        result['code'] += code

    elif isinstance(obj, ast.Pass):
        pass

    elif isinstance(obj, ast.Import) or isinstance(obj, ast.ImportFrom):
        pass

    else:
        raise UnsupportedSemanticsError('{} is currently not supported (line {})'.format(
            obj, obj.lineno))

    if (result['code'].endswith('}')):
        result['code'] += '\n\n'
    elif len(result['code'].rsplit('\n')[0]) > 0 and not result['code'].endswith('\n'):
        result['code'] += ';\n'

    return result

def translate(code):
    parsed = ast.parse(code)

    result_template = {
        'var_names': {'global': set(), 'local': set()},
        'funcs': set(),
        'code': ''
    }

    to_arduino(parsed, result_template)
    return result_template

def main():
    file = open(args.file)
    pycode = file.read()
    sketchname = file.name.split('.py')[0]
    sketchname = sketchname.rsplit('/')[1]
    result = translate(pycode)
    
    try:
        os.mkdir(sketchname)
    except OSError:
        pass

    with open('{0}/{0}.ino'.format(sketchname), 'w') as sketch:
        sketch.write(result['code'])

if __name__ == '__main__':
    argp = ArgumentParser()
    argp.add_argument('file', type=str, help='file to parse')
    args = argp.parse_args()

    main()
