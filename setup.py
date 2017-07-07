from setuptools import setup, find_packages

def readme():
    with open("README.rst", "r") as f:
        return f.read()

setup(
    name = "data-depgraph",
    version = "0.4.3",
    packages = find_packages(),

    author = "Nat Wilson",
    author_email = "njwilson23@gmail.com",
    description = "Small dependency resolution library for scientific datasets",
    long_description = readme(),
    url = "https://github.com/njwilson23/depgraph",
    license = "MIT License",
    classifiers = ["Programming Language :: Python :: 2",
                   "Programming Language :: Python :: 2.7",
                   "Programming Language :: Python :: 3",
                   "Programming Language :: Python :: 3.4",
                   "Programming Language :: Python :: 3.5",
                   "License :: OSI Approved :: MIT License"],
)
