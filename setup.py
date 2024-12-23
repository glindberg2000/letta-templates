from setuptools import setup, find_packages

setup(
    name="letta_templates",
    version="0.2.0",
    description="Templates and tools for Letta AI server",
    author="LettaDev",
    packages=find_packages(),
    install_requires=[
        "letta>=0.6.6",
        "grpcio-tools>=1.68.1",
        "protobuf>=5.26.1",
    ],
)
