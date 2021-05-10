#!/usr/bin/env python3
import os
from setuptools import setup
import shutil


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


if not os.path.exists('build'):
    os.mkdir('build')
scripts = (
    'main.py',
    # Rarely used
    # Adding these will make tab complete slightly worse
    # 'gmap2gxiv.py'
    # 'util.py',
)
scripts_dist = []
for script in scripts:
    # Make script names more executable like
    if script == "main.py":
        dst = 'build/pr0nmap'
    else:
        dst = 'build/pr0nmap-' + script.replace('.py', '').replace('_', '-')
    shutil.copy(script, dst)
    scripts_dist.append(dst)

setup(
    name="pr0nmap",
    version="2.0.0",
    author="John McMaster",
    author_email='JohnDMcMaster@gmail.com',
    description=("siliconpr0n.org map generator."),
    license="BSD",
    keywords="leaflet",
    url='https://github.com/JohnDMcMaster/pr0nmap',
    packages=['pr0nmap'],
    scripts=scripts_dist,
    install_requires=[
    ],
    long_description="pr0nmap go vroom",
    classifiers=[
        "License :: OSI Approved :: BSD License",
    ],
)
