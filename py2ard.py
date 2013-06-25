#!/usr/bin/env python3.3

import ast, os, subprocess
from inspect import signature
from argparse import ArgumentParser
from warnings import warn, simplefilter

import ardlib

VAR_NEW = '{indent}{type} {name} = {value}'
VAR_REDEFINED = '{indent}{name} = {value}'
FUNC_DEF = '{type} {name}({args})'
FUNC_CALL = '{indent}{name}({args})'
BIN_OP = '{indent}{left} {op} {right}'
CMPOP = '{left} {cmpop} {comparator}'
IF = '{indent}if ({test})'

types = {
    'int': 'int',
    'float': 'float',
    'str': 'string',
    'bool': 'boolean',
    'None': 'void',
    'NoneType': 'void',
    '_empty': 'void'
}

funcs = {}

for attr in dir(ardlib):
    # somehow this is the only way to check if something's a function in Python
    live_attr = eval('ardlib.' + attr)
    if type(live_attr) is type(lambda x: x):
        func_name = attr
        func_type = signature(live_attr).return_annotation.__name__
        funcs[func_name] = types[func_type]

result_template = {
    'var_names': {'global': set(), 'local': set()},
    'funcs': funcs,
    'code': ''
}

MAKE_STRUCTURE = '''CODE_DIR = {sketch_folder}
BOARD_TAG = {board}
ARDUINO_PORT = {port}
include $(ARDMK_DIR)/arduino-mk/Arduino.mk'''

class UnsupportedSyntaxError(Exception):
    def __init__(self, message, line):
        self.message = message
        self.line = line

    def __str__(self):
        return '{} (line {})'.format(self.message, self.line)

class UndeclaredFunctionWarning(Warning):
    pass

def unsupported_syntax(message, line):
    raise UnsupportedSyntaxError(message, line)

calc_indent = lambda obj: ' ' * obj.col_offset

def postprocess(code):
    code = code.replace('True', 'true')
    code = code.replace('False', 'false')

    return code


def get_type(value):
    valtype = type(value)

    if valtype is str:
        if len(value) is 1:
            return 'char'
        else:
            return 'string[{}]'.format(len(value))
    else:
        return types[valtype.__name__]

def get_operator(op):
    if isinstance(op, ast.Add):
        return '+'

    if isinstance(op, ast.Sub):
        return '-'

    if isinstance(op, ast.Mult):
        return '*'

    if isinstance(op, ast.Div):
        return '/'

def get_cmpop(op):
    # cmpop = Eq | NotEq | Lt | LtE | Gt | GtE | Is | IsNot | In | NotIn

    if isinstance(op, ast.Eq):
        return '=='

    if isinstance(op, ast.NotEq):
        return '!='

    if isinstance(op, ast.Lt):
        return '<'

    if isinstance(op, ast.LtE):
        return '<='

    if isinstance(op, ast.Gt):
        return '>'

    if isinstance(op, ast.GtE):
        return '>='

    if isinstance(op, ast.Is):
        return '=='

    if isinstance(op, ast.IsNot):
        return '!='

def to_arduino(obj, result={'code': ''}, terminate=True):

    if obj == [] or obj is None:
        return result

    if isinstance(obj, list):
        to_arduino(obj[0], result, terminate=terminate)
        obj.pop(0)
        to_arduino(obj, result, terminate=terminate)

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

        result['funcs'][func_name] = func_type
        result['var_names']['local'] = set()
        result['code'] += code

        if func_name != 'setup' and func_name != 'loop':
            result['code'] = declaration_code + ';\n\n' + result['code']

    elif isinstance(obj, ast.Assign):
        var_name = obj.targets[0].id
        var_value = to_arduino(obj.value, {'code': ''}, terminate=terminate)['code']

        if isinstance(obj.value, ast.Call):
            var_type = result['funcs'][var_value.split('(')[0].lstrip()]
        else:
            var_type = get_type(var_value)

        var_value = str(var_value).lstrip()

        scope = 'global' if obj.col_offset is 0 else 'local'

        if (var_name in result['var_names'][scope]
            or var_name in result['var_names']['global']):

            code = VAR_REDEFINED.format(indent=calc_indent(obj), name=var_name,
             value=var_value)
        else:
            code = VAR_NEW.format(indent=calc_indent(obj), type=var_type,
             name=var_name, 
                value=var_value)
            result['var_names']['local'].add(var_name)

        result['code'] += code

    elif isinstance(obj, ast.Expr):
        return to_arduino(obj.value, result, terminate=terminate)

    elif isinstance(obj, ast.Call):
        func_name = to_arduino(obj.func, {'code': ''}, terminate=False)['code']

        if isinstance(obj.args[0], ast.Call):
            args_code = to_arduino(obj.args, {'code': ''}, terminate=False)['code'].lstrip()

        else:
            args_code = ''
            for n, arg in enumerate(obj.args):
                if n + 1 < len(obj.args):
                    args_code += str(to_arduino(arg, terminate=False)['code']).lstrip() + ', '
                else:
                    args_code += str(to_arduino(arg, terminate=False)['code']).lstrip()

        code = FUNC_CALL.format(indent=calc_indent(obj), name=func_name, args=args_code)
        result['code'] += code

    elif isinstance(obj, ast.Attribute):
        class_name = to_arduino(obj.value, terminate=False)['code'].lstrip()
        attribute_name = obj.attr

        code = '{}.{}'.format(class_name, attribute_name)

        return {'code': code} 

    elif isinstance(obj, ast.Str):
        if len(obj.s) is 1:
            code = "'{}'".format(obj.s)
        else:
            code = '"{}"'.format(obj.s)
        return {'code': code}

    elif isinstance(obj, ast.If):
        test_code = to_arduino(obj.test, {'code': ''}, terminate=False)['code'].lstrip()
        body_code = to_arduino(obj.body, {'code': ''})['code']
        try:
            orelse_code = to_arduino(obj.orelse[0], {'code': ''})['code']
        except IndexError:
            orelse_code = to_arduino(obj.orelse, {'code': ''})['code']

        if_code = (IF.format(indent=calc_indent(obj), test=test_code)
            + '\n{}{{\n'.format(calc_indent(obj)) + body_code + 
            '{}}}\n'.format(calc_indent(obj)))

        if len(obj.orelse) >= 1:
            if isinstance(obj.orelse[0], ast.If) and 'else if' not in orelse_code:
                orelse_code = orelse_code.replace('if', 'else if')
            else:
                orelse_code = '{indent}else\n{indent}{{\n{indent}{code}{indent}}}'.format(
                    indent=calc_indent(obj), code=orelse_code)

        code = if_code + orelse_code
        result['code'] += code

    elif isinstance(obj, ast.Compare):
        left = to_arduino(obj.left, terminate=False)['code'].lstrip()
        
        if len(obj.ops) is 1:
            cmpop = get_cmpop(obj.ops[0])
        else:
            unsupported_syntax(
                'Comparisons with multiple operators are currently not supported',
                obj.lineno)

        if len(obj.comparators) is 1:
            comparator = str(to_arduino(obj.comparators[0], terminate=False)['code']).lstrip()
        else:
            unsupported_syntax(
                'Comparisons with multiple operators are currently not supported',
                obj.lineno)

        code = CMPOP.format(left=left, cmpop=cmpop, comparator=comparator)
        return {'code': code}

    elif isinstance(obj, ast.Return):
        ret_value = to_arduino(obj.value, {'code': ''}, terminate=terminate)
        result['code'] += calc_indent(obj) + 'return ' + ret_value['code'].lstrip()

    elif isinstance(obj, ast.BinOp):
        left = to_arduino(obj.left, terminate=terminate)['code']
        right = to_arduino(obj.right, terminate=terminate)['code']
        op = get_operator(obj.op)

        code = BIN_OP.format(indent=calc_indent(obj),
            left=left, right=right, op=op)
        result['code'] += code

    elif isinstance(obj, ast.Import):
        terminate = False

        modules = obj.names

        for module in modules:
            filename = module.name + '.py'
            write_translation(filename, 'h')

        result['code'] += '#include ' + module.name + '\n'

    elif isinstance(obj, ast.Pass):
        pass

    else:
        raise UnsupportedSyntaxError('{} syntax is currently not supported'.format(
            type(obj).__name__), obj.lineno)

    # hackety hack
    result['code'] = str(result['code'])

    if terminate:
        if (result['code'].endswith('}')):
            result['code'] += '\n'
        elif len(result['code'].rsplit('\n')[0]) > 0 and not result['code'].endswith('\n'):
            result['code'] += ';\n'

    if args.verbose:
        print(result['code'])

    return result

def translate(code):
    parsed = ast.parse(code)

    result = result_template.copy()

    to_arduino(parsed, result)

    result['code'] = postprocess(result['code'])
    return result

def make_make(sketchname):
    make = MAKE_STRUCTURE.format(
    sketch_folder=sketchname,
    port=args.port,
    board=args.board)

    with open(os.path.join(sketchname, 'Makefile'), 'w') as makefile:
        makefile.write(make)

def run_make(sketchname):
    if args.upload:
        subprocess.call(['make', 'upload', '-C', sketchname])
    else:
        subprocess.call(['make', '-C', sketchname])
    os.remove(os.path.join(sketchname, 'Makefile'))

def write_translation(filename, extension='ino'):
    file = open(filename)
    pycode = file.read()
    result = translate(pycode)
    
    try:
        os.mkdir(sketchname)
    except OSError:
        pass

    filename = filename.rsplit('/')[1]

    with open('{}/{}.{}'.format(sketchname, filename.split('.')[0], extension), 'w') as sketch:
        sketch.write(result['code'])

def main():
    global sketchname
    sketchname = args.file.split('.py')[0].rsplit('/')[1]

    write_translation(args.file)

    if args.compile:
        make_make(sketchname)
        run_make(sketchname)

if __name__ == '__main__':
    argp = ArgumentParser()
    argp.add_argument('file', type=str, help='file to parse')
    argp.add_argument('-v', '--verbose', action='store_true', default=False,
     help='verbose mode')
    argp.add_argument('-w', action='store_true', default=False, 
        help='suppress warnings')

    # options for compilation
    argp.add_argument('-c', '--compile', action='store_true', 
        default=False, help='compile the script')
    argp.add_argument('-b', '--board', type=str, default='uno', 
        help='board type to compile for')
    argp.add_argument('-p', '--port', default='/dev/ttyusb', type=str,
        help='arduino serial port')
    argp.add_argument('-u', '--upload', action='store_true', default=False, 
        help='upload the script to the board (works only if -c or --compile is specified')
    args = argp.parse_args()

    if args.w:
        simplefilter('ignore')

    main()
