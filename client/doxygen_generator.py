#!/usr/bin/env python3
"""!
@package inline_doxygen_generator
@brief Embeds dynamic Doxygen docstrings and maps import usage directly within Python files.
@details Statically parses code structural syntax, inventories imported objects, tracks 
         actual usage across the source tree, and mutates file arrays with exact indentation.
"""

import ast
import os
import sys

class CodeUsageAnalyzer(ast.NodeVisitor):
    """!
    @brief AST Visitor that sweeps code to log all variable, function, and object names referenced.
    """
    def __init__(self):
        self.used_names = set()

    def visit_Name(self, node: ast.Name):
        # Captures direct name usages like 'logging' or 'inspect'
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Captures root object name references from chained attributes (e.g., 'logging.root')
        current = node.value
        while isinstance(current, ast.Attribute):
            current = current.value
        if isinstance(current, ast.Name):
            self.used_names.add(current.id)
        self.generic_visit(node)

def parse_argument_signature(node: ast.FunctionDef) -> list:
    """!
    @brief Statically analyzes a function definition node to discover parameters and defaults.
    @param node The ast.FunctionDef block target from the parsed syntax tree.
    @return A list of dictionaries detailing parameter names and fallback default string values.
    """
    params = []
    args = node.args.args
    defaults = node.args.defaults
    
    default_offset = len(args) - len(defaults)
    
    for i, arg in enumerate(args):
        arg_info = {"name": arg.arg, "default": None}
        if i >= default_offset:
            default_node = defaults[i - default_offset]
            if isinstance(default_node, ast.Constant):
                arg_info["default"] = repr(default_node.value)
            else:
                arg_info["default"] = "Expression"
        params.append(arg_info)
        
    return params

def format_doxygen_block(node, indent_level=0) -> list:
    """!
    @brief Constructs standard Doxygen syntax string blocks featuring signature details.
    @param node The code block object element (ast.FunctionDef, ast.ClassDef, ast.Module).
    @param indent_level The integer numerical alignment spaces formatting padding layout.
    @return A list of formatted string lines containing structured doxygen markers.
    """
    indent = " " * indent_level
    lines = [f'{indent}"""!']
    
    if isinstance(node, ast.Module):
        lines.append(f'{indent}@package {node.base_name}')
        lines.append(f'{indent}@brief Top-level codebase framework module wrapper container.')
        lines.append(f'{indent}@details Automatically generated template infrastructure map.')
        
    elif isinstance(node, ast.ClassDef):
        lines.append(f'{indent}@brief Object representation profile managing {node.name} attributes.')
        lines.append(f'{indent}@details Handles custom lifecycle workflows, components, and memory states.')
        lines.append(f'{indent}@note Created and instantiated cleanly via initialization constructor calls.')
        
    elif isinstance(node, ast.FunctionDef):
        is_method = indent_level > 0 and node.args.args and node.args.args.arg == "self"
        block_type = "object method" if is_method else "independent function"
        
        lines.append(f'{indent}@brief Executes the structural {node.name} {block_type}.')
        
        params = parse_argument_signature(node)
        for param in params:
            if param["name"] == "self":
                lines.append(f'{indent}@param self Implicit reference linking instance memory pointer allocation.')
                continue
            default_str = f' (Defaults to {param["default"]}).' if param["default"] is not None else ""
            lines.append(f'{indent}@param {param["name"]} Functional runtime input element value context requirement{default_str}.')
            
        lines.append(f'{indent}@return Yields processed variable calculations data states or context conditions.')
        
    lines.append(f'{indent}"""')
    return lines

def format_import_doxygen(node, used_names: set, indent_level=0) -> list:
    """!
    @brief Creates a specialized Doxygen comment evaluating import visibility usage metrics.
    @param node The ast.Import or ast.ImportFrom reference node.
    @param used_names Set string index keys gathered from code analysis.
    @param indent_level Number of spaces to pad the block.
    @return A list of generated doxygen template lines.
    """
    indent = " " * indent_level
    lines = [f'## @see Reference dependency binding tracker info:']
    
    if isinstance(node, ast.Import):
        for alias in node.names:
            lookup = alias.asname if alias.asname else alias.name
            status = "ACTIVE" if lookup in used_names else "UNUSED (Safe for cleanup optimization removal)"
            lines.append(f'#  - Module Name: `{alias.name}` -> Usage State: **{status}**')
            
    elif isinstance(node, ast.ImportFrom):
        module_from = node.module if node.module else "local relative package path"
        lines.append(f'#  - From Module Namespace Source: `{module_from}`')
        for alias in node.names:
            lookup = alias.asname if alias.asname else alias.name
            status = "ACTIVE" if lookup in used_names else "UNUSED"
            lines.append(f'#    * Object Bound: `{alias.name}` -> Target status: **{status}**')
            
    return lines

def process_python_file(input_path: str):
    """!
    @brief Injects structural Doxygen documentation and dependency usage blocks into a source copy.
    @param input_path Relative or absolute literal string path to the code file.
    """
    if not os.path.exists(input_path):
        print(f"Error: Input target source locator path does not exist: '{input_path}'")
        sys.exit(1)
        
    filename_base, _ = os.path.splitext(os.path.basename(input_path))
    output_filename = f"{filename_base}_doxygen.py"
    
    with open(input_path, "r", encoding="utf-8") as f:
        source_lines = f.read().splitlines()
        
    source_code = "\n".join(source_lines)
    try:
        root_node = ast.parse(source_code, filename=input_path)
    except SyntaxError as err:
        print(f"Compilation tracking failure. Syntax tree failed generation: {err}")
        sys.exit(1)
        
    root_node.base_name = filename_base
    
    # Run our global AST static usage map gather pass
    analyzer = CodeUsageAnalyzer()
    analyzer.visit(root_node)
    
    insertions = []
    
    def find_nodes(node):
        for child in ast.iter_child_nodes(node):
            # Process typical targets: Classes and Functions
            if isinstance(child, (ast.ClassDef, ast.FunctionDef)):
                indent = child.col_offset + 4
                doc_lines = format_doxygen_block(child, indent_level=indent)
                first_body_node = child.body[0]
                insert_line = first_body_node.lineno - 1
                insertions.append((insert_line, doc_lines))
                find_nodes(child)
                
            # Process target imports blocks
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                indent = child.col_offset
                import_docs = format_import_doxygen(child, analyzer.used_names, indent_level=indent)
                # Place comment block cleanly *above* the actual import line
                insert_line = child.lineno - 1
                insertions.append((insert_line, import_docs))
                
            elif isinstance(child, ast.AST):
                find_nodes(child)

    find_nodes(root_node)
    
    # Sort updates backwards to safeguard slice indexing positioning math
    insertions.sort(key=lambda x: x[0], reverse=True)
    
    modified_lines = list(source_lines)
    for line_idx, doc_lines in insertions:
        modified_lines[line_idx:line_idx] = doc_lines
        
    module_block = format_doxygen_block(root_node, indent_level=0)
    modified_lines = module_block + modified_lines
    
    with open(output_filename, "w", encoding="utf-8") as out_file:
        out_file.write("\n".join(modified_lines) + "\n")
        
    print(f"Success! Merged Doxygen documentation directly into source: '{output_filename}'")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage error layout pattern footprint target missing.")
        print("Run command: python inline_doxygen_generator.py <your_input_target_file.py>")
        sys.exit(1)
        
    process_python_file(sys.argv[1])

