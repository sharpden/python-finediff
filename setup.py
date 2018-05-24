import sys
import os
from setuptools import setup, find_packages

try:
    readme = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()
except:
    readme = ''

version = '0.0.1'

install_requires = []

setup(
    name='python-finediff',
    version=version,
    description="Python port of https://github.com/gorhill/PHP-FineDiff",
    long_description=readme,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Topic :: Utilities"
    ],
    keywords='diff, finediff',
    author='sharpden',
    author_email='sharp-c@yandex.ru',
    url='https://github.com/sharpden/python-finediff',
    py_modules=['finediff'],
    license='MIT',
    install_requires=install_requires,
)