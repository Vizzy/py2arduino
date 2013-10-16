#!/usr/bin/env python3.3

import ast, os, subprocess
from inspect import signature
from argparse import ArgumentParser
from warnings import warn, simplefilter

import ardlib
import config

MESSAGE = '''/* 
 * This code has been auto-generated by pyduino from a Python-like source.
 * Please see https://github.com/Vizzy/pyduino for details.
 * (c) Anton Osten 
 */'''

VAR_NEW_UNASSIGNED = '{indent}{type} {name}'
VAR_NEW_ASSIGNED = '{indent}{name} = {value}'
LIST = '{indent}{type} {name}'
TUPLE = '{indent}{type} {name}({elts})'

AUG_ASSIGN = '{indent}{name} {op}= {value}'
FUNC_DEF = '{type} {name}({args})'
FUNC_CALL = '{indent}{name}({args})'
BOOL_OP = '{indent}{left} {op} {right}'
BIN_OP = '({left} {op} {right})'
CMPOP = '{left} {cmpop} {comparator}'
IF = '{indent}if ({test})'
WHILE = '{indent}while ({test})'

types = {
    'int': 'int',
    'float': 'float',
    'str': 'char',
    'bool': 'boolean',
    'None': 'void',
    'NoneType': 'void',
    '_empty': 'void'
}

# supported container types
container_types = (tuple, list)

funcs = {}

result_template = {
            'variables': {'global': {}},
            'funcs': funcs,
            'cur_scope': 'global',
            'code': ''
}

# add in types for library functions and constants
for attr in dir(ardlib):
    # somehow this is the only way to check if something's a function in Python
    live_attr = eval('ardlib.' + attr)
    if type(live_attr) is type(lambda x: x):
        func_name = attr
        func_type = signature(live_attr).return_annotation.__name__
        funcs[func_name] = types[func_type]
    else:
        # hack for library constants
        if not attr.startswith('__'):
            try:
                const_type = types[type(live_attr).__name__]
            except KeyError:
                continue
            result_template['variables']['global'][attr] = const_type


# MAKE_STRUCTURE = '''CODE_DIR = {sketch_folder}
# BOARD_TAG = {board}
# ARDUINO_PORT = {port}
# # CPPFLAGS = -std=c++11
# include $(ARDMK_DIR)/arduino-mk/Arduino.mk'''

class CompilationError(Exception):
    def __init__(self, message, line):
        self.message = message
        self.line = line

    def __str__(self):
        return '{} (line {})'.format(self.message, self.line)

class UnsupportedSyntaxError(CompilationError):
    pass

class ContainerTypeError(CompilationError):
    pass

class UndeclaredVariableError(CompilationError):
    pass

class UndeclaredFunctionWarning(Warning):
    pass

def unsupported_syntax(message, line):
    raise UnsupportedSyntaxError(message, line)

calc_indent = lambda obj: ' ' * obj.col_offset

def get_arduino_type(value):

    valtype = type(value)

    if valtype is str:
        # get rid of the quotes
        value = value.replace("'", '')
        value = value.replace('"', '')

        if len(value) is 1:
            return 'char'
        else:
            return 'char *'

    elif isinstance(valtype, container_types):
        container_elts_type = get_container_elts_type(value)
        if isinstance(valtype, list):
            container_type = 'List<{}>'.format(container_elts_type)
        elif isinstance(valtype, tuple):
            container_type = 'Tuple<{}>'.format(container_elts_type)
    try:
        return types[valtype.__name__]
    except KeyError:
        raise TypeError('Type {} is not yet supported'.format(
            valtype.__name__))

def get_variable_type(name_obj, result):
    '''Returns the type of an initialised variable
        from an ast.Name object
        or fails with an error if no such variable has been initialised'''

    cur_scope = result['cur_scope']
    var_name = name_obj.id

    try:
        var_type = result['variables'][cur_scope][var_name]
    except KeyError:
        try:
            var_type = result['variables']['global'][var_name]
        except KeyError:
            raise UndeclaredVariableError(
                'variable {} has not been declared'.format(var_name),
                name_obj.lineno)

    return var_type


def get_container_elts_type(container):
    if len(container) is 0:
        return None

    container_type = type(container[0])

    # check that all the elements are of the same type
    for elt in container:
        if type(elt) is not container_type:
            raise TypeError
    else:
        return get_arduino_type(container[0])


def get_binop_type(binop, result):
    '''This function takes an ast.BinOp object
    and the dictionary of processed code so far
    and will attempt to deduce the type of the result'''

    # division always results in a float
    if isinstance(binop.op, ast.Div):
        return 'float'

    sides = (binop.left, binop.right)


    for side in sides:
        # recurse through the binop
        if isinstance(side, ast.BinOp):
            return get_binop_type(side, result)
        # variables involved
        if isinstance(side, ast.Name):
            var = side.id
            var_type = result['variables'][result['cur_scope']].get(var)
            if var_type is None:
                var_type = result['variables']['global'].get(var)

            if var_type is None:
                raise UndeclaredVariableError(
                    'Variable {} has not been declared'.format(var),
                    side.lineno)
            
            elif var_type == 'float':
                return var_type
        # function calls involved
        if isinstance(side, ast.Call):
            func_name = side.func.id
            if result[funcs][func_name] == 'float':
                return 'float'
        # if it's a float, the whole thing's a float
        if isinstance(side, ast.Num):
            if type(side.n) is float:
                return 'float'

    # default to int
    return 'int'

def get_unaryop_type(unaryop, result):
    # if it's a variable
    if isinstance(unaryop.operand, ast.Name):
        var_name = unaryop.operand.id
        var_type = result['variables'][result['cur_scope']].get(var_name)
        if var_type is None:
            var_type = result['variables']['global'].get(var_name)

        if var_type is None:
            raise UndeclaredVariableError(
                'Variable {} has not been declared'.format(var_name),
                unaryop.lineno)
        else:
            return var_type
    else:
        return get_arduino_type(unaryop.operand.n)


def get_boolop(op):
    if isinstance(op, ast.And):
        return '&&'

    if isinstance(op, ast.Or):
        return '||'

def get_operator(op):
    if isinstance(op, ast.Add):
        return '+'

    if isinstance(op, ast.Sub):
        return '-'

    if isinstance(op, ast.Mult):
        return '*'

    if isinstance(op, ast.Div):
        return '/'

    if isinstance(op, ast.Mod):
        return '%'

    if isinstance(op, ast.Pow):
        return '^'

def get_unaryop(op):
    if isinstance(op, ast.Invert):
        return '~'

    if isinstance(op, ast.Not):
        return '!'

    if isinstance(op, ast.UAdd):
        return '+'

    if isinstance(op, ast.USub):
        return '-'

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

def get_func_returns(parsed):
    funcs = {}

    for obj in parsed.body:
        if isinstance(obj, ast.FunctionDef):
            func_name = obj.name

            if obj.returns is None:
                func_type = 'void'
            else:
                func_type = types[obj.returns.id]

            funcs[func_name] = func_type

    return funcs

def process_container(obj, varname, result):
    # create an actual live list
    elts = [eval(to_arduino(elt)['code']) for elt in obj.elts]
    indent = calc_indent(obj)

    if isinstance(obj, ast.List):
        container_type = get_arduino_type(elts)
        code = LIST.format(indent=indent,
            type=container_type, name=varname)

        for elt in elts:
            code += '{}.append({})\n'.format(calc_indent(obj),
                varname, str(elt))

    elif isinstance(obj, ast.Tuple):
        elts = tuple(elts)
        container_type = get_arduino_type(elts)

        # we first need to create a temporary C-style array
        # to construct a Tuple object from it

        arr = str(elts).replace('(', '{').replace(')', '}')
        arr_type = get_container_elts_type(elts)
        arr_name = 'temp_arr'
        arr_len = len(elts)
        arr_code = '{indent}{type} {name}{size} = {arr}\n'.format(
            indent=indent, type=arr_type, name='temp_arr',
            size=str(arr_len), arr=arr)

        tuple_code = '{indent}{type} {name}({arr})\n'.format(
            indent=indent, type=container_type, name=varname,
            arr=arr_name)

        code = arr_code + tuple_code

    else:
        raise CompilationError('Only lists and tuples supported',
            obj.lineno)

    return {'type': container_type, 'code': code}


# COMPILER/TRANSLATOR

def to_arduino(obj, result=None, newline=True):

    if result is None:
        result = result_template.copy()

    if obj == [] or obj is None:
        return result

    if isinstance(obj, list):
        to_arduino(obj[0], result, newline=newline)
        obj.pop(0)
        to_arduino(obj, result, newline=newline)

    elif isinstance(obj, ast.Name):
        return {'code': obj.id}

    elif isinstance(obj, ast.Num):
        return {'code': obj.n}

    elif isinstance(obj, ast.Module):
        result = to_arduino(obj.body, result, newline=newline)

    elif isinstance(obj, ast.FunctionDef):
        func_name = obj.name
        func_args = {}

        result['cur_scope'] = func_name
        result['variables'][func_name] = {}

        for arg in obj.args.args:
            arg_name = arg.arg
            arg_type = to_arduino(arg.annotation, newline=newline)['code']
            # convert the type to proper arduino type
            try:
                arg_type = types[arg_type]
            except KeyError:
                raise UnsupportedSyntaxError
            func_args[arg_name] = arg_type
            # arguments are local variables
            result['variables'][func_name][arg_name] = arg_type

        args_code = ''

        for n, arg in enumerate(func_args):
            if n + 1 < len(func_args):
                args_code += '{} {}, '.format(func_args[arg], arg)
            else:
                args_code += '{} {}'.format(func_args[arg], arg)

        # this is needed for variable declarations later
        # must be stored here because otherwise the body gets popped out
        indent = calc_indent(obj.body[0])

        temp_result = result.copy()
        temp_result['code'] = ''
        to_arduino(obj.body, temp_result, newline=newline)
        body_code = temp_result['code']

        # get function type
        # strong preference given to annotations
        if obj.returns is None:
            try:
                func_type = temp_result['funcs'][func_name]
            except KeyError:
                func_type = 'void'
        else:
            func_type = types[obj.returns.id]

        # declare all the local variables at the top
        # (important to ensure correct types)
        for var_name in temp_result['variables'][func_name]:
            if (var_name == 'DECLARED_GLOBALS' or 
                var_name in func_args):
                continue

            var_type = temp_result['variables'][func_name][var_name]

            var_declaration = VAR_NEW_UNASSIGNED.format(
                indent=indent, type=var_type, name=var_name)

            body_code = var_declaration + '\n' + body_code

        declaration_code = FUNC_DEF.format(type=func_type, name=func_name,
                                args=args_code)

        code = (declaration_code + ' {\n'
                 + body_code + '}\n')

        result['funcs'][func_name] = func_type
        result['code'] += code

        if func_name != 'setup' and func_name != 'loop':
            result['code'] = declaration_code + ';\n\n' + result['code']

        # set the scope back to global
        result['cur_scope'] = 'global'

    elif isinstance(obj, ast.Assign):
        var_name = obj.targets[0].id

        if isinstance(obj.value, (ast.List, ast.Tuple)):
            processed = process_container(obj.value, var_name, result)
            var_type = processed['type']
            code = processed['code']
        else:
            var_value = to_arduino(obj.value, newline=False)['code']

            if isinstance(obj.value, ast.Name):
                var_type = get_variable_type(obj.value, result)
            elif isinstance(obj.value, ast.Call):
                var_type = result['funcs'][obj.value.func.id]
            elif isinstance(obj.value, ast.BinOp):
                var_type = get_binop_type(obj.value, result)
            elif isinstance(obj.value, ast.UnaryOp):
                var_type = get_unaryop_type(obj.value, result)
            else:
                var_type = get_arduino_type(var_value)

            var_value = str(var_value).lstrip()

            cur_scope = result['cur_scope']

            code = VAR_NEW_ASSIGNED.format(indent=calc_indent(obj), name=var_name,
             value=var_value)

        # check if it's used as a local or as a global
        try:
            if var_name in result['variables'][cur_scope]['DECLARED_GLOBALS']:
                cur_scope = 'global'
        except KeyError:
            pass
        
        # update the type
        result['variables'][cur_scope][var_name] = var_type
        result['code'] += code

    elif isinstance(obj, ast.AugAssign):
        var_name = obj.target.id

        if isinstance(obj.value, ast.Num):
            var_type = get_arduino_type(obj.value.n)
        elif isinstance(obj.value, ast.Name):
            var_type = get_variable_type(obj.value, result)

        op = get_operator(obj.op)

        # if it's division, it's a float
        if op == '/':
            var_type = 'float'

        var_value = str(to_arduino(obj.value, newline=newline)['code'])

        code = AUG_ASSIGN.format(indent=calc_indent(obj), name=var_name, 
                                    op=op, value=var_value)

        # update the type
        cur_scope = result['cur_scope']
        try:    
            if var_name in result['variables'][cur_scope]['DECLARED_GLOBALS']:
                cur_scope = 'global'
        except KeyError:
            pass

        result['variables'][cur_scope][var_name] = var_type

        result['code'] += code

    elif isinstance(obj, ast.Expr):
        return to_arduino(obj.value, result, newline=newline)

    elif isinstance(obj, ast.Call):
        func_name = to_arduino(obj.func, newline=False)['code']

        if obj.args != []:
            if isinstance(obj.args[0], ast.Call):
                args_code = to_arduino(obj.args, newline=False)['code'].lstrip()

            else:
                args_code = ''
                for n, arg in enumerate(obj.args):
                    if n + 1 < len(obj.args):
                        args_code += str(to_arduino(arg,
                                         newline=False)['code']).lstrip() + ', '
                    else:
                        args_code += str(to_arduino(arg,
                                         newline=False)['code']).lstrip()
        else:
            args_code = ''

        code = FUNC_CALL.format(indent=calc_indent(obj), name=func_name, args=args_code)
        result['code'] += code

    elif isinstance(obj, ast.Attribute):
        class_name = to_arduino(obj.value,
         newline=False)['code'].lstrip()
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
        test_code = to_arduino(obj.test, newline=False)['code'].lstrip()
        temp_result = result.copy()
        temp_result['code'] = ''
        body_code = to_arduino(obj.body, temp_result)['code']
        try:
            orelse_code = to_arduino(obj.orelse[0])['code']
        except IndexError:
            orelse_code = to_arduino(obj.orelse)['code']

        if_code = (IF.format(indent=calc_indent(obj), test=test_code)
            + ' {\n' + body_code + 
            '{indent}}}\n'.format(indent=calc_indent(obj)))

        if len(obj.orelse) >= 1:
            if isinstance(obj.orelse[0], ast.If) and 'else if' not in orelse_code:
                orelse_code = orelse_code.replace('if', 'else if')
            else:
                orelse_code = '{indent}else {{\n{code}{indent}}}'.format(
                    indent=calc_indent(obj), code=orelse_code)

        code = if_code + orelse_code
        result['code'] += code

    elif isinstance(obj, ast.While):
        test_code = to_arduino(obj.test, newline=False)['code'].lstrip()
        body_code = to_arduino(obj.body)['code']
        try:
            orelse_code = to_arduino(obj.orelse[0])['code']

            # realign the indent
            orelse_code = orelse_code.split(calc_indent(obj.orelse[0]))[1]
        except IndexError:
            # there is no else case in the loop
            orelse_code = ''

        while_code = (WHILE.format(indent=calc_indent(obj), test=test_code)
                    + ' {\n' + body_code + 
                    '{indent}}}\n'.format(indent=calc_indent(obj)))

        code = while_code + orelse_code
        result['code'] += code

    elif isinstance(obj, ast.Return):
        ret_value = to_arduino(obj.value, newline=newline)
        # get its type for function type inference
        cur_scope = result['cur_scope']
        if isinstance(obj.value, ast.Name):
            ret_type = get_variable_type(obj.value, result)
        elif isinstance(obj.value, ast.Num):
            ret_type = get_arduino_type(obj.value.n)
        else:
            ret_type = 'void'
        result['funcs'][cur_scope] = ret_type
        result['code'] += calc_indent(obj) + 'return ' + str(ret_value['code']).lstrip()

    elif isinstance(obj, ast.BoolOp):
        op = get_boolop(obj.op)

        # left is the first element of obj.values
        left = to_arduino(obj.values[0], newline=newline)['code']

        # check if it's multiple boolean ops
        for value in obj.values:
            if not isinstance(value, ast.Name):
                multiop = True
            else:
                multiop = False

        # right is everything else (which we have to process recursively)
        if multiop:
            right = to_arduino(obj.values[1:], newline=newline)['code']
            code = BOOL_OP.format(indent=calc_indent(obj), left=left, right=right,
                                op=op)
        # SPECIAL CASE IF IT'S THE SAME OPERATOR
        # may Jah forgive me for this code
        else:
            right = [to_arduino(value, newline=False)['code'].strip()
                        for value in obj.values[1:]]
            right = (' ' + op + ' ').join(right)

        
        code = BOOL_OP.format(indent=calc_indent(obj), left=left, right=right,
                                op=op)

        result['code'] += code


    elif isinstance(obj, ast.BinOp):
        left = to_arduino(obj.left, newline=newline)['code']
        right = to_arduino(obj.right, newline=newline)['code']
        op = get_operator(obj.op)

        code = BIN_OP.format(indent=calc_indent(obj),
            left=left, right=right, op=op)
        result['code'] += code

    elif isinstance(obj, ast.UnaryOp):
        op = get_unaryop(obj.op)
        operand = to_arduino(obj.operand, result, newline=newline)['code']

        code = calc_indent(obj) + op + operand
        result['code'] += code

    elif isinstance(obj, ast.Compare):
        left = to_arduino(obj.left, newline=False)['code'].lstrip()
        
        if len(obj.ops) is 1:
            cmpop = get_cmpop(obj.ops[0])
        else:
            unsupported_syntax(
                'Comparisons with multiple operators are currently not supported',
                obj.lineno)

        if len(obj.comparators) is 1:
            comparator = str(to_arduino(obj.comparators[0],
             newline=False)['code']).lstrip()
        else:
            unsupported_syntax(
                'Comparisons with multiple operators are currently not supported',
                obj.lineno)

        code = CMPOP.format(left=left, cmpop=cmpop, comparator=comparator)
        result['code'] += code


    elif isinstance(obj, ast.Import):
        newline = False

        modules = obj.names

        for module in modules:
            filename = module.name + '.py'
            translated = translate(open(filename).read())
            write_translation(translated['code'], module.name, 'hpp')

        result['code'] = ('#include ' + module.name + '.hpp' + 
                            '\n' + result['code'])

    elif isinstance(obj, ast.Global):
        newline = False
        declared_globals = set(obj.names)
        cur_scope = result['cur_scope']
        result['variables'][cur_scope]['DECLARED_GLOBALS'] = declared_globals

    elif isinstance(obj, ast.Pass):
        pass

    elif isinstance(obj, ast.Break):
        result['code'] += calc_indent(obj) + 'break'

    elif isinstance(obj, ast.Continue):
        result['code'] += calc_indent(obj) + 'continue'

    else:
        raise UnsupportedSyntaxError('{} syntax is currently not supported'.format(
            type(obj).__name__), obj.lineno)

    # hackety hack
    result['code'] = str(result['code'])

    if newline:
        result['code'] += '\n'

    return result

def postprocess(result):
    code = result['code']

    code = code.replace('True', 'true')
    code = code.replace('False', 'false')

    # hack to support global variables
    global_declarations = ''
    for global_var in result['variables']['global']:
        # check that it's not a library constant
        if global_var not in dir(ardlib):
            var_type = result['variables']['global'][global_var]
            var_declaration = VAR_NEW_UNASSIGNED.format(
                indent='', type=var_type, name=global_var)
            global_declarations += var_declaration + '\n'
    code = global_declarations + code


    # add semicolons
    code = code.splitlines()
    code = [line.rstrip() for line in code]

    for n, line in enumerate(code):
        if (not (line.endswith('{') or line.endswith('}'))
            and not line.endswith(';') and len(line) > 0):
            line += ';\n'
        elif line.endswith('}'):
            line += '\n\n'
        elif len(line) > 0:
            line += '\n'
        code[n] = line

    code = ''.join(code)

    code = MESSAGE + '\n\n' + code

    return code

def translate(code):
    parsed = ast.parse(code)

    funcs = get_func_returns(parsed)
    result = result_template.copy()
    result['funcs'].update(funcs)

    to_arduino(parsed, result)

    result['code'] = postprocess(result)
    return result

def write_translation(translated, filename, extension='ino'):
    
    try:
        os.mkdir(sketchname)
    except OSError:
        pass

    if '/' in filename:
        filename = os.path.split(filename)[1]

    sketchpath = os.path.join(sketchname, (filename.split('.')[0] + '.' + extension))
    with open(sketchpath, 'w') as sketch:
        sketch.write(translated)

def run(sketchname, upload=False):
    if upload:
        run_flag = '--upload'
    else:
        run_flag = '--verify'

    sketchpath = os.path.join(sketchname, sketchname + '.ino')
    sketchpath = os.path.abspath(sketchpath)
    subprocess.call([config.arduino_path,
                    args.board,
                    args.port,
                    run_flag,
                    sketchpath])

def main():
    global sketchname

    sketchname = os.path.split(args.file)[1].split('.py')[0]

    sketchfile = open(args.file)
    translated = translate(sketchfile.read())

    write_translation(translated['code'], sketchname)

    if args.compile:
        run(sketchname)
    elif args.upload:
        run(sketchname, upload=True)

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
