from setuptools import setup, find_packages

setup(
    name='android_music_automation',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'uiautomator2>=2.16.0',
        'pytest>=7.0.0',
        'PyYAML>=6.0.0',
    ],
    author='Serhii Drobot',
    author_email='drobot@rebelinternet.eu',
    description='Automated control system for managing multiple music apps on Android devices',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    python_requires='>=3.8',
)