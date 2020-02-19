import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gtagora-app",
    version="0.0.1",
    author="Martin Bührer",
    author_email="info@gyrotools.com",
    description="Python version of the Agora app",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gyrotools/gtagora-app-py",
    packages=setuptools.find_packages(),
    install_requires=[
        'websockets',
        'gtagora-connector'
    ],
    python_requires='>=3.6.0',
    entry_points={
        'console_scripts': ['gtagoraapp=gtagoraapp.agoraapp:run'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
