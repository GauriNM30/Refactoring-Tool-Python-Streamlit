import ast
import google.generativeai as genai
import os

class Refactoring:
    # ----------------------------------------------------------------
    # Basic Code Smell Detectors
    # ----------------------------------------------------------------
    def detect_long_methods(self, code, threshold=15):
        lines = code.splitlines(keepends=True)
        try:
            tree = ast.parse(code)
        except Exception as e:
            raise Exception(f"Could not parse file: {e}")

        long_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not hasattr(node, "end_lineno"):
                    raise Exception("Your Python version does not support 'end_lineno'. Please use Python 3.8 or higher.")
                start_line = node.lineno - 1  # 0-indexed
                end_line = node.end_lineno     # 1-indexed (exclusive)
                function_lines = lines[start_line:end_line]
                non_empty_lines = [line for line in function_lines if line.strip() != ""]
                if len(non_empty_lines) > threshold:
                    long_methods.append((node.name, len(non_empty_lines)))
        return long_methods

    def detect_long_parameter_list(self, code, threshold=3):
        try:
            tree = ast.parse(code)
        except Exception as e:
            raise Exception(f"Could not parse file: {e}")

        long_params = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                param_count = len(node.args.args)
                if param_count > threshold:
                    long_params.append((node.name, param_count))
        return long_params

    # ----------------------------------------------------------------
    # Duplicate Function Detection and Refactoring (Function-Level)
    # ----------------------------------------------------------------
    def detect_duplicate_functions(self, code, similarity_threshold=0.75):
        """
        Detect duplicate functions based on identical function bodies.
        Ignores the function signature and compares the unparsed bodies.
        """
        try:
            tree = ast.parse(code)
        except Exception as e:
            raise Exception(f"Could not parse file: {e}")
        
        function_map = {}
        duplicates = []
        # Process top-level function definitions.
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                try:
                    # Unparse the function body (ignore the signature)
                    func_body_code = "\n".join([ast.unparse(n) for n in node.body])
                except Exception:
                    func_body_code = ""
                # Normalize by stripping extra whitespace.
                normalized_body = "\n".join(line.strip() for line in func_body_code.splitlines() if line.strip())
                if normalized_body in function_map:
                    duplicates.append((function_map[normalized_body], node.name))
                else:
                    function_map[normalized_body] = node.name
        return duplicates

    def refactor_duplicate_functions(self, code, duplicate_pairs):
        try:
            tree = ast.parse(code)
        except Exception as e:
            raise Exception(f"Could not parse file for refactoring: {e}")
        
        # Build a mapping: duplicate_function -> primary_function.
        mapping = {}
        for primary, duplicate in duplicate_pairs:
            mapping[duplicate] = primary

        new_body = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in mapping:
                primary = mapping[node.name]
                # Build a call with the same arguments.
                call_expr = ast.Call(
                    func=ast.Name(id=primary, ctx=ast.Load()),
                    args=[ast.Name(id=arg.arg, ctx=ast.Load()) for arg in node.args.args],
                    keywords=[]
                )
                # Replace the entire function body with a return call.
                new_node = ast.FunctionDef(
                    name=node.name,
                    args=node.args,
                    body=[ast.Return(value=call_expr)],
                    decorator_list=node.decorator_list
                )
                new_body.append(new_node)
            else:
                new_body.append(node)
        tree.body = new_body
        tree = ast.fix_missing_locations(tree)
        try:
            refactored_code = ast.unparse(tree)
        except Exception as e:
            raise Exception(f"Refactoring failed during unparsing: {e}")
        return refactored_code

    # ----------------------------------------------------------------
    # Duplicate Block Detection and Refactoring (Block-Level)
    # ----------------------------------------------------------------
    def detect_duplicate_blocks(self, code, window_size=2, similarity_threshold=0.75):
        try:
            tree = ast.parse(code)
        except Exception as e:
            raise Exception(f"Could not parse file: {e}")
        
        blocks_list = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                body = node.body
                if len(body) < window_size:
                    continue
                for i in range(len(body) - window_size + 1):
                    block_nodes = body[i:i+window_size]
                    try:
                        block_code = "\n".join([ast.unparse(n) for n in block_nodes])
                    except Exception:
                        block_code = ""
                    tokens = set(block_code.split())
                    blocks_list.append((func_name, i, block_code, tokens))
        
        groups = []
        used = set()
        n = len(blocks_list)
        for i in range(n):
            if i in used:
                continue
            group = [blocks_list[i]]
            used.add(i)
            for j in range(i+1, n):
                if blocks_list[i][0] == blocks_list[j][0]:
                    continue  # ignore blocks from the same function
                if j in used:
                    continue
                tokens_i = blocks_list[i][3]
                tokens_j = blocks_list[j][3]
                if tokens_i and tokens_j:
                    intersection = tokens_i.intersection(tokens_j)
                    union = tokens_i.union(tokens_j)
                    similarity = len(intersection) / len(union) if union else 0
                    if similarity >= similarity_threshold:
                        group.append(blocks_list[j])
                        used.add(j)
            if len(group) > 1:
                groups.append(group)
        return groups

    def refactor_duplicate_blocks(self, code, duplicate_block_groups, window_size=2):
        try:
            tree = ast.parse(code)
        except Exception as e:
            raise Exception(f"Could not parse file for refactoring duplicate blocks: {e}")

        global_new_funcs = {}

        for group in duplicate_block_groups:
            # Use the first occurrence as representative.
            rep_func_name, rep_index, rep_block_code, rep_tokens = group[0]
            free_vars = None
            # Find the representative function node and compute free vars.
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name == rep_func_name:
                    block_nodes = node.body[rep_index:rep_index+window_size]
                    free_vars = self.get_free_vars(block_nodes)
                    break
            if free_vars is None:
                free_vars = set()

            args = ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg=v) for v in sorted(free_vars)],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[]
            )

            candidate = self.analyze_block_functionality(rep_block_code)
            new_func_name = candidate
            suffix = 1
            while new_func_name in global_new_funcs:
                new_func_name = f"{candidate}_{suffix}"
                suffix += 1
            global_new_funcs[new_func_name] = new_func_name

            # Extract the helper body from the representative occurrence.
            helper_body = None
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name == rep_func_name:
                    helper_body = node.body[rep_index:rep_index+window_size]
                    break
            if helper_body is None:
                helper_body = []

            if not helper_body or not isinstance(helper_body[-1], ast.Return):
                if helper_body and isinstance(helper_body[0], ast.Assign) and helper_body[0].targets:
                    first_target = helper_body[0].targets[0]
                    if isinstance(first_target, ast.Name):
                        var_name = first_target.id
                        helper_body.append(ast.Return(value=ast.Name(id=var_name, ctx=ast.Load())))
                else:
                    helper_body.append(ast.Return(value=ast.Constant(value=None)))

            new_helper = ast.FunctionDef(
                name=new_func_name,
                args=args,
                body=helper_body,
                decorator_list=[]
            )

            # Replace each occurrence of the duplicate block with a call to the helper.
            for occurrence in group:
                func_name, start_index, block_code, tokens = occurrence
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == func_name:
                        # Capture return value from a call to newly created helper function to replace duplicate code
                        if start_index < len(node.body) and isinstance(node.body[start_index], ast.Assign):
                            assign_stmt = node.body[start_index]
                            if assign_stmt.targets and isinstance(assign_stmt.targets[0], ast.Name):
                                var_name = assign_stmt.targets[0].id
                                new_stmt = ast.Assign(
                                    targets=[ast.Name(id=var_name, ctx=ast.Store())],
                                    value=ast.Call(
                                        func=ast.Name(id=new_func_name, ctx=ast.Load()),
                                        args=[ast.Name(id=v, ctx=ast.Load()) for v in sorted(free_vars)],
                                        keywords=[]
                                    )
                                )
                            else:
                                new_stmt = ast.Expr(
                                    value=ast.Call(
                                        func=ast.Name(id=new_func_name, ctx=ast.Load()),
                                        args=[ast.Name(id=v, ctx=ast.Load()) for v in sorted(free_vars)],
                                        keywords=[]
                                    )
                                )
                        else:
                            new_stmt = ast.Expr(
                                value=ast.Call(
                                    func=ast.Name(id=new_func_name, ctx=ast.Load()),
                                    args=[ast.Name(id=v, ctx=ast.Load()) for v in sorted(free_vars)],
                                    keywords=[]
                                )
                            )
                        del node.body[start_index:start_index+window_size]
                        node.body.insert(start_index, new_stmt)
                        break

            # Append the new helper function
            tree.body.append(new_helper)

        tree = ast.fix_missing_locations(tree)
        try:
            refactored_code = ast.unparse(tree)
        except Exception as e:
            raise Exception(f"Refactoring duplicate blocks failed during unparsing: {e}")
        return refactored_code

    # ----------------------------------------------------------------
    # Helper Methods
    # ----------------------------------------------------------------
    def get_free_vars(self, nodes):
        """
        Return variables used (loaded) in nodes that are not assigned (stored) in them.
        """
        free_vars = set()
        assigned = set()
        class FreeVarVisitor(ast.NodeVisitor):
            def visit_Name(self, n):
                if isinstance(n.ctx, ast.Load):
                    free_vars.add(n.id)
                elif isinstance(n.ctx, ast.Store):
                    assigned.add(n.id)
        for node in nodes:
            FreeVarVisitor().visit(node)
        return free_vars - assigned

    def analyze_block_functionality(self, code_snippet):
        """
        This is something i wanted to try. Using an LLM to name the newly created function based on the extracted code.
        Use Gemini 1.5 Flash to generate a candidate helper function name in snake case based on the provided code snippet.
        As this is a small model, it did not take much time to run.
        I used prompt engineering to use this model for naming functions.
        """
        genai.configure(api_key="")
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "Analyze the given Python code snippet and return only a meaningful function name in snake case. "
            "Do not include explanations or extra text. Just return a valid Python function name in snake case.\n\n"
            f"Code:\n{code_snippet}"
        )
        response = model.generate_content(prompt)
        suggested_name = response.text.strip().split("\n")[0]
        suggested_name = suggested_name.replace("`", "").strip()
        if suggested_name.isidentifier():
            return suggested_name
        else:
            return "common_block"