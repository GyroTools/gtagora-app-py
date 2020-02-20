# gtagora-app-py [![Build Status](https://travis-ci.org/gyrofx/gtagora-connector-py.svg?branch=master)](https://travis-ci.org/gyrofx/gtagora-connector-py)

Helper app for Agora (http://www.gyrotools.com/gt/index.php/products/agora)

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install gtagora-app.

```bash
pip install gtagora-app
```

Currently gtagora-app supports python 3.6 and 3.7.

## Basic usage

### Run
Run the app with
```bash
gtagoraapp
```

### Setup
when the app is run for the first time, a setup process is started. You will be prompted for the Agora URL, your 
credentials and path settings. 
The setup can also be started manually by calling:
```bash
gtagoraapp --setup
```

