from setuptools import setup, find_packages

setup(
    name="letta_templates",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "letta>=0.6.6",
        "protobuf<5.0.0",
    ],
    author="LettaDev",
    description="Templates and tools for Letta AI server",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
)
