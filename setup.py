from setuptools import setup
from Cython.Build import cythonize
import numpy
setup(
    ext_modules=cythonize("random_video_effect.pyx", compiler_directives={'language_level': "3"})
)
