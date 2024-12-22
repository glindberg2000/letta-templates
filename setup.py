from setuptools import setup, find_packages

setup(
    name="letta_templates",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "letta>=0.6.6",
        "grpcio-tools>=1.68.1",
        "protobuf>=5.26.1,<6.0dev",
        "pydantic",
        "python-dotenv"
    ],
    author="LettaDev",
    description="Templates and tools for Letta AI server",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
)
