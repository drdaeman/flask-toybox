#!/usr/bin/env python

from setuptools import setup

setup(
    name="Flask-ToyBox",
    version="0.0.2",
    url="https://github.com/drdaeman/flask-toybox/",
    license="MIT",
    author="Aleksey Zhukov",
    author_email="drdaeman@drdaeman.pp.ru",
    description="Create somehow-RESTful HTTP APIs with Flask",
    long_description=open("README.rst", "r").read(),
    packages=["flask_toybox"],
    test_suite="tests",
    zip_safe=False,
    platforms="any",
    install_requires=["Flask >=0.9"],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Web Environment",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 2 :: Only",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ]
)