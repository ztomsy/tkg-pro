

TKG-PRO is a Python3 package for Algo and HF Trading on crypto exchanges based on ccxt and ztom python libraries.

Features:

- ThresholdRecoveryOrder: 
  is aimed to be filled for the setted dest amount and if fails fills on best market price. If the price will drop (or raise) belowe the threshold - order will be filled via taker market price.     
  
- MakerStopLossOrder:
  Start with maker for best amount. Than if price drops above threshold try - recreate order for maker if taker price drops above threshold - than set the taker order. 

Installation
=============


python3 -m pip install -r requirements.txt 
python3 -m pip install -e .

Running the tests: python3 -m unittest -v -b



Usage:
=============


Project structure have been taken from  `<http://www.kennethreitz.org/essays/repository-structure-and-python>`_.
If you want to learn more about ``setup.py`` files, check out `this repository <https://github.com/kennethreitz/setup.py>`_.
