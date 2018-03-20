from setuptools import setup, find_packages

setup(
    name='py_adb',
    version='0.0.1',
    description='python adb imprementation based on libusb1',
    longer_description='''
python adb imprementation based on libusb1
inspired by https://github.com/google/python-adb
''',
    maintainer='yandex load team',
    maintainer_email='load-public@yandex-team.ru',
    url='https://github.com/nettorta/py-adb',
    packages=find_packages(exclude=["tests", "tmp", "docs", "data"]),
    install_requires=[
    ],
    setup_requires=[
    ],
    tests_require=[
    ],
    entry_points={
        'console_scripts': [
            'py_adb = py_adb.demo:main',
        ],
    },
    license='MPLv2',
    package_data={},
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Testing :: Traffic Generation',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    use_2to3=True, )
