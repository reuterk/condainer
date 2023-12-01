from pathlib import Path
from setuptools import setup, find_packages


def get_long_description():
    base_dir = Path(__file__).parent
    return (base_dir / "README.md").read_text()


def get_version_string():
    base_dir = Path(__file__).parent
    version_py = (base_dir / "condainer" / "version.py").read_text()
    ver = {}
    exec(version_py, ver)
    return ver['get_version_string']()

setup(
    name='condainer',
    version=get_version_string(),
    description='Build, manage, and run compressed squashfs images of Conda environments transparently on HPC or elsewhere.',
    long_description = get_long_description(),
    author='Klaus Reuter',
    author_email='klaus.reuter@mpcdf.mpg.de',
    url='https://gitlab.mpcdf.mpg.de/mpcdf/condainer',
    packages=find_packages(include=['condainer',]),
    install_requires=[
        'PyYAML',
    ],
    entry_points={
        'console_scripts': ['cnd=condainer.main:cli']
    },
)
