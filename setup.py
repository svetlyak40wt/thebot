import os.path
import sys

from setuptools import setup, find_packages


if sys.version > '3':
    req_filename = 'requirements/production3.txt'
else:
    req_filename = 'requirements/production.txt'

if os.path.exists(req_filename):
    requirements = open(req_filename).readlines()
else:
    # this branch should work only when running under the tox
    requirements = []


setup(
    name='thebot',
    version='0.4.1',
    description=(
    ),
    keywords='chat irc xmpp basecamp jira fun',
    license = 'New BSD License',
    author="Alexander Artemenko",
    author_email='svetlyak.40wt@gmail.com',
    url='http://github.com/svetlyak40wt/thebot/',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    packages=find_packages(),
    scripts=['scripts/thebot'],
    install_requires=requirements,
)
