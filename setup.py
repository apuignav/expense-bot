#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import io
from os.path import dirname
from os.path import join

from setuptools import find_packages
from setuptools import setup


def read(*names, **kwargs):
    """Read file."""
    with io.open(join(dirname(__file__), *names),
                 encoding=kwargs.get('encoding', 'utf8')) as file_:
        return file_.read()


setup(name='expensebot',
      version='0.0.0',
      license='BSD 3-Clause License',
      description='Expense tracker Telegram Bot',
      long_description=read('README.md'),
      author='Albert Puig Navarro',
      author_email='albert.puig.navarro@gmail.com',
      url='https://github.com/apuignav/expense-bot',
      packages=find_packages('.'),
      package_data={'expensebot': ['data/*.yaml']},
      include_package_data=True,
      zip_safe=False,
      classifiers=['Programming Language :: Python :: 3.7',
                   'Programming Language :: Python :: 3.11',
                   'Programming Language :: Python :: Implementation :: CPython',
                   ],
      python_requires='>=3.7',
      install_requires=['gspread==5.1.1',
                        'PyYAML==6.0.1',
                        'python-telegram-bot==13.15',
                        'fuzzywuzzy==0.18.0',
                        'python-Levenshtein==0.20.9; python_version < "3.8"',
                        'python-Levenshtein==0.25.1; python_version >= "3.8"',
                        'datefinder==0.7.0',
                        'importlib-resources>=3.0.0; python_version < "3.9"',
                        'setuptools<81',
                        'urllib3==1.26.20'
                        ],
      entry_points={'console_scripts': ['expensebot = expensebot.cli:main']})

# EOF
