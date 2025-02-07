from setuptools import setup, find_packages

setup(
    name="letta-templates",
    version="3.1.1",
    packages=["letta_templates"],  # Explicitly list the package
    package_data={
        "letta_templates": ["docs/**/*"]
    },
    include_package_data=True,  # Add this to use MANIFEST.in
    entry_points={
        'console_scripts': [
            'letta-cli=letta_templates.letta_cli:main',  # Assuming there's a main() function
        ],
    },
    install_requires=[
        "letta-client>=0.1.26",
        "pydantic>=2.10.6",
        "httpx>=0.28.1",
        "anyio>=4.8.0",
        "python-dotenv",
        "requests"
    ],
    author="Plato",
    description="Templates and tools for Letta NPCs",
    long_description=open("docs/README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
) 