from setuptools import setup, find_packages

setup(
    name="letta-templates",
    version="3.0.0",
    description="Templates and tools for Letta AI agents",
    author="G. Lindberg",
    author_email="greglindberg@gmail.com",
    packages=find_packages(where="letta-v2"),
    package_dir={"": "letta-v2"},
    install_requires=[
        "letta-client>=0.1.26",
        "pydantic>=2.10.6",
        "httpx>=0.28.1",
        "anyio>=4.8.0",
        "python-dotenv",
        "requests"
    ],
    python_requires=">=3.8",
)
