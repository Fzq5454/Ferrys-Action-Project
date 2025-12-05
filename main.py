import sys
import os

sys.path.append(os.path.dirname(__file__))

from fap_interpreter.syntax_checker import SyntaxChecker
from fap_interpreter.runtime_checker import RuntimeChecker

def extract_debug_directives_and_clean_code(code):
    lines = code.split('\n')
    cleaned_lines = []
    debug_mode = False
    debug_plus_mode = False
    
    for line in lines:
        stripped_line = line.strip()
        if stripped_line == '@debug=true':
            debug_mode = True
            continue
        elif stripped_line == '@debug=false':
            debug_mode = False
            continue
        elif stripped_line == '@debugPL=true':
            debug_plus_mode = True
            continue
        elif stripped_line == '@debugPL=false':
            debug_plus_mode = False
            continue
        else:
            cleaned_lines.append(line)
    
    cleaned_code = '\n'.join(cleaned_lines)
    return debug_mode, debug_plus_mode, cleaned_code

def main():
    if len(sys.argv) < 2:
        print(f"\033[91m[ERROR] Please provide a FAP file to execute\033[0m")
        print(f"Usage: python main.py <fap_file>")
        return
    
    filename = sys.argv[1]
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
            original_lines = code.split('\n')
    except FileNotFoundError as e:
        print(f"\033[91m[ERROR] Failed to find the file: '{e}'\033[0m")
        return
    except Exception as e:
        print(f"\033[91m[ERROR] Failed to read the file: '{e}'\033[0m")
        return

    debug_mode, debug_plus_mode, cleaned_code = extract_debug_directives_and_clean_code(code)
    
    print("\033[96m=== FAP Language Interpreter ===\033[0m")
    
    if debug_mode:
        print(f"\033[95m[DEBUG] Debug mode: debug (ENV mode)\033[0m")
    elif debug_plus_mode:
        print(f"\033[95m[DEBUG] Debug mode: debugPL (Full stack trace)\033[0m")
    
    syntax_checker = SyntaxChecker()
    syntax_checker.set_debug_mode(debug_mode, debug_plus_mode, original_lines)
    
    processed_code = syntax_checker.preprocess_code(cleaned_code)
    
    if debug_mode or debug_plus_mode:
        processed_lines = processed_code.split('\n')
        print(f"\033[95m[DEBUG] Processed code:\033[0m")
        for i, line in enumerate(processed_lines, 1):
            print(f"\033[95m[DEBUG] Line {i}: {repr(line)}\033[0m")
    
    syntax_errors = syntax_checker.check_syntax(cleaned_code)
    
    all_errors = []
    has_output = False
    
    for error in syntax_errors:
        all_errors.append(error)
        print(f"\033[91m{error}\033[0m")
    
    if processed_code.strip() and not syntax_errors:
        if debug_mode or debug_plus_mode:
            print(f"\033[95m[DEBUG] Starting runtime execution...\033[0m")
        runtime_checker = RuntimeChecker()
        runtime_checker.set_debug_mode(debug_mode, debug_plus_mode, original_lines)
        runtime_checker.execute(processed_code)
        
        for error in runtime_checker.errors:
            all_errors.append(error)
            print(f"\033[91m{error}\033[0m")
        
        has_output = runtime_checker.has_output
        if debug_mode or debug_plus_mode:
            print(f"\033[95m[DEBUG] Runtime execution completed. Has output: {has_output}\033[0m")
    else:
        if debug_mode or debug_plus_mode:
            print(f"\033[95m[DEBUG] No code to execute or syntax errors found\033[0m")
    
    if all_errors:
        print(f"\033[91mTotal errors: {len(all_errors)}\033[0m")
    else:
        if not has_output:
            print(f"\033[93m[WARN] The project ran successfully, but there was no output\033[0m")
        else:
            print("\033[92mExecution completed successfully!\033[0m")

if __name__ == "__main__":
    main()