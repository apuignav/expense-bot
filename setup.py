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
      classifiers=['Programming Language :: Python :: 3.6',
                   'Programming Language :: Python :: 3.7',
                   'Programming Language :: Python :: Implementation :: CPython',
                   ],
      python_requires='>=3.5',
      install_requires=['gspread==3.1.0',
                        'oauth2client==4.1.3',
                        'pyOpenSSL==19.0.0',
                        'PyYAML==5.1.2',
                        'python-Levenshtein==0.12.0',
                        'python-telegram-bot==12.0.0b1',
                        'fuzzywuzzy==0.17.0',
                        'datefinder==0.7.0',
                        'importlib-resources>3.0.0'
                        ],
      entry_points={'console_scripts': ['expensebot = expensebot.cli:main']})

# EOF
