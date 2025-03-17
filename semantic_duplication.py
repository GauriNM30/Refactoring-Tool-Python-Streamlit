import streamlit as st
import ast
import difflib


class SemanticDuplicateDetector:
    def __init__(self):
        pass

    def are_functions_semantically_duplicate(self, func_code1, func_code2):
        """
        Compare two function codes and return True if they do the same thing, ignoring names and spaces.
        """
        # Strip out variable names and whitespace, focus on operations
        normalized_code1 = self.normalize_code(func_code1)
        normalized_code2 = self.normalize_code(func_code2)
        
        similarity_ratio = self.calculate_similarity(normalized_code1, normalized_code2)
        return similarity_ratio > 0.80  # Consider 80% similarity as the threshold for semantic duplication

    def normalize_code(self, code):
        """
        Simplify the code by removing variable names and making the structure simpler, focusing only on the operations.
        """
        tree = ast.parse(code)
        normalized_code = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                normalized_code.append("def " + node.name + "()")
            elif isinstance(node, ast.If):
                normalized_code.append("if condition:")
            elif isinstance(node, ast.For):
                normalized_code.append("for item in iterable:")
            elif isinstance(node, ast.BinOp):
                normalized_code.append("binary operation")
            elif isinstance(node, ast.Call):
                normalized_code.append("function call")
            elif isinstance(node, ast.Assign):
                normalized_code.append("assignment")
            # You can add more logic here to normalize other structures

        return " ".join(normalized_code)

    def calculate_similarity(self, code1, code2):
        """
        Calculate similarity ratio between two pieces of code using difflib's SequenceMatcher.
        """
        sequence_matcher = difflib.SequenceMatcher(None, code1, code2)
        return sequence_matcher.ratio()

    def extract_functions_from_code(self, code):
        """
        Extract function definitions from the provided Python code.
        Return a list of dictionaries with function name and code.
        """
        tree = ast.parse(code)
        functions = []

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                function_code = ast.unparse(node)
                functions.append({
                    "name": node.name,
                    "code": function_code
                })

        return functions


def main():
    st.title("Semantic Code Duplication Detection")

    # Upload a file (Python code)
    uploaded_file = st.sidebar.file_uploader("Upload Python Code", type=["py"])

    if uploaded_file is not None:
        # Read the uploaded file
        code = uploaded_file.read().decode("utf-8")
        st.sidebar.text("Code uploaded successfully")

        # Show uploaded code in the sidebar
        st.sidebar.code(code, language='python')

        # Initialize the SemanticDuplicateDetector
        detector = SemanticDuplicateDetector()

        # Extract functions from the uploaded code
        functions = detector.extract_functions_from_code(code)
        similar_pairs = []

        # Check for semantic duplication between function pairs
        for i, func1 in enumerate(functions):
            for j, func2 in enumerate(functions):
                if i < j:  # Compare each pair only once
                    code1 = func1['code']
                    code2 = func2['code']
                    
                    are_duplicate = detector.are_functions_semantically_duplicate(code1, code2)
                    
                    if are_duplicate:
                        similar_pairs.append((func1['name'], func2['name']))

        # Show results of semantic duplication
        if similar_pairs:
            st.write("### Semantically Duplicate Functions Detected:")
            for pair in similar_pairs:
                st.write(f"- `{pair[0]}` and `{pair[1]}`")
        else:
            st.write("No semantic duplication detected.")


if __name__ == "__main__":
    main()
