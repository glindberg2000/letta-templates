from setuptools import setup, find_packages

setup(
    name="letta_templates",
    version="0.9.2",
    description="Templates and tools for Letta AI agents",
    author="G. Lindberg",
    packages=find_packages(),
    install_requires=[
        "letta==0.6.6",
        "python-dotenv",
        "requests",
        "numpy>=1.17.0"
    ],
    python_requires=">=3.8",
)
