from setuptools import setup, find_packages

setup(
    name="letta_templates",
    version="0.9.12",
    description="Templates and tools for Letta AI agents",
    author="G. Lindberg",
    package_dir={"": "letta-v2"},
    packages=find_packages(where="letta-v2"),
    install_requires=[
        "letta-client>=0.1.21",
        "python-dotenv",
        "requests",
        "numpy>=1.17.0",
        "typing-extensions",
        "pydantic"
    ],
    python_requires=">=3.8",
)
