from setuptools import find_packages, setup
REQUIREMENTS = [i.strip().replace("==", "~=") for i in open("requirements.txt").readlines()]

setup(
    name='jaaql-middleware-python',
    packages=find_packages(include=['jaaql']),
    version='1.0.0',
    url='https://github.com/JAAQL/JAAQL-middleware-python',
    description='The jaaql package, allowing for rapid development and deployment of RESTful HTTP applications',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Software Quality Measurement and Improvement bv',
    author_email="aaron.tasker@sqmi.nl",
    license='LICENSE.txt',
    install_requires=REQUIREMENTS
)
