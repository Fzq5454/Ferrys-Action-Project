import re
from typing import List

class SyntaxChecker:
    def __init__(self):
        self.errors = []
        self.debug_mode = False
        self.debug_plus_mode = False
        self.original_lines = []
        self.debug_output = []

    def set_debug_mode(self, debug_mode: bool, debug_plus_mode: bool, original_lines: List[str]):
        self.debug_mode = debug_mode
        self.debug_plus_mode = debug_plus_mode
        self.original_lines = original_lines

    def _add_debug_output(self, line_num: int, message: str):
        if not self.debug_plus_mode:
            return
            
        if line_num <= 0 or line_num > len(self.original_lines):
            return
            
        line_content = self.original_lines[line_num - 1].rstrip()
        debug_line = f"\033[33m[Line {line_num}: {line_content}] {message}\033[0m"
        self.debug_output.append(debug_line)

    def preprocess_code(self, code: str) -> str:
        lines = code.split('\n')
        processed_lines = []
        
        in_block_comment = False
        block_comment_start_line = 0
        
        for line_num, line in enumerate(lines, 1):
            original_line = line.rstrip()
            stripped_line = original_line.strip()
            
            if not stripped_line:
                continue
                
            if stripped_line.startswith('@None'):
                continue
                
            if stripped_line.startswith('#X') and not in_block_comment:
                in_block_comment = True
                block_comment_start_line = line_num
                continue
                
            if stripped_line.startswith('#Y'):
                if in_block_comment:
                    in_block_comment = False
                else:
                    self._add_error(f"Unexpected block comment end '#Y'", line_num)
                continue
                
            if in_block_comment:
                continue
            
            processed_lines.append(original_line)
        
        if in_block_comment:
            self._add_error(f"Unclosed block comment starting at line {block_comment_start_line}", block_comment_start_line)
        
        return '\n'.join(processed_lines)

    def check_syntax(self, code: str) -> List[str]:
        self.errors = []
        self.debug_output = []
        
        processed_code = self.preprocess_code(code)
        
        if not processed_code.strip():
            for debug_line in self.debug_output:
                print(debug_line)
            return self.errors
            
        lines = processed_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if stripped_line:
                self._add_debug_output(line_num, "[SYNTAX_CHECK] Processing line")
                self._is_valid_statement(stripped_line, line_num, lines)
            else:
                self._add_debug_output(line_num, "[SYNTAX_CHECK] Skipping empty line")
        
        if not self.errors:
            self._check_symbol_integrity(lines)
        
        for debug_line in self.debug_output:
            print(debug_line)
            
        return self.errors

    def _check_symbol_integrity(self, lines: List[str]) -> None:
        if not self.debug_plus_mode:
            return
            
        bracket_stack = []
        brace_stack = []
        paren_stack = []
        quote_stack = []
        in_string = False
        
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            if not stripped_line:
                continue
                
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Checking symbol integrity")
                
            i = 0
            while i < len(line):
                char = line[i]
                
                if char == '"':
                    if not in_string:
                        in_string = True
                        quote_stack.append(('"', line_num, i + 1))
                    else:
                        in_string = False
                        if quote_stack:
                            quote_stack.pop()
                    i += 1
                    continue
                
                if in_string:
                    i += 1
                    continue
                
                if char == '[':
                    bracket_stack.append(('[', line_num, i + 1))
                elif char == ']':
                    if bracket_stack:
                        bracket_stack.pop()
                    else:
                        self._add_error("Unexpected ']'", line_num)
                
                elif char == '{':
                    brace_stack.append(('{', line_num, i + 1))
                elif char == '}':
                    if brace_stack:
                        brace_stack.pop()
                    else:
                        self._add_error("Unexpected '}'", line_num)
                
                elif char == '(':
                    paren_stack.append(('(', line_num, i + 1))
                elif char == ')':
                    if paren_stack:
                        paren_stack.pop()
                    else:
                        self._add_error("Unexpected ')'", line_num)
                
                i += 1
        
        for symbol, line_num, pos in bracket_stack:
            self._add_error("Unclosed '['", line_num)
        
        for symbol, line_num, pos in brace_stack:
            self._add_error("Unclosed '{'", line_num)
        
        for symbol, line_num, pos in paren_stack:
            self._add_error("Unclosed '('", line_num)
        
        for symbol, line_num, pos in quote_stack:
            self._add_error("Unclosed '\"'", line_num)

    def _is_valid_statement(self, line: str, line_num: int, lines: List[str]) -> bool:
        self._add_debug_output(line_num, f"[SYNTAX_CHECK] Checking syntax: {line}")
    
        if line.startswith('Again('):
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid again statement")
            return True
        if line == 'rep.stop':
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid rep.stop statement")
            return True
        if line == ']':
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid block end")
            return True
            
        if line == 'or':
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid 'or' keyword")
            return True
            
        if line == 'or [':
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid 'or' with block start")
            return True
            
        if line == '] or':
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid block end with 'or'")
            return True
            
        if line == '] or [':
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid block end with 'or' and block start")
            return True
            
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', line):
            self._add_error(f"Invalid statement: '{line}' - looks like a variable name but not used in assignment", line_num)
            return False
            
        if re.match(r'^-?\d+(\.\d+)?$', line):
            self._add_error(f"Invalid statement: '{line}' - number literal not used in expression", line_num)
            return False
            
        if re.match(r'^"[^"]*"$', line):
            self._add_error(f"Invalid statement: '{line}' - string literal not used in expression", line_num)
            return False

        if line.startswith('New List '):
            if '=>' not in line:
                self._add_error(f"List definition must include '=>': '{line}'", line_num)
                return False
                
            arrow_index = line.find('=>')
            left_side = line[9:arrow_index].strip()
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', left_side):
                self._add_error(f"Invalid list name: '{left_side}'", line_num)
                return False
                
            right_side = line[arrow_index+2:].strip()
            if not right_side.startswith('[') or not right_side.endswith(']'):
                self._add_error(f"List definition must be followed by list literal: '{line}'", line_num)
                return False
                
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid list definition")
            return True

        list_method_pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*\.(add|clear)\(.*\)$'
        if re.match(list_method_pattern, line):
            if '.add(' in line:
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\.add\([^)]+\)$', line):
                    self._add_error(f"Invalid list.add call: '{line}'", line_num)
                    return False
            elif '.clear(' in line:
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\.clear\(\)$', line):
                    self._add_error(f"Invalid list.clear call: '{line}'", line_num)
                    return False
                    
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid list method call")
            return True

        list_access_pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*\[\d+\]$'
        if re.match(list_access_pattern, line):
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid list access")
            return True

        if line.startswith('Fuc '):
            if not re.match(r'^Fuc\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*\[$', line):
                self._add_error(f"Invalid function definition: '{line}'", line_num)
                return False
            
            match = re.match(r'^Fuc\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\((.*)\)\s*\[$', line)
            if match:
                params_str = match.group(1).strip()
                if params_str:
                    params = [p.strip() for p in params_str.split(',')]
                    for param in params:
                        if param:
                            if not re.match(r'^(int|float|str)\s+[a-zA-Z_][a-zA-Z0-9_]*$', param):
                                self._add_error(f"Invalid function parameter: '{param}' in '{line}'", line_num)
                                return False
            
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid function definition")
            return True

        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)$', line) and not line.startswith('getInputFor') and not line.startswith('out.'):
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid function call")
            return True

        if line.startswith('back.value('):
            if not re.match(r'^back\.value\([^)]*\)$', line):
                self._add_error(f"Invalid return statement: '{line}'", line_num)
                return False
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid return statement")
            return True
            
        if line.startswith('Const '):
            parts = line.split()
            if len(parts) < 4:
                self._add_error(f"Constant definition must include type, name, and initial value: '{line}'", line_num)
                return False
            if '->' not in line:
                self._add_error(f"Constant definition must include '->': '{line}'", line_num)
                return False
            
            arrow_index = line.find('->')
            left_side = line[6:arrow_index].strip()
            if not re.match(r'^(int|float|str)\s+[a-zA-Z_][a-zA-Z0-9_]*$', left_side):
                self._add_error(f"Invalid constant declaration format: '{line}'", line_num)
                return False
                
            type_name = left_side.split()[0]
            if type_name not in ['int', 'float', 'str']:
                self._add_error(f"Invalid type name: '{type_name}'", line_num)
                return False
                
            right_side = line[arrow_index+2:].strip()
            if not right_side:
                self._add_error(f"Constant definition must include initial value after '->'", line_num)
                return False
            
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid constant definition")
            return True
            
        if line.startswith('New '):
            parts = line.split()
            if len(parts) < 3:
                self._add_error(f"Variable definition must include type and name: '{line}'", line_num)
                return False
                
            if '->' in line:
                arrow_index = line.find('->')
                left_side = line[4:arrow_index].strip()
                if not re.match(r'^(int|float|str)\s+[a-zA-Z_][a-zA-Z0-9_]*$', left_side):
                    self._add_error(f"Invalid variable declaration format: '{line}'", line_num)
                    return False
            else:
                left_side = line[4:].strip()
                if not re.match(r'^(int|float|str)\s+[a-zA-Z_][a-zA-Z0-9_]*$', left_side):
                    self._add_error(f"Invalid variable declaration format: '{line}'", line_num)
                    return False
                    
            type_name = parts[1]
            if type_name not in ['int', 'float', 'str']:
                self._add_error(f"Invalid type name: '{type_name}'", line_num)
                return False
            
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid variable definition")
            return True
            
        if line.startswith('Cause '):
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid cause statement")
            return True

        if line.startswith('Again('):
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid again statement")
            return True

        if line == 'rep.stop':
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid rep.stop statement")
            return True

        if '->' in line and not line.strip().startswith('@'):
            parts = line.split('->')
            if len(parts) == 2:
                left_side = parts[0].strip()
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', left_side):
                    self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid assignment")
                    return True
                elif re.match(r'^(int|float|str)\s+[a-zA-Z_][a-zA-Z0-9_]*$', left_side):
                    type_name = left_side.split()[0]
                    if type_name not in ['int', 'float', 'str']:
                        self._add_error(f"Invalid type name: '{type_name}'", line_num)
                        return False
                    self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid variable definition with assignment")
                    return True
            
        valid_starts = [
            'Const ', 'New ', 'Cause ', 'Again(', 'out.Info(', 'out.Warn(', 'out.Error(',
            'getInputFor(', 'rootFor(', 'squFor(', 'd.root(', 't.root(', 'Fuc ', 'back.value('
        ]
        
        for start in valid_starts:
            if line.startswith(start):
                self._add_debug_output(line_num, f"[SYNTAX_CHECK] Valid statement starting with '{start}'")
                return True
                
        if re.match(r'^getInputFor\("[^"]*"\)$', line):
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid input call")
            return True
                
        if re.match(r'^out\.(Info|Warn|Error)\(.*\)$', line):
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid output statement")
            return True
            
        if line == 'rep.stop':
            self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid rep.stop statement")
            return True
            
        if '|' in line and not line.strip().startswith('@'):
            pipe_count = line.count('|')
            if pipe_count == 2 and line.count('->') == 1:
                self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid assignment with absolute value")
                return True
            elif pipe_count >= 2:
                self._add_debug_output(line_num, "[SYNTAX_CHECK] Valid expression with absolute values")
                return True
            
        self._add_error(f"Invalid statement: '{line}'", line_num)
        return False

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