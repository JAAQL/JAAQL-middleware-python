from setuptools import find_packages, setup
from jaaql.constants import VERSION

REQUIREMENTS = [i.strip().replace("==", "~=") for i in open("requirements.txt").readlines()]

setup(
    name='jaaql-middleware-python',
    packages=find_packages(include=['jaaql.*', 'jaaql']),
    version=VERSION,
    url='https://github.com/JAAQL/JAAQL-middleware-python',
    description='The jaaql package, allowing for rapid development and deployment of RESTful HTTP applications',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Software Quality Measurement and Improvement bv',
    author_email="aaron.tasker@sqmi.nl",
    license='Mozilla Public License Version 2.0 with Commons Clause',
    install_requires=REQUIREMENTS,
    package_data={'': ['config/*.ini', 'scripts/*.sql', 'migrations/*.sql', 'scripts/*.html']},
)
