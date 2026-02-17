"""
Thirsty-Lang Standard Library Setup
Installation script for the Thirsty-Lang stdlib
"""

from setuptools import setup, find_packages
import os

# Read README
readme_path = os.path.join(os.path.dirname(__file__), 'tarl', 'stdlib', 'README.md')
with open(readme_path, 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='thirsty-lang-stdlib',
    version='1.0.0',
    description='Standard library for Thirsty-Lang (TARL) programming language',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Thirsty-Lang Team',
    author_email='team@thirsty-lang.org',
    url='https://github.com/IAmSoThirsty/Thirsty-Lang',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'pyyaml>=6.0',  # For policy support
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
            'black>=23.0.0',
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    keywords='thirsty-lang tarl programming-language stdlib',
    project_urls={
        'Bug Reports': 'https://github.com/IAmSoThirsty/Thirsty-Lang/issues',
        'Source': 'https://github.com/IAmSoThirsty/Thirsty-Lang',
        'Documentation': 'https://github.com/IAmSoThirsty/Thirsty-Lang/blob/main/tarl/stdlib/README.md',
    },
)
