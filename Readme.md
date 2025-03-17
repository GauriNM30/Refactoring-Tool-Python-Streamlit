# Code Refactor Tool

Welcome to the Code Refactor Tool! This tool helps streamline your Python code by detecting long methods, overloaded parameter lists, and semantically duplicate code. 

## Setup

### 1. Insert Gemini API Key
To use the refactoring functionality, you need to insert your Gemini API key into the `refactoring.py` file. Go to line number 302 in the `refactoring.py` file and add your Gemini API key there.

### 2. Running the App
To run the main application, use the following command:
```bash
streamlit run app.py

### 3. Running the Semantic Code Detector
To run the semantic code duplication detector separately, use the command:
```bash
streamlit run semantic_duplication.py

Note: To keep the original solution intact, I added the semantic duplicate detector functionality in a completely separate file, semantic_duplication.py.

##Features
Detect long methods

Find overloaded parameter lists

Detect and refactor semantically duplicate code

Enjoy refactoring your code with ease!
