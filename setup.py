# -*- coding: utf-8 -*-

# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='tkgpro',
    version='0.1.0',
    description='Some advanced classes based on tkg-core package',
    long_description=readme,
    author='Ivan Averin',
    author_email='i.averin@gmail.com',
    url='',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)

