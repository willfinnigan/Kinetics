from setuptools import setup

setup(
  name = 'kinetics',
  packages = ['kinetics'],
  version = '1.3.8',
  license='MIT',
  description = 'Python code to run kinetic models of enzyme reactions',
  author = 'William Finnigan',
  author_email = 'wjafinnigan@gmail.com',
  url = 'https://github.com/willfinnigan/kinetics',
  download_url = 'https://github.com/willfinnigan/kinetics/archive/1.3.8.tar.gz',
  keywords = ['enzyme', 'kinetics', 'modelling'],
  install_requires=['scipy', 'numpy', 'SALib', 'tqdm', 'matplotlib', 'pandas', 'deap', 'seaborn'],
  classifiers=[
    'Development Status :: 3 - Alpha',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3'],
)