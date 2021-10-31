from setuptools import find_packages, setup
from jaaql.constants import VERSION
import platform

REQUIREMENTS = [i.strip().replace("==", "~=") for i in open("requirements.txt").readlines()]

additional = ["psycopg2~=2.9.1"] if platform.system() == 'Windows' or platform.system() == 'Darwin' else []

setup(
    name='jaaql-middleware-python',
    packages=find_packages(include=['jaaql']),
    version=VERSION,
    url='https://github.com/JAAQL/JAAQL-middleware-python',
    description='The jaaql package, allowing for rapid development and deployment of RESTful HTTP applications',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Software Quality Measurement and Improvement bv',
    author_email="aaron.tasker@sqmi.nl",
    license='Mozilla Public License Version 2.0 with Commons Clause',
    install_requires=REQUIREMENTS + additional
)
