from setuptools import setup, find_packages

setup(
    name='thebot',
    version='0.1.0',
    description=(
    ),
    keywords='chat irc xmpp basecamp jira fun',
    license = 'New BSD License',
    author="Alexander Artemenko",
    author_email='svetlyak.40wt@gmail.com',
    url='http://github.com/svetlyak40wt/thebot/',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Server',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
    ],
    packages=find_packages(),
    scripts=['scripts/thebot'],
    install_requires = open('requirements/base.txt').readlines()
)