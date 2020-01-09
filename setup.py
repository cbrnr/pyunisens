from setuptools import setup

setup(name='pyunisens',
      version='0.1',
      description='A python implementation of the Unisens standard',
      url='http://github.com/skjerns/pyUnisens',
      author='skjerns',
      author_email='nomail',
      license='GNU 2.0',
      packages=['unisens'],
      install_requires=[
         'numpy',
         'pandas'],
      zip_safe=False)
