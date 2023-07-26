from setuptools import setup
from distutils.util import convert_path

version_path = convert_path('server/npg/version.py')
namespace = {}
with open(version_path) as ver_file:
    exec(ver_file.read(), namespace)

setup(
    version=namespace['__version__'],
)
