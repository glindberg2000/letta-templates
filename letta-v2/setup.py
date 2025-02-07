from setuptools import setup, find_packages

setup(
    name="letta-templates",
    version="3.1.0",
    packages=find_packages(),
    package_data={
        "letta_templates": ["docs/**/*"]  # Include all docs
    },
    install_requires=[
        "letta-client>=0.1.0",
        "python-dotenv>=0.19.0",
        "requests>=2.26.0",
        "typing-extensions>=4.0.0"
    ],
    author="Plato",
    description="Templates and tools for Letta NPCs",
    long_description=open("docs/README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
) 