from setuptools import setup, find_packages

setup(
    name="letta_templates",
    version="0.9.3",
    description="Templates and tools for Letta AI agents",
    author="G. Lindberg",
    packages=find_packages(),
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