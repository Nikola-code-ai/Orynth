import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'aerolab_simulation'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'resource'), glob('resource/*.json')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'config'), glob('config/*.json5')),
        (os.path.join('share', package_name, 'scripts'), glob('scripts/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='AeroLab',
    maintainer_email='team@aerolab.todo',
    description='Aerolab Simulation Package for 5-drone swarm and formation',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'flock_orchestrator = aerolab_simulation.flock_orchestrator:main',
            'tf_static_bridge = aerolab_simulation.tf_static_bridge:main'
        ],
    },
)
