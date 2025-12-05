from typing import Any, Dict, List, Optional

class Environment:
    def __init__(self, parent=None):
        self.variables: Dict[str, Any] = {}
        self.constants: Dict[str, Any] = {}
        self.functions: Dict[str, Dict] = {}
        self.debug_mode = False
        self.debug_plus_mode = False
        self.parent = parent

    def set_debug_mode(self, debug_mode: bool, debug_plus_mode: bool):
        self.debug_mode = debug_mode
        self.debug_plus_mode = debug_plus_mode

    def _add_method_call(self, method_name: str, *args):
        if not self.debug_plus_mode:
            return
        args_str = ", ".join(str(arg) for arg in args)
        print(f"\033[38;2;255;165;0m[ENV] [METHOD CALL] Environment.{method_name}({args_str})\033[0m")

    def define_var(self, name: str, value: Any) -> None:
        self._add_method_call("define_var", name, value)
        self.variables[name] = value
        if self.debug_mode or self.debug_plus_mode:
            print(f"\033[90m[ENV] Defined variable: {name} = {value}\033[0m")

    def define_const(self, name: str, value: Any) -> None:
        self._add_method_call("define_const", name, value)
        self.constants[name] = value
        if self.debug_mode or self.debug_plus_mode:
            print(f"\033[90m[ENV] Defined constant: {name} = {value}\033[0m")

    def define_func(self, name: str, params: List[Dict], body, env) -> None:
        self._add_method_call("define_func", name, params)
        self.functions[name] = {
            'params': params,
            'body': body,
            'env': env
        }
        if self.debug_mode or self.debug_plus_mode:
            param_str = ", ".join([f"{p['type']} {p['name']}" for p in params])
            print(f"\033[90m[ENV] Defined function: {name}({param_str})\033[0m")

    def set_value(self, name: str, value: Any) -> None:
        self._add_method_call("set_value", name, value)
        if name in self.constants:
            raise ValueError(f"Cannot modify constant: {name}")
        if name in self.variables:
            old_value = self.variables[name]
            self.variables[name] = value
            if self.debug_mode or self.debug_plus_mode:
                print(f"\033[90m[ENV] Updated variable: {name} = {value} (was: {old_value})\033[0m")
        else:
            if self.parent and self.parent.is_defined(name):
                self.parent.set_value(name, value)
            else:
                raise ValueError(f"Variable not defined: {name}")

    def get_value(self, name: str) -> Any:
        self._add_method_call("get_value", name)
        if name in self.constants:
            value = self.constants[name]
            if self.debug_mode or self.debug_plus_mode:
                print(f"\033[90m[ENV] Retrieved constant: {name} = {value}\033[0m")
            return value
        elif name in self.variables:
            value = self.variables[name]
            if self.debug_mode or self.debug_plus_mode:
                print(f"\033[90m[ENV] Retrieved variable: {name} = {value}\033[0m")
            return value
        elif name in self.functions:
            value = self.functions[name]
            if self.debug_mode or self.debug_plus_mode:
                print(f"\033[90m[ENV] Retrieved function: {name}\033[0m")
            return value
        elif self.parent:
            return self.parent.get_value(name)
        else:
            raise ValueError(f"Variable not defined: {name}")

    def get_func(self, name: str) -> Optional[Dict]:
        self._add_method_call("get_func", name)
        if name in self.functions:
            return self.functions[name]
        elif self.parent:
            return self.parent.get_func(name)
        else:
            return None

    def is_defined(self, name: str) -> bool:
        self._add_method_call("is_defined", name)
        if name in self.variables or name in self.constants or name in self.functions:
            return True
        elif self.parent:
            return self.parent.is_defined(name)
        else:
            return False

    def is_constant(self, name: str) -> bool:
        self._add_method_call("is_constant", name)
        return name in self.constants

    def is_function(self, name: str) -> bool:
        self._add_method_call("is_function", name)
        return name in self.functions or (self.parent and self.parent.is_function(name))

    def create_child_env(self):
        return Environment(parent=self)