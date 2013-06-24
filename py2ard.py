#!/usr/bin/env python3.3

import ast, os, subprocess
from argparse import ArgumentParser
from warnings import warn, simplefilter

import ardlib

VAR_NEW = '{indent}{type} {name} = {value}'
VAR_REDEFINED = '{indent}{name} = {value}'
FUNC_DEF = '{type} {name}({args})'
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

MAKE_STRUCTURE = '''CODE_DIR = {sketch_folder}
BOARD_TAG = {board}
ARDUINO_PORT = {port}
include $(ARDMK_DIR)/arduino-mk/Arduino.mk'''

class UnsupportedSemanticsError(Exception):
    pass

class UndeclaredFunctionWarning(Warning):
    pass

calc_indent = lambda obj: ' ' * obj.col_offset

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

def to_arduino(obj, result={'code': ''}, terminate=True):

    if obj == [] or obj is None:
        return result

    if isinstance(obj, list):
        result = to_arduino(obj[0], result, terminate=terminate)
        obj.pop(0)
        result = to_arduino(obj, result, terminate=terminate)

    elif isinstance(obj, ast.Name):
        return {'code': obj.id}

    elif isinstance(obj, ast.Num):
        return {'code': obj.n}

    elif isinstance(obj, ast.Module):
        result = to_arduino(obj.body, result, terminate=terminate)

    elif isinstance(obj, ast.FunctionDef):
        func_name = obj.name
        func_args = set()

        for arg in obj.args.args:
            arg_name = arg.arg
            arg_type = to_arduino(arg.annotation, terminate=terminate)['code']
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
        to_arduino(obj.body, temp_result, terminate=terminate)
        body_code = temp_result['code']

        declaration_code = FUNC_DEF.format(type=func_type, name=func_name,
                                args=args_code)

        code = (declaration_code + '\n{\n'
                 + body_code + '}\n\n')

        result['funcs'].add(func_name)
        result['var_names']['local'] = set()
        result['code'] += code

        if func_name != 'setup' and func_name != 'loop':
            result['code'] = declaration_code + ';\n\n' + result['code']

    elif isinstance(obj, ast.Assign):
        var_name = obj.targets[0].id
        var_value = convert_value(to_arduino(obj.value, terminate=terminate)['code'])
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
        return to_arduino(obj.value, result, terminate=terminate)

    elif isinstance(obj, ast.Call):
        func_name = to_arduino(obj.func, terminate=terminate)['code']

        if (func_name not in result['funcs']
            and not hasattr(ardlib, func_name)):

            # issue a warning if an undeclared function is used
            warn('''function {} (line {}) is undefined
If its definition occurs later, it will be prepended to the top'''.format(
                func_name,
                obj.lineno), UndeclaredFunctionWarning)

        if isinstance(obj.args[0], ast.Call):
            temp_result = result.copy()
            temp_result['code'] = ''
            to_arduino(obj.args, temp_result, terminate=False)
            args_code = temp_result['code'].lstrip()

        else:
            args_code = ''
            for n, arg in enumerate(obj.args):
                if n + 1 < len(obj.args):
                    args_code += str(to_arduino(arg, terminate=False)['code']).lstrip() + ', '
                else:
                    args_code += str(to_arduino(arg, terminate=False)['code']).lstrip()

        code = FUNC_CALL.format(indent=calc_indent(obj), name=func_name, args=args_code)
        result['code'] += code

    elif isinstance(obj, ast.Return):
        ret_value = to_arduino(obj.value, {'code': ''}, terminate=terminate)
        result['code'] += calc_indent(obj) + 'return ' + ret_value['code'].lstrip()

    elif isinstance(obj, ast.BinOp):
        left = to_arduino(obj.left, terminate=terminate)['code']
        right = to_arduino(obj.right, terminate=terminate)['code']
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

    # hackety hack
    result['code'] = str(result['code'])

    if terminate:
        if (result['code'].endswith('}')):
            result['code'] += '\n'
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

def make_make(sketchname):
    make = MAKE_STRUCTURE.format(
    sketch_folder=sketchname,
    port=args.port,
    board=args.board)

    with open('Makefile', 'w') as makefile:
        makefile.write(make)

def run_make(sketchname):
    subprocess.call(['make', '-C', sketchname])
    os.remove('Makefile')

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

    if args.compile:
        make_make(sketchname)
        run_make(sketchname)

if __name__ == '__main__':
    argp = ArgumentParser()
    argp.add_argument('file', type=str, help='file to parse')
    argp.add_argument('-w', action='store_true', default=False, 
        help='suppress warnings')

    # options for compilation
    argp.add_argument('-c', '--compile', action='store_true', 
        default=False, help='compile the script')
    argp.add_argument('-b', '--board', type=str, default='uno', 
        help='board type to compile for')
    argp.add_argument('-p', '--port', type=str,
        help='arduino serial port')
    argp.add_argument('-u', '--upload', action='store_true', default=False, 
        help='upload the script to the board (works only if -c or --compile is specified')
    args = argp.parse_args()

    if args.w:
        simplefilter('ignore')

    main()
