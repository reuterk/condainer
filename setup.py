from setuptools import setup, find_packages

setup(
    name='condainer',
    version='0.1.0',
    description='Create, manage, run Conda environments using compressed squashfs images.',
    author='Klaus Reuter',
    author_email='klaus.reuter@mpcdf.mpg.de',
    url='https://gitlab.mpcdf.mpg.de/khr/condainer',
    packages=find_packages(include=['condainer',]),
    install_requires=[
        'PyYAML',
    ],
    entry_points={
        'console_scripts': ['condainer=condainer.main:cli']
    },
)

