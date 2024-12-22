from setuptools import setup, find_packages

setup(
    name="letta_templates",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "letta>=0.1.0",
    ],
    author="LettaDev",
    description="Templates and tools for Letta AI server",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)
