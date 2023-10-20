from setuptools import setup, find_packages
from pathlib import Path

base_dir = Path(__file__).parent
long_description = (base_dir / "README.md").read_text()

setup(
    name='condainer',
    version='0.1.2',
    description='Build, manage, and run compressed squashfs images of Conda environments transparently on HPC or elsewhere.',
    long_description = long_description,
    author='Klaus Reuter',
    author_email='klaus.reuter@mpcdf.mpg.de',
    url='https://gitlab.mpcdf.mpg.de/khr/condainer',
    packages=find_packages(include=['condainer',]),
    install_requires=[
        'PyYAML',
    ],
    entry_points={
        'console_scripts': ['cnd=condainer.main:cli']
    },
)
