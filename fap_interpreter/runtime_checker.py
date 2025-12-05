import sys
import re
import math
import copy
from typing import Set, Any, List, Optional, Dict
from lark import Token
from lark.exceptions import UnexpectedInput

class RuntimeChecker:
    def __init__(self):
        from fap_interpreter.parser import create_fap_parser
        from fap_interpreter.environment import Environment
        
        self.parser = create_fap_parser()
        self.env = Environment()
        self.env.define_var("out", {
            "Info": "out.Info",
            "Warn": "out.Warn", 
            "Error": "out.Error"
        })
        self.env.define_var("rep", {
            "stop": "rep.stop"
        })
        self.env.define_var("now", {
            "repeat": "now.repeat"
        })
        self.env.define_var("back", {
            "value": "back.value"
        })
        self.used_variables: Set[str] = set()
        self.defined_vars: Set[str] = set()
        self.assigned_vars: Set[str] = set()
        self.warned_vars: Set[str] = set()
        self.errors = []
        self.error_vars_list = []
        self.has_output = False
        self.debug_mode = False
        self.debug_plus_mode = False
        self.original_lines = []
        self.current_line_num = 0
        self.debug_output = []
        self.should_break = False
        self.return_value = None
        self.should_return = False

    def set_debug_mode(self, debug_mode: bool, debug_plus_mode: bool, original_lines: List[str]):
        self.debug_mode = debug_mode
        self.debug_plus_mode = debug_plus_mode
        self.original_lines = original_lines
        self.env.set_debug_mode(debug_mode, debug_plus_mode)

    def _add_debug_output(self, line_num: int, message: str):
        if not self.debug_plus_mode:
            return
            
        if line_num <= 0 or line_num > len(self.original_lines):
            return
            
        line_content = self.original_lines[line_num - 1].rstrip()
        debug_line = f"\033[33m[Line {line_num}: {line_content}] {message}\033[0m"
        self.debug_output.append(debug_line)

    def _add_method_call(self, line_num: int, method_name: str):
        if not self.debug_plus_mode:
            return
            
        if line_num <= 0 or line_num > len(self.original_lines):
            return
            
        line_content = self.original_lines[line_num - 1].rstrip()
        method_line = f"\033[38;2;255;165;0m[Line {line_num}: {line_content}] [METHOD CALL] {method_name}()\033[0m"
        self.debug_output.append(method_line)

    def execute(self, code: str) -> None:
        try:
            self.debug_output = []
            self._add_debug_output(0, "[RUNTIME] Starting execution")
            self._add_method_call(0, "RuntimeChecker.execute")
                
            if self.debug_mode or self.debug_plus_mode:
                print(f"\033[95m[DEBUG] Parsing code...\033[0m")
            ast = self.parser.parse(code)
            if ast is None:
                if self.debug_mode or self.debug_plus_mode:
                    print(f"\033[95m[DEBUG] Parser returned None\033[0m")
                return
            if self.debug_mode or self.debug_plus_mode:
                print(f"\033[95m[DEBUG] Parser successful, AST has {len(ast.children)} children\033[0m")
            
            self.collect_defined_vars(ast)
            if self.debug_mode or self.debug_plus_mode:
                print(f"\033[95m[DEBUG] Starting to visit {len(ast.children)} statements\033[0m")
            
            self.current_line_num = 1
            
            for i, stmt in enumerate(ast.children):
                try:
                    if hasattr(stmt, 'meta') and hasattr(stmt.meta, 'line'):
                        self.current_line_num = stmt.meta.line
                    else:
                        self.current_line_num = i + 1
                    
                    if self.debug_plus_mode:
                        print(f"\033[95m[DEBUG] Visiting statement {i+1} at line {self.current_line_num}\033[0m")
                    self.visit(stmt)
                except Exception as e:
                    error_msg = str(e)
                    if not any(marker in error_msg for marker in ['Tree(', 'Token(', 'visit_']):
                        self._add_error(error_msg, self.current_line_num)
                    else:
                        if self.debug_mode or self.debug_plus_mode:
                            print(f"\033[95m[DEBUG] Internal error in statement {i+1}: {e}\033[0m")
            
            self.check_unused_vars()
            
            for debug_line in self.debug_output:
                print(debug_line)
            
        except Exception as e:
            error_msg = str(e)
            if self.debug_mode or self.debug_plus_mode:
                print(f"\033[95m[DEBUG] Global runtime error: {e}\033[0m")
            if not any(marker in error_msg for marker in ['Tree(', 'Token(', 'visit_']):
                self._add_error(error_msg, self.current_line_num)

    def _add_error(self, error_msg: str, line_num: int = 0):
        if self.debug_plus_mode:
            line_content = self.original_lines[line_num - 1].rstrip() if 0 < line_num <= len(self.original_lines) else ""
            full_error_msg = f"\033[33m[Line {line_num}: {line_content}]\033[0m \033[91m[ERROR] {error_msg}\033[0m"
        elif self.debug_mode:
            full_error_msg = f"\033[33m[Line {line_num}]\033[0m \033[91m[ERROR] {error_msg}\033[0m"
        else:
            full_error_msg = f"\033[91m[ERROR] {error_msg}\033[0m"
            
        if full_error_msg not in self.errors:
            self.errors.append(full_error_msg)

    def collect_defined_vars(self, node):
        if hasattr(node, 'data'):
            if node.data == 'var_def':
                var_name_token = node.children[1]
                if isinstance(var_name_token, Token) and var_name_token.type == 'IDENT':
                    var_name = var_name_token.value
                    if var_name not in self.error_vars_list:
                        self.defined_vars.add(var_name)
                        self._add_debug_output(self.current_line_num, f"[RUNTIME] Defined variable: {var_name}")
            elif node.data == 'const_def':
                const_name_token = node.children[1]
                if isinstance(const_name_token, Token) and const_name_token.type == 'IDENT':
                    const_name = const_name_token.value
                    if const_name not in self.error_vars_list:
                        self.defined_vars.add(const_name)
                        self._add_debug_output(self.current_line_num, f"[RUNTIME] Defined constant: {const_name}")
            elif node.data == 'list_def':
                list_name_token = node.children[0]
                if isinstance(list_name_token, Token) and list_name_token.type == 'IDENT':
                    list_name = list_name_token.value
                    if list_name not in self.error_vars_list:
                        self.defined_vars.add(list_name)
                        self._add_debug_output(self.current_line_num, f"[RUNTIME] Defined list: {list_name}")
            elif node.data == 'assignment':
                var_name_token = node.children[0]
                if isinstance(var_name_token, Token) and var_name_token.type == 'IDENT':
                    var_name = var_name_token.value
                    if var_name not in self.error_vars_list:
                        self.defined_vars.add(var_name)
                        self._add_debug_output(self.current_line_num, f"[RUNTIME] Defined variable via assignment: {var_name}")
            elif node.data == 'func_def':
                func_name_token = node.children[0]
                if isinstance(func_name_token, Token) and func_name_token.type == 'IDENT':
                    func_name = func_name_token.value
                    if func_name not in self.error_vars_list:
                        self.defined_vars.add(func_name)
                        self._add_debug_output(self.current_line_num, f"[RUNTIME] Defined function: {func_name}")
            elif node.data == 'cause_stmt':
                block_node = node.children[1]
                if hasattr(block_node, 'data') and block_node.data == 'block':
                    for stmt in block_node.children:
                        if hasattr(stmt, 'data') and stmt.data in ['var_def', 'const_def', 'list_def', 'assignment', 'output_stmt', 'cause_stmt', 'input_call', 'again_stmt', 'list_method_call', 'func_def', 'func_call_stmt', 'back_stmt']:
                            self.collect_defined_vars(stmt)
                if len(node.children) > 2 and node.children[2].data == 'block':
                    or_block = node.children[2]
                    for stmt in or_block.children:
                        if hasattr(stmt, 'data') and stmt.data in ['var_def', 'const_def', 'list_def', 'assignment', 'output_stmt', 'cause_stmt', 'input_call', 'again_stmt', 'list_method_call', 'func_def', 'func_call_stmt', 'back_stmt']:
                            self.collect_defined_vars(stmt)
            elif node.data == 'again_stmt':
                block_node = node.children[2] if len(node.children) > 2 else node.children[1]
                if hasattr(block_node, 'data') and block_node.data == 'block':
                    for stmt in block_node.children:
                        if hasattr(stmt, 'data') and stmt.data in ['var_def', 'const_def', 'list_def', 'assignment', 'output_stmt', 'cause_stmt', 'input_call', 'again_stmt', 'list_method_call', 'func_def', 'func_call_stmt', 'back_stmt']:
                            self.collect_defined_vars(stmt)
            
            for child in node.children:
                if hasattr(child, 'data'):
                    self.collect_defined_vars(child)

    def visit(self, node) -> Any:
        try:
            if isinstance(node, Token):
                return self.visit_token(node)
            elif hasattr(node, 'data'):
                method_name = f'visit_{node.data}'
                method = getattr(self, method_name, self.visit_unknown)
                self._add_method_call(self.current_line_num, f"RuntimeChecker.{method_name}")
                result = method(node)
                if self.debug_plus_mode:
                    node_type = node.data if hasattr(node, 'data') else str(type(node))
                    self._add_debug_output(self.current_line_num, f"[RUNTIME] Visited {node_type} -> {result}")
                return result
            else:
                return node
        except Exception as e:
            error_msg = str(e)
            if not any(marker in error_msg for marker in ['Tree(', 'Token(', 'visit_']):
                raise e
            else:
                raise Exception("Invalid statement")

    def visit_token(self, token: Token) -> Any:
        method_name = f'visit_{token.type}'
        method = getattr(self, method_name, self.visit_unknown_token)
        self._add_method_call(self.current_line_num, f"RuntimeChecker.{method_name}")
        result = method(token)
        if self.debug_plus_mode:
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Visited token {token.type} '{token.value}' -> {result}")
        return result

    def visit_start(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_start")
        for child in node.children:
            self.visit(child)

    def visit_statement(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_statement")
        if node.children:
            self.visit(node.children[0])

    def visit_func_def(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_func_def")
        
        if len(node.children) < 3:
            self._add_error("Invalid function definition")
            return
            
        func_name_token = node.children[0]
        params_node = node.children[1]
        block_node = node.children[2]
        
        if isinstance(func_name_token, Token):
            func_name = func_name_token.value
        else:
            func_name = self.visit(func_name_token)
        
        if func_name in self.error_vars_list:
            return

        if self.env.is_defined(func_name):
            self._add_error(f"Function '{func_name}' is already defined")
            self.error_vars_list.append(func_name)
            return
            
        params = []
        if hasattr(params_node, 'data') and params_node.data == 'params':
            for param_node in params_node.children:
                if hasattr(param_node, 'data') and param_node.data == 'param':
                    if hasattr(param_node, 'children') and len(param_node.children) >= 2:
                        type_node = param_node.children[0]
                        name_token = param_node.children[1]
                        
                        # 获取类型名称
                        if hasattr(type_node, 'data'):
                            if type_node.data == 'type_int':
                                param_type = 'int'
                            elif type_node.data == 'type_float':
                                param_type = 'float'
                            elif type_node.data == 'type_str':
                                param_type = 'str'
                            else:
                                param_type = 'int'  # 默认类型
                        else:
                            param_type = 'int'  # 默认类型
                        
                        if isinstance(name_token, Token):
                            param_name = name_token.value
                            params.append({
                                'name': param_name,
                                'type': param_type
                            })
        
        self.env.define_func(func_name, params, block_node, self.env)
        self.defined_vars.add(func_name)
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Defined function {func_name} with typed params {params}")

    def visit_func_params(self, node) -> List[Dict]:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_func_params")
        params = []
        for child in node.children:
            if hasattr(child, 'data') and child.data == 'type_and_name':
                if len(child.children) >= 2:
                    type_token = child.children[0]
                    name_token = child.children[1]
                    if isinstance(type_token, Token) and isinstance(name_token, Token):
                        params.append({
                            'name': name_token.value,
                            'type': type_token.value
                        })
                elif child.children:
                    token = child.children[0]
                    if isinstance(token, Token) and token.type == 'IDENT':
                        params.append({
                            'name': token.value,
                            'type': 'int'
                        })
        return params

    def visit_func_call_stmt(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_func_call_stmt")
        self.visit_func_call(node)

    def visit_func_call(self, node) -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_func_call")
        
        func_name_token = node.children[0]
        if isinstance(func_name_token, Token):
            func_name = func_name_token.value
        else:
            func_name = self.visit(func_name_token)
        
        self.used_variables.add(func_name)
        
        if func_name in self.error_vars_list:
            return None
            
        if not self.env.is_function(func_name):
            self._add_error(f"Function '{func_name}' is not defined")
            self.error_vars_list.append(func_name)
            return None
            
        func_info = self.env.get_func(func_name)
        if not func_info:
            self._add_error(f"Function '{func_name}' not found")
            return None
            
        args = []
        if len(node.children) > 1:
            args_node = node.children[1]
            if hasattr(args_node, 'data') and args_node.data == 'func_args':
                if hasattr(args_node, 'children'):
                    for arg_node in args_node.children:
                        arg_value = self.visit(arg_node)
                        args.append(arg_value)
            else:
                for i in range(1, len(node.children)):
                    arg_node = node.children[i]
                    arg_value = self.visit(arg_node)
                    args.append(arg_value)
        
        func_params = func_info['params']
        expected_params = [p['name'] for p in func_params]
        param_types = {p['name']: p['type'] for p in func_params}
        
        if len(args) != len(expected_params):
            self._add_error(f"Function '{func_name}' expects {len(expected_params)} arguments but got {len(args)}")
            return None
        
        casted_args = []
        for i, (param_name, arg_value) in enumerate(zip(expected_params, args)):
            param_type = param_types[param_name]
            casted_arg = self.cast_type(arg_value, param_type, f"{func_name} argument {i+1}")
            if casted_arg is None:
                self._add_error(f"Argument {i+1} of function '{func_name}' cannot be cast to type '{param_type}'")
                return None
            casted_args.append(casted_arg)
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Calling function {func_name} with args {casted_args}")
        
        func_env = func_info['env'].create_child_env()
        
        for param_name, arg_value in zip(expected_params, casted_args):
            func_env.define_var(param_name, arg_value)
        
        old_env = self.env
        old_return_value = self.return_value
        old_should_return = self.should_return
        
        self.env = func_env
        self.return_value = None
        self.should_return = False
        
        try:
            self.visit(func_info['body'])
            
            result = self.return_value
            self.env = old_env
            self.return_value = old_return_value
            self.should_return = old_should_return
            
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Function {func_name} returned: {result}")
            return result
            
        except Exception as e:
            self.env = old_env
            self.return_value = old_return_value
            self.should_return = old_should_return
            raise e

    def visit_back_stmt(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_back_stmt")
        
        if len(node.children) > 0:
            expr_node = node.children[0]
            return_value = self.visit(expr_node)
            self.return_value = return_value
        else:
            self.return_value = None
            
        self.should_return = True
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Return statement with value: {self.return_value}")

    def visit_func_params(self, node) -> List[Dict]:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_func_params")
        params = []
        for child in node.children:
            if hasattr(child, 'data') and child.data == 'type_and_name':
                type_token = child.children[0]
                name_token = child.children[1]
                if isinstance(type_token, Token) and isinstance(name_token, Token):
                    params.append({
                        'name': name_token.value,
                        'type': type_token.value
                    })
        return params

    def visit_func_args(self, node) -> List[Any]:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_func_args")
        args = []
        for child in node.children:
            arg_value = self.visit(child)
            args.append(arg_value)
        return args

    def visit_block(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_block")
        if hasattr(node, 'data') and node.data == 'block':
            for stmt in node.children:
                if hasattr(stmt, 'data') and stmt.data == 'statement':
                    if self.should_return or self.should_break:
                        break
                    self.visit(stmt)

    def visit_factor(self, node) -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_factor")
        if len(node.children) == 1:
            child = node.children[0]
            if hasattr(child, 'data'):
                if child.data == 'math_func_call':
                    return self.visit_math_func_call(child)
                elif child.data == 'input_call':
                    return self.visit_input_call_as_expr(child)
                elif child.data == 'member_access_expr':
                    return self.visit_member_access_expr(child)
                elif child.data == 'list_literal':
                    return self.visit_list_literal(child)
                elif child.data == 'list_access':
                    return self.visit_list_access(child)
                elif child.data == 'abs_expr':
                    return self.visit_abs_expr(child)
                elif child.data == 'func_call':
                    return self.visit_func_call(child)
            return self.visit(child)
        else:
            return self.visit(node.children[1])

    def visit_math_func_call(self, node) -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_math_func_call")
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Math function call node has {len(node.children)} children")
        
        if not node.children:
            self._add_error("Math function call missing function name")
            return 0
            
        func_name_node = node.children[0]
        
        if isinstance(func_name_node, Token):
            func_name = func_name_node.value
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Function name: {func_name}")
            
            self.used_variables.add(func_name)
            
            if func_name in ['squFor', 'rootFor', 'd.root', 't.root']:
                if func_name == 'squFor':
                    return self._handle_squFor(node)
                elif func_name == 'rootFor':
                    return self._handle_rootFor(node)
                elif func_name == 'd.root':
                    return self._handle_d_root(node)
                elif func_name == 't.root':
                    return self._handle_t_root(node)
                else:
                    self._add_error(f"Unknown math function: {func_name}")
                    return 0
            else:
                return self.visit_func_call(node)
        else:
            self._add_error("Invalid math function call syntax")
            return 0

    def _handle_squFor(self, node) -> Any:
        self._add_debug_output(self.current_line_num, "[RUNTIME] Handling squFor function")
        
        if len(node.children) < 3:
            self._add_error("squFor function requires two arguments: base and exponent")
            return 0
            
        base_expr = node.children[1]
        exponent_expr = node.children[2]
        
        base = self.visit(base_expr)
        exponent = self.visit(exponent_expr)
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] squFor arguments: base={base}, exponent={exponent}")
        
        if base is None or exponent is None:
            self._add_error("squFor function arguments cannot be None")
            return 0
            
        if not isinstance(base, (int, float)) or not isinstance(exponent, (int, float)):
            self._add_error("squFor function requires numeric arguments")
            return 0
            
        try:
            result = base ** exponent
            self._add_debug_output(self.current_line_num, f"[RUNTIME] squFor result: {base}^{exponent} = {result}")
            
            if isinstance(result, float) and result.is_integer():
                return int(result)
            return result
        except Exception as e:
            self._add_error(f"Power calculation error: {e}")
            return 0

    def _handle_rootFor(self, node) -> Any:
        self._add_debug_output(self.current_line_num, "[RUNTIME] Handling rootFor function")
        
        if len(node.children) < 3:
            self._add_error("rootFor function requires two arguments: value and root_type")
            return 0
            
        value_expr = node.children[1]
        root_type_expr = node.children[2]
        
        value = self.visit(value_expr)
        root_type = self.visit(root_type_expr)
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] rootFor arguments: value={value}, root_type={root_type}")
        
        if value is None or root_type is None:
            self._add_error("rootFor function arguments cannot be None")
            return 0
            
        if not isinstance(root_type, (int, float)):
            try:
                root_type = int(root_type)
            except (ValueError, TypeError):
                self._add_error(f"Root type must be a number, got: {root_type}")
                return 0
        
        if root_type == 2:
            if value < 0:
                self._add_error("Cannot calculate square root of negative number")
                return 0
            result = math.sqrt(value)
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Square root of {value} = {result}")
            return int(result) if result.is_integer() else result
        elif root_type == 3:
            result = value ** (1/3)
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Cube root of {value} = {result}")
            return int(result) if result.is_integer() else result
        else:
            self._add_error(f"Unsupported root type: {root_type}. Use 2 for square root or 3 for cube root.")
            return 0

    def _handle_d_root(self, node) -> Any:
        self._add_debug_output(self.current_line_num, "[RUNTIME] Handling d.root function")
        
        if len(node.children) < 2:
            self._add_error("d.root function requires one argument")
            return 0
            
        value_expr = node.children[1]
        value = self.visit(value_expr)
        
        if value is None:
            self._add_error("d.root function argument cannot be None")
            return 0
            
        if value < 0:
            self._add_error("Cannot calculate square root of negative number")
            return 0
            
        result = math.sqrt(value)
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Square root of {value} = {result}")
        return int(result) if result.is_integer() else result

    def _handle_t_root(self, node) -> Any:
        self._add_debug_output(self.current_line_num, "[RUNTIME] Handling t.root function")
        
        if len(node.children) < 2:
            self._add_error("t.root function requires one argument")
            return 0
            
        value_expr = node.children[1]
        value = self.visit(value_expr)
        
        if value is None:
            self._add_error("t.root function argument cannot be None")
            return 0
            
        result = value ** (1/3)
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Cube root of {value} = {result}")
        return int(result) if result.is_integer() else result

    def visit_abs_expr(self, node) -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_abs_expr")
        
        if len(node.children) < 1:
            self._add_error("Absolute value expression missing inner expression")
            return 0
            
        inner_expr = node.children[0]
        value = self.visit(inner_expr)
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Absolute value of {value}")
        
        if value is None:
            self._add_error("Absolute value expression cannot have None value")
            return 0
            
        if not isinstance(value, (int, float)):
            self._add_error(f"Absolute value requires numeric argument, got {type(value).__name__}")
            return 0
            
        result = abs(value)
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Absolute value result: |{value}| = {result}")
        return result

    def visit_member_access(self, node) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_member_access")
        obj_token = node.children[0]
        attr_token = node.children[1]
        
        obj_name = obj_token.value
        attr_name = attr_token.value
        
        if not self.env.is_defined(obj_name):
            self._add_error(f"Object '{obj_name}' is not defined")
            return ""
        
        obj = self.env.get_value(obj_name)
        
        if attr_name not in obj:
            self._add_error(f"Object '{obj_name}' has no member '{attr_name}'")
            return ""
        
        return f"{obj_name}.{attr_name}"

    def visit_output_args(self, node) -> list:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_output_args")
        args = []
        for child in node.children:
            if child is None:
                self._add_error("Invalid argument in output function: empty argument")
                return []
            arg_value = self.visit(child)
            if arg_value is None:
                self._add_error("Invalid argument in output function")
                return []
            
            if isinstance(arg_value, list):
                arg_value = str(arg_value)
                
            args.append(arg_value)
        return args

    def visit_expr(self, node) -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_expr")
        if len(node.children) == 1:
            return self.visit(node.children[0])
        else:
            left = self.visit(node.children[0])
            for i in range(1, len(node.children), 2):
                op = self.visit(node.children[i])
                right = self.visit(node.children[i+1])
                if op == '+':
                    if isinstance(left, str) or isinstance(right, str):
                        left = str(left) + str(right)
                    else:
                        left = left + right
                elif op == '-':
                    left = left - right
                elif op == '*':
                    left = left * right
                elif op == '/':
                    if right == 0:
                        self._add_error("Division by zero")
                        return 0
                    left = left / right
            return left

    def visit_term(self, node) -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_term")
        if len(node.children) == 1:
            return self.visit(node.children[0])
        else:
            left = self.visit(node.children[0])
            for i in range(1, len(node.children), 2):
                op = self.visit(node.children[i])
                right = self.visit(node.children[i+1])
                if op == '*':
                    left = left * right
                elif op == '/':
                    if right == 0:
                        self._add_error("Division by zero")
                        return 0
                    left = left / right
            return left

    def visit_type_name(self, node) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_type_name")
        if hasattr(node, 'data'):
            if node.data == 'type_int':
                return 'int'
            elif node.data == 'type_float':
                return 'float'
            elif node.data == 'type_str':
                return 'str'
        return 'int'

    def visit_STRING(self, token: Token) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_STRING")
        return token.value[1:-1]

    def visit_NUMBER(self, token: Token) -> int | float:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_NUMBER")
        return float(token.value) if '.' in token.value else int(token.value)

    def visit_IDENT(self, token: Token) -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_IDENT")
        var_name = token.value
        self.used_variables.add(var_name)
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Variable access: {var_name}")
        
        if not self.env.is_defined(var_name):
            self._add_error(f"Variable '{var_name}' not defined")
            if var_name not in self.error_vars_list:
                self.error_vars_list.append(var_name)
            return None
        
        value = self.env.get_value(var_name)
        
        if (var_name in self.defined_vars and 
            var_name not in self.assigned_vars and 
            not self.env.is_constant(var_name) and
            var_name not in self.warned_vars and
            var_name not in self.error_vars_list):
            warning_msg = f"Variable '{var_name}' used without assignment, using default value: {value}"
            if self.debug_mode or self.debug_plus_mode:
                self._add_debug_output(self.current_line_num, f"[WARN] {warning_msg}")
            else:
                print(f"\033[93m[WARN] {warning_msg}\033[0m", file=sys.stderr)
            self.warned_vars.add(var_name)
        
        return value

    def visit_TYPE(self, token: Token) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_TYPE")
        return token.value

    def visit_COMPARISON_OP(self, token: Token) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_COMPARISON_OP")
        return token.value

    def visit_ADD_OP(self, token: Token) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_ADD_OP")
        return token.value

    def visit_MUL_OP(self, token: Token) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_MUL_OP")
        return token.value

    def visit_LOGIC_OP(self, token: Token) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_LOGIC_OP")
        return token.value

    def cast_type(self, value: Any, type_name: str, var_name: str = "") -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.cast_type")
        if var_name and var_name in self.error_vars_list:
            return None
            
        try:
            if type_name == 'int':
                if isinstance(value, str):
                    if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
                        return int(value)
                    else:
                        raise ValueError(f"String '{value}' cannot be converted to int")
                elif isinstance(value, float):
                    if value.is_integer():
                        return int(value)
                    else:
                        raise ValueError(f"Float '{value}' cannot be converted to int without loss of precision")
                return int(value)
            elif type_name == 'float':
                if isinstance(value, str):
                    try:
                        return float(value)
                    except ValueError:
                        raise ValueError(f"String '{value}' cannot be converted to float")
                return float(value)
            elif type_name == 'str':
                return str(value)
            else:
                error_msg = f"Unsupported type: '{type_name}'" + (f" for variable '{var_name}'" if var_name else "")
                self._add_error(error_msg)
                if var_name:
                    self.error_vars_list.append(var_name)
                return None
        except (ValueError, TypeError) as e:
            error_msg = f"Cannot cast '{value}' to type '{type_name}'" + (f" for variable '{var_name}'" if var_name else "")
            if str(e):
                error_msg += f" - {e}"
            self._add_error(error_msg)
            if var_name:
                self.error_vars_list.append(var_name)
            return None

    def check_unused_vars(self) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.check_unused_vars")
        unused = self.defined_vars - self.used_variables
        for var in unused:
            if var not in self.error_vars_list:
                warning_msg = f"'{var}' is defined but not used"
                if self.debug_mode or self.debug_plus_mode:
                    self._add_debug_output(self.current_line_num, f"[WARN] {warning_msg}")
                else:
                    print(f"\033[93m[WARN] {warning_msg}\033[0m", file=sys.stderr)

    def visit_unknown(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_unknown")
        node_type = node.data if hasattr(node, 'data') else str(type(node))
        if node_type not in ['start', 'condition', 'type_name', 'math_func', 'conditions', 'list_method', 'func_params', 'func_args']:
            self._add_error(f"Unknown statement type: {node_type}")

    def visit_unknown_token(self, token: Token) -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_unknown_token")
        return token.value

    def visit_list_def(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_list_def")
        list_name_token = node.children[0]
        list_literal_node = node.children[1]
        
        if isinstance(list_name_token, Token):
            list_name = list_name_token.value
        else:
            list_name = self.visit(list_name_token)
        
        if list_name in self.error_vars_list:
            return

        if self.env.is_defined(list_name):
            self._add_error(f"List '{list_name}' is already defined")
            self.error_vars_list.append(list_name)
            return
            
        list_value = self.visit(list_literal_node)
        self.env.define_var(list_name, list_value)
        self.defined_vars.add(list_name)
        self.assigned_vars.add(list_name)
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Defined list {list_name} = {list_value}")

    def visit_list_literal(self, node) -> list:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_list_literal")
        elements = []
        for child in node.children:
            element = self.visit(child)
            elements.append(element)
        return elements

    def visit_list_method_call(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_list_method_call")
        
        method_name = ""
        if 0 < self.current_line_num <= len(self.original_lines):
            line_content = self.original_lines[self.current_line_num - 1].strip()
            if '.add(' in line_content:
                method_name = 'add'
            elif '.clear(' in line_content:
                method_name = 'clear'
        
        if not method_name:
            self._add_error(f"Invalid list method call: could not extract method name")
            return
            
        list_name_token = node.children[0]
        if isinstance(list_name_token, Token):
            list_name = list_name_token.value
        else:
            list_name = self.visit(list_name_token)
            
        if list_name in self.error_vars_list:
            return
            
        if not self.env.is_defined(list_name):
            self._add_error(f"List '{list_name}' is not defined")
            self.error_vars_list.append(list_name)
            return
            
        current_list = self.env.get_value(list_name)
        if not isinstance(current_list, list):
            self._add_error(f"'{list_name}' is not a list")
            return
            
        if method_name == 'add':
            if len(node.children) < 3:
                self._add_error(f"List.add method requires an element to add")
                return
                
            element_node = node.children[2]
            element = self.visit(element_node)
            
            current_list.append(element)
            self.env.set_value(list_name, current_list)
            self.assigned_vars.add(list_name)
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Added element {element} to list {list_name}")
            
        elif method_name == 'clear':
            if len(node.children) > 2:
                self._add_error(f"List.clear method should not have arguments")
                return
                
            current_list.clear()
            self.env.set_value(list_name, current_list)
            self.assigned_vars.add(list_name)
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Cleared list {list_name}")
        else:
            self._add_error(f"Unknown list method: '{method_name}'")

    def visit_list_method(self, node) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_list_method")
        if node.children:
            for child in node.children:
                if isinstance(child, Token):
                    return child.value.lower()
        return ""

    def visit_list_access(self, node) -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_list_access")
        list_name_token = node.children[0]
        index_node = node.children[1]
        
        if isinstance(list_name_token, Token):
            list_name = list_name_token.value
        else:
            list_name = self.visit(list_name_token)
            
        index = self.visit(index_node)
        
        if list_name in self.error_vars_list:
            return None
            
        if not self.env.is_defined(list_name):
            self._add_error(f"List '{list_name}' is not defined")
            self.error_vars_list.append(list_name)
            return None
            
        current_list = self.env.get_value(list_name)
        if not isinstance(current_list, list):
            self._add_error(f"'{list_name}' is not a list")
            return None
            
        if not isinstance(index, int):
            self._add_error(f"List index must be an integer, got {type(index).__name__}")
            return None
            
        if index < 0 or index >= len(current_list):
            self._add_error(f"List index {index} out of range for list of length {len(current_list)}")
            return None
            
        return current_list[index]

    def visit_assignment(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_assignment")
        var_name_token = node.children[0]
        value_node = node.children[1]
        
        if isinstance(var_name_token, Token):
            var_name = var_name_token.value
        else:
            var_name = self.visit(var_name_token)
        
        value = self.visit(value_node)
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Assignment: {var_name} = {value}")
        
        if var_name in self.error_vars_list:
            return
            
        if not self.env.is_defined(var_name):
            self.env.define_var(var_name, value)
            self.defined_vars.add(var_name)
            self.assigned_vars.add(var_name)
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Auto-defined variable {var_name} = {value}")
        else:
            if self.env.is_constant(var_name):
                self._add_error(f"Cannot assign values to constants afterward: '{var_name}'")
                return
            
            current_value = self.env.get_value(var_name)
            if current_value is None:
                self._add_error(f"Variable '{var_name}' has no value")
                return
                
            actual_type = type(current_value).__name__
            if actual_type == 'str':
                actual_type = 'str'
            elif isinstance(current_value, int):
                actual_type = 'int'
            elif isinstance(current_value, float):
                actual_type = 'float'
                
            new_value = self.cast_type(value, actual_type, var_name)
                
            if new_value is not None:
                self.env.set_value(var_name, new_value)
                self.assigned_vars.add(var_name)
                self._add_debug_output(self.current_line_num, f"[RUNTIME] Successfully assigned {var_name} = {new_value}")

    def visit_again_stmt(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_again_stmt")
        
        if len(node.children) < 2:
            self._add_error("Invalid Again statement: missing required parts")
            return
        
        times_expr = node.children[0]
        repeat_var = None
        block_node = None
        
        if len(node.children) == 3:
            if isinstance(node.children[1], Token) and node.children[1].type == 'IDENT':
                repeat_var = node.children[1].value
            block_node = node.children[2]
        elif len(node.children) == 2:
            block_node = node.children[1]
        else:
            self._add_error("Invalid Again statement structure")
            return
        
        if block_node is None or not hasattr(block_node, 'data') or block_node.data != 'block':
            self._add_error("Invalid Again statement: missing or invalid block")
            return
        
        times = self.visit(times_expr)
        
        if not isinstance(times, (int, float)) or times < 0:
            self._add_error("Loop times must be a non-negative number")
            return
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Starting loop: {times} iterations")
        
        self.should_break = False
        
        for i in range(int(times)):
            if self.should_break:
                break
                
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Loop iteration: {i+1}")
            
            if repeat_var:
                self.env.define_var(repeat_var, i + 1)
                self._add_debug_output(self.current_line_num, f"[RUNTIME] Set repeat variable '{repeat_var}' = {i+1}")
            
            self.visit_block(block_node)
            
            if self.should_break:
                self._add_debug_output(self.current_line_num, f"[RUNTIME] Loop break at iteration {i+1}")
                break
        
        if repeat_var and self.env.is_defined(repeat_var):
            self.env.variables.pop(repeat_var, None)
        
        self.should_break = False

    def visit_member_access_expr(self, node) -> Any:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_member_access_expr")
        
        obj_token = node.children[0]
        attr_token = node.children[1]
        
        obj_name = obj_token.value
        attr_name = attr_token.value
        
        if not self.env.is_defined(obj_name):
            self._add_error(f"Object '{obj_name}' is not defined")
            return None
        
        obj = self.env.get_value(obj_name)
        
        if attr_name not in obj:
            self._add_error(f"Object '{obj_name}' has no member '{attr_name}'")
            return None
        
        if obj_name == 'now' and attr_name == 'repeat':
            if self.env.is_defined('repeat'):
                return self.env.get_value('repeat')
            else:
                self._add_error("'now.repeat' can only be used inside an Again loop that provides a repeat parameter")
                return None
        
        return obj[attr_name]

    def visit_rep_stop(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_rep_stop")
        self.should_break = True
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Loop break requested via rep.stop")

    def visit_input_call(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_input_call")
        self.visit_input_call_as_expr(node)

    def visit_input_call_as_expr(self, node) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_input_call_as_expr")
        if not node.children:
            self._add_error("Input call missing prompt string")
            return ""
        
        prompt_node = node.children[0]
        prompt = self.visit(prompt_node)
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Input call with prompt: {prompt}")
        
        try:
            user_input = input(f"\033[94m[INFO] {prompt}\033[0m")
            self._add_debug_output(self.current_line_num, f"[RUNTIME] User input: {user_input}")
            return user_input
        except EOFError:
            self._add_error("Unexpected end of input")
            return ""
        except Exception as e:
            self._add_error(f"Input error: {str(e)}")
            return ""

    def visit_var_def(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_var_def")
        type_name_token = node.children[0]
        if isinstance(type_name_token, Token):
            type_name = type_name_token.value
        else:
            type_name = type_name_token.children[0].value if type_name_token.children else 'int'
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Variable definition: type={type_name}")
        
        if type_name not in ['int', 'float', 'str']:
            self._add_error(f"Invalid type name: '{type_name}'")
            return
        
        var_name_token = node.children[1]
        if isinstance(var_name_token, Token):
            var_name = var_name_token.value
        else:
            var_name = self.visit(var_name_token)
        
        if var_name in self.error_vars_list:
            return

        if self.env.is_defined(var_name):
            self._add_error(f"Variable '{var_name}' is already defined")
            self.error_vars_list.append(var_name)
            return
            
        if len(node.children) > 2:
            value_node = node.children[2]
            value = self.visit(value_node)
            
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Variable {var_name} assigned value: {value}")
            
            if isinstance(value, (int, float)):
                actual_type = 'int' if isinstance(value, int) else 'float'
                casted_value = self.cast_type(value, actual_type, var_name)
            else:
                casted_value = self.cast_type(value, type_name, var_name)
                
            if casted_value is not None:
                self.env.define_var(var_name, casted_value)
                self.assigned_vars.add(var_name)
                self.defined_vars.add(var_name)
                self._add_debug_output(self.current_line_num, f"[RUNTIME] Successfully defined variable {var_name} = {casted_value}")
        else:
            default_values = {'int': 0, 'float': 0.0, 'str': ''}
            default_value = default_values.get(type_name, None)
            self.env.define_var(var_name, default_value)
            self.defined_vars.add(var_name)
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Defined variable {var_name} with default value: {default_value}")

    def visit_const_def(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_const_def")
        if len(node.children) < 3:
            self._add_error("Constant definition must include an initial value")
            return
            
        type_name_token = node.children[0]
        if isinstance(type_name_token, Token):
            type_name = type_name_token.value
        else:
            type_name = type_name_token.children[0].value if type_name_token.children else 'int'
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Constant definition: type={type_name}")
        
        if type_name not in ['int', 'float', 'str']:
            self._add_error(f"Invalid type name: '{type_name}'")
            return
        
        const_name_token = node.children[1]
        if isinstance(const_name_token, Token):
            const_name = const_name_token.value
        else:
            const_name = self.visit(const_name_token)
        
        if const_name in self.error_vars_list:
            return

        if self.env.is_defined(const_name):
            self._add_error(f"Constant '{const_name}' is already defined")
            self.error_vars_list.append(const_name)
            return
            
        value = self.visit(node.children[2])
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Constant {const_name} assigned value: {value}")
        
        if isinstance(value, (int, float)):
            actual_type = 'int' if isinstance(value, int) else 'float'
            casted_value = self.cast_type(value, actual_type, const_name)
        else:
            casted_value = self.cast_type(value, type_name, const_name)
            
        if casted_value is not None:
            self.env.define_const(const_name, casted_value)
            self.assigned_vars.add(const_name)
            self.defined_vars.add(const_name)
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Successfully defined constant {const_name} = {casted_value}")

    def visit_cause_stmt(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_cause_stmt")
        conditions_node = node.children[0]
        if_block = node.children[1]
        or_block = node.children[2] if len(node.children) > 2 else None
        
        if not hasattr(conditions_node, 'data') or conditions_node.data != 'conditions':
            self._add_error("Invalid conditions structure")
            return
        
        conditions_result = self.visit(conditions_node)
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Conditions result: {conditions_result}")
        
        if conditions_result:
            self._add_debug_output(self.current_line_num, "[RUNTIME] Executing if block")
            self.visit_block(if_block)
        elif or_block:
            self._add_debug_output(self.current_line_num, "[RUNTIME] Executing else block")
            self.visit_block(or_block)

    def visit_conditions(self, node) -> bool:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_conditions")
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Conditions node has {len(node.children)} children")
        
        if not node.children:
            return False
        
        if len(node.children) == 1:
            result = self.visit(node.children[0])
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Single condition result: {result}")
            return result
        
        results = []
        logic_ops = []
        
        for i, child in enumerate(node.children):
            if hasattr(child, 'data'):
                if child.data == 'condition':
                    result = self.visit(child)
                    results.append(result)
                    self._add_debug_output(self.current_line_num, f"[RUNTIME] Condition {len(results)}: {result}")
                elif child.data == 'logic_op':
                    logic_op = self.visit(child)
                    logic_ops.append(logic_op)
                    self._add_debug_output(self.current_line_num, f"[RUNTIME] Logic op {len(logic_ops)}: {logic_op}")
        
        if not logic_ops and len(results) > 1:
            self._add_debug_output(self.current_line_num, f"[RUNTIME] No logic ops found, defaulting to AND")
            final_result = True
            for result in results:
                final_result = final_result and result
                if not final_result:
                    break
            return final_result
        
        if len(results) == len(logic_ops) + 1:
            final_result = results[0]
            for i, logic_op in enumerate(logic_ops):
                if logic_op == 'and':
                    final_result = final_result and results[i + 1]
                elif logic_op == 'or':
                    final_result = final_result or results[i + 1]
                else:
                    self._add_error(f"Unknown logical operator: '{logic_op}'")
                    return False
                
                if logic_op == 'and' and not final_result:
                    break
                if logic_op == 'or' and final_result:
                    break
                    
            return final_result
        else:
            self._add_error("Mismatch between conditions and logic operators")
            return False

    def visit_logic_op(self, node) -> str:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_logic_op")
        
        if 0 < self.current_line_num <= len(self.original_lines):
            line_content = self.original_lines[self.current_line_num - 1]
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Current line content: {line_content}")
            
            if ' and ' in line_content:
                return 'and'
            elif ' or ' in line_content:
                return 'or'
        
        if node.children and isinstance(node.children[0], Token):
            token_value = node.children[0].value.lower()
            self._add_debug_output(self.current_line_num, f"[RUNTIME] Logic op token value: {token_value}")
            return token_value
        
        return 'and'

    def visit_condition(self, node) -> bool:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_condition")
        left = self.visit(node.children[0])
        op = self.visit(node.children[1])
        right = self.visit(node.children[2])
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Condition: {left} {op} {right}")
        
        try:
            if op == '?':
                return left == right
            elif op == '!':
                return left != right
            elif op == '>':
                return left > right
            elif op == '<':
                return left < right
            elif op == '>=':
                return left >= right
            elif op == '<=':
                return left <= right
            else:
                self._add_error(f"Unknown comparison operator: {op}")
                return False
        except TypeError as e:
            self._add_error(f"Comparison failed between {type(left).__name__} and {type(right).__name__}: {e}")
            return False

    def visit_output_stmt(self, node) -> None:
        self._add_method_call(self.current_line_num, "RuntimeChecker.visit_output_stmt")
        member_node = node.children[0]
        if not hasattr(member_node, 'data') or member_node.data != 'member_access':
            self._add_error("Expected member access in output statement")
            return
        
        full_func_name = self.visit(member_node)
        
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Output statement: {full_func_name}")
        
        if not full_func_name or '.' not in full_func_name:
            self._add_error(f"Invalid member access: {full_func_name}")
            return
        
        obj_name, method_name = full_func_name.split('.', 1)

        valid_output_funcs = {"out.Info", "out.Warn", "out.Error"}
        if full_func_name not in valid_output_funcs:
            self._add_error(f"Invalid output function: {full_func_name}")
            return

        msg_parts = []
        if len(node.children) > 1:
            args_node = node.children[1]
            if hasattr(args_node, 'children') and args_node.children:
                for i, arg in enumerate(args_node.children):
                    if arg is None:
                        self._add_error("Invalid argument in output function: empty argument")
                        return
                    
                    arg_value = self.visit(arg)
                    if arg_value is None:
                        self._add_error(f"Invalid argument at position {i+1} in output function")
                        return
                        
                    if isinstance(arg_value, list):
                        arg_value = str(arg_value)
                        
                    try:
                        msg_parts.append(str(arg_value))
                    except Exception as e:
                        self._add_error(f"Error formatting argument: {e}")
                        return
        
        full_msg = "".join(msg_parts)

        self.has_output = True
        self._add_debug_output(self.current_line_num, f"[RUNTIME] Output message: {full_msg}")

        if method_name == "Info":
            print(f"\033[94m[INFO] {full_msg}\033[0m")
        elif method_name == "Warn":
            print(f"\033[93m[WARN] {full_msg}\033[0m", file=sys.stderr)
        elif method_name == "Error":
            print(f"\033[91m[ERROR] {full_msg}\033[0m", file=sys.stderr)