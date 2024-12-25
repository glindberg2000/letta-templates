from setuptools import setup, find_packages

setup(
    name="letta_templates",
    version="0.2.7",
    description="Templates and tools for Letta AI server",
    author="LettaDev",
    packages=find_packages(),
    install_requires=[
        "letta>=0.2.0",
        "python-dotenv>=0.19.0"
    ],
)
