import os
import pkg_resources

def view_docs():
    """Print the response handling documentation."""
    try:
        doc_path = pkg_resources.resource_filename('letta_templates', 'docs/response_handling.md')
        print(f"\nLooking for docs at: {doc_path}")
        with open(doc_path, 'r') as f:
            print(f.read())
    except Exception as e:
        print(f"\nError loading docs from {doc_path}: {e}")
        print("\nDocs can also be found at:")
        print("https://github.com/glindberg2000/letta-templates/blob/v0.9.8/letta-v2/letta_templates/docs/response_handling.md")
