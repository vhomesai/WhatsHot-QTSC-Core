from setuptools import setup, find_packages

setup(
    name="triqee",
    version="3.1.0",
    description="Triqee Sovereign Quantum Architecture, Multi-Cloud QPU Arbitrage SDK & Gemini 4 Argon Co-Processor",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Jon Vierk & CAO Trixee",
    author_email="jon@triqee.com",
    url="https://doi.org/10.5281/zenodo.23045297",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.9",
    install_requires=[
        "qiskit>=1.0.0",
        "amazon-braket-sdk>=1.80.0",
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "yfinance>=0.2.0",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "triqee=triqee.cli:main",
        ],
    },
)
