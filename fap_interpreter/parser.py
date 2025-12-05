from lark import Lark, Tree

FAP_GRAMMAR = '''
    start: (statement NEWLINE)* statement?

    statement: const_def 
             | var_def 
             | assignment
             | cause_stmt 
             | output_stmt
             | input_call
             | again_stmt
             | rep_stop
             | list_method_call
             | list_def
             | func_def
             | func_call_stmt
             | back_stmt

    const_def: "Const" type_name IDENT "->" expr
    var_def: "New" type_name IDENT ("->" expr)?
    list_def: "New" "List" IDENT "=>" list_literal
    assignment: IDENT "->" expr
    
    cause_stmt: "Cause" conditions block ("or" block)?
    conditions: condition (logic_op condition)*
    condition: expr COMPARISON_OP expr
    logic_op: "and"i | "or"i
    block: "[" (statement | NEWLINE)* "]"
    
    output_stmt: member_access "(" output_args? ")"
    member_access: IDENT "." IDENT
    output_args: expr ("," expr)*
    
    input_call: "getInputFor" "(" STRING ")" | "st.getInputFor" "(" STRING ")"
    
    again_stmt: "Again" "(" expr ")" block
              | "Again" "(" expr "," IDENT ")" block
    
    rep_stop: "rep" "." "stop"
    
    list_method_call: IDENT "." list_method "(" expr? ")"
    list_method: "add"i | "clear"i
    list_literal: "[" [expr ("," expr)*] "]"
    
    func_def: "Fuc" IDENT "(" params ")" block
    params: [param ("," param)*]
    param: type_name IDENT
    func_call_stmt: IDENT "(" func_args? ")"
    back_stmt: "back" "." "value" "(" expr? ")"
    
    expr: term (ADD_OP term)*
    term: factor (MUL_OP factor)*
    factor: NUMBER | STRING | IDENT | member_access_expr | input_call | math_func_call | list_literal | list_access | abs_expr | func_call | "(" expr ")"
    member_access_expr: IDENT "." IDENT
    list_access: IDENT "[" expr "]"
    math_func_call: IDENT "(" expr ("," expr)* ")"
    func_call: IDENT "(" func_args? ")"
    func_args: expr ("," expr)*
    abs_expr: "|" expr "|"
    type_name: "int" -> type_int
              | "float" -> type_float
              | "str" -> type_str

    COMPARISON_OP: ">=" | "<=" | "?" | "!" | ">" | "<"
    ADD_OP: "+" | "-"
    MUL_OP: "*" | "/"
    IDENT: /[a-zA-Z_][a-zA-Z0-9_]*/
    NUMBER: /-?[0-9]+(\\.[0-9]+)?/
    STRING: /"[^"]*"/
    LIST_ARROW: "=>"

    %import common.NEWLINE
    %import common.WS
    %ignore WS
'''

def create_fap_parser():
    return Lark(FAP_GRAMMAR, parser='lalr', start='start')

__all__ = ['create_fap_parser', 'Tree']