import streamlit as st
import streamlit.components.v1 as components
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from refactoring import Refactoring
import re

st.set_page_config(page_title="Code Smell Detector", layout="centered", initial_sidebar_state="expanded")
st.title("Code Smell Detector by Gauri")

def highlight_code(code, snippets):
    """
    Highlight the code using Pygments and wrap each "snippet" with a yellow background. Returns HTML to display.
    """
    # Generate HTML highlighted code.
    formatter = HtmlFormatter(nowrap=True)
    highlighted_code = highlight(code, PythonLexer(), formatter)
    # For each snippet, wrap its occurrences with a yellow span.
    for snippet in snippets:
        pattern = re.escape(snippet)
        # Wrap with <span> having yellow background.
        highlighted_code = re.sub(
            pattern,
            f'<span style="background-color: yellow; font-weight: bold;">{snippet}</span>',
            highlighted_code
        )
    # Wrap in a <pre> tag to mimic st.code styling.
    style = f"<style>{formatter.get_style_defs('.highlight')}</style>"
    html_code = f"{style}<pre class='highlight'>{highlighted_code}</pre>"
    return html_code

def main():
    st.markdown("""
        **Welcome to the Code Refactor Tool! Let’s streamline your code :)**
        
        1. Upload a Python file.
        2. The tool will analyze the code for:
           - Long methods (more than 15 non-empty lines)
           - Long parameter lists (more than 3 parameters)
           - Duplicate code (semantically duplicate)
        3. If duplicate code is found, you will have the option to refactor it.
    """)
    
    uploaded_file = st.file_uploader("Upload a Python file", type=["py"])
    if not uploaded_file:
        st.warning("Please upload a .py file.")
        return

    try:
        code = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return

    refactorer = Refactoring()
    detected_smells = []

    # Detect long methods.
    try:
        long_methods = refactorer.detect_long_methods(code)
        if long_methods:
            details = [f"Function {name} has {count} non-empty lines." for name, count in long_methods]
            detected_smells.append({"type": "Long Method", "details": details})
    except Exception as e:
        st.error(str(e))

    # Detect long parameter lists.
    try:
        long_params = refactorer.detect_long_parameter_list(code)
        if long_params:
            details = [f"Function {name} has {count} parameters." for name, count in long_params]
            detected_smells.append({"type": "Long Parameter List", "details": details})
    except Exception as e:
        st.error(str(e))

    # Detect duplicate code
    try:
        duplicate_funcs = refactorer.detect_duplicate_functions(code)
        if duplicate_funcs:
            details = [f"Duplicate functions detected: {primary} and {dup}" for primary, dup in duplicate_funcs]
            detected_smells.append({"type": "Duplicate Function", "details": details})
    except Exception as e:
        st.error(str(e))
    
    try:
        duplicate_blocks = refactorer.detect_duplicate_blocks(code)
        if duplicate_blocks:
            details = []
            for group in duplicate_blocks:
                func_names = sorted({occ[0] for occ in group})
                indices = sorted({str(occ[1]) for occ in group})
                details.append(f"In functions {', '.join(func_names)}, duplicate block starts at indices: {', '.join(indices)}")
            detected_smells.append({"type": "Duplicate Block", "details": details})
    except Exception as e:
        st.error(str(e))
    
    # Highlight Code smells
    smell_snippets = []
    for smell in detected_smells:
        for detail in smell["details"]:
            m = re.search(r"Function (\w+)", detail)
            if m:
                smell_snippets.append(m.group(1))
            m = re.search(r"Duplicate functions detected: (\w+)\s+and\s+(\w+)", detail)
            if m:
                smell_snippets.append(m.group(1))
                smell_snippets.append(m.group(2))
            m = re.search(r"In functions ([\w,\s]+),", detail)
            if m:
                names = m.group(1).split(',')
                smell_snippets.extend(name.strip() for name in names if name.strip())
    smell_snippets = list(set(smell_snippets))
    
    highlighted_uploaded_code = highlight_code(code, smell_snippets)
    
    # Display the highlighted code in the sidebar
    with st.sidebar:
        st.title("Uploaded Code")
        st.code(code, language="python")
        st.markdown("### Uploaded Code with Highlights")
        components.html(highlighted_uploaded_code, height=400, scrolling=True)
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.info("Analyzing Code...")
    if detected_smells:
        st.error("Code Smells Detected:")
        for smell in detected_smells:
            st.subheader(smell["type"])
            for detail in smell["details"]:
                st.write(f'<p style="color:orange;">{detail}</p>', unsafe_allow_html=True)
    else:
        st.success("No code smells detected.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <style>
        .right-sidebar {
            position: fixed;
            top: 0;
            right: 0;
            width: 300px;
            height: 100%;
            padding: 20px;
            box-shadow: -2px 0 5px rgba(0,0,0,0.1);
        }
        .main-content {
            margin-right: 320px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Enable refactoring if duplicate code is detected.
    if duplicate_funcs or duplicate_blocks:
        if st.button("Refactor Code"):
            try:
                refactored_code = code
                if duplicate_funcs:
                    refactored_code = refactorer.refactor_duplicate_functions(refactored_code, duplicate_funcs)
                if duplicate_blocks:
                    refactored_code = refactorer.refactor_duplicate_blocks(refactored_code, duplicate_blocks)
                st.subheader("Refactored Code Preview:")
                st.code(refactored_code, language="python")
                st.download_button("Download Refactored Code", refactored_code, file_name="refactored_code.py")
            except Exception as e:
                st.error(str(e))
    else:
        st.success("No duplicate code detected, refactoring not available.")

if __name__ == "__main__":
    main()