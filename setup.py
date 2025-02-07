from setuptools import setup, find_namespace_packages

setup(
    name="letta-templates",
    version="3.1.0",
    package_dir={"": "letta-v2"},
    packages=find_namespace_packages(where="letta-v2"),
    package_data={
        "letta_templates": ["docs/**/*"]
    },
    install_requires=[
        "letta-client>=0.1.26",
        "pydantic>=2.10.6",
        "httpx>=0.28.1",
        "anyio>=4.8.0",
        "python-dotenv",
        "requests"
    ],
    author="Plato",
    description="Templates and tools for Letta NPCs",
    long_description=open("docs/README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
) 