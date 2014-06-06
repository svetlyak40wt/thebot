import sys

from setuptools import setup, find_packages


if sys.version > '3':
    requirements = open('requirements/production3.txt').readlines()
else:
    requirements = open('requirements/production.txt').readlines()

setup(
    name='thebot',
    version='0.3.3',
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
    package_data={'thebot': ['requirements/*.txt']},
    scripts=['scripts/thebot'],
    install_requires=requirements,
)
