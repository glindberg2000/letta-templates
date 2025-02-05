from setuptools import setup, find_packages

setup(
    name="letta-templates",
    version="0.9.7",
    description="Templates and tools for Letta AI agents",
    author="G. Lindberg",
    package_dir={"": "letta-v2"},
    packages=find_packages(where="letta-v2"),
    package_data={
        "letta_templates": ["docs/*.md"]
    },
    install_requires=[
        "letta-client==0.1.21",
        "pydantic==2.10.6",
        "httpx==0.28.1",
        "anyio==4.8.0",
        "python-dotenv",
        "requests",
        "numpy>=1.17.0",
        "typing-extensions"
    ],
    python_requires=">=3.8",
) 