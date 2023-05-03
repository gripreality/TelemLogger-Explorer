from setuptools import setup, find_packages

setup(
    name='telemExplorer',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'fastkml',
    ],
    extras_require={
        'gui': ['tkinter'],
    },
    entry_points={
        'console_scripts': [
            'telemexplorer=telemExplorer:main',
        ],
        'gui_scripts': [
            'telemexplorer-gui=telemExplorer:gui_main [gui]',
        ],
    },
)
