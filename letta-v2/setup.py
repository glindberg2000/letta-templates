from setuptools import setup, find_packages

setup(
    name="letta_templates",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "letta",
        "letta-client",
        "python-dotenv"
    ]
) 