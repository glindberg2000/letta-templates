from setuptools import setup, find_packages

setup(
    name="letta_templates",
    version="0.2.0",  # Incremented for persona memory updates
    description="Templates and tools for Letta AI agents",
    author="Ella AI Care",
    author_email="support@ella-ai-care.com",
    packages=find_packages(),
    install_requires=[
        "letta>=0.1.0",
        "python-dotenv>=0.19.0",
        "requests>=2.26.0"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)