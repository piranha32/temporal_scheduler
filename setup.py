import io
import os
import re

from setuptools import find_packages
from setuptools import setup


# doc: https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/
# build:
#      all: python -m build
#      wheel: python -m build --wheel
#      source: python -m build --sdist
# upload to testpypi: twine upload --repository testpypi dist/*
# upload to pypi: twine upload --repository testpypi dist/*

def read(filename):
    filename = os.path.join(os.path.dirname(__file__), filename)
    text_type = type(u"")
    with io.open(filename, mode="r", encoding='utf-8') as fd:
        return re.sub(text_type(r':[a-z]+:`~?(.*?)`'), text_type(r'``\1``'), fd.read())


setup(
    name="temporal_scheduler",
    version="2022.04.18",
    url="https://github.com/piranha32/temporal_scheduler",
    license='GPLv3',

    author="Jacek Radzikowski",
    author_email="jacek.radzikowski@gmail.com",

    description="Lightweight temporal scheduler for thread  synchronization and code execution",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",

    packages=find_packages(exclude=('tests',)),

    install_requires=['sortedcontainers'],
    python_requires='>=3',

    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    test_suite="tests",

)
