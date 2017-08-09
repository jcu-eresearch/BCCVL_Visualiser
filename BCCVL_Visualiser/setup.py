import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid >= 1.4.4',
#    'psycopg2',
#    'SQLAlchemy',
#    'GeoAlchemy2',


    # mapscript and GDAL is now installed during the buildout.
    # it is installed using the cmmi recipe (configure && make && make install)
    #
    # For travis, it's installed via packages
    #
    'GDAL >= 1.11.2',
    'mapscript >= 6.2.1',      # Python Map Server implementation
    'zope.interface >= 4.1.0',

    'dogpile.cache',    # cache regions, lets you cache the result of queries
    'Pillow',           # Python Imaging Library
    'shapely',          # PostGIS-ish operations in python
    'transaction',
    'pyramid_tm',
    'pyramid_debugtoolbar',
    'zope.sqlalchemy',
    'requests',
    'waitress',
    'pyramid_xmlrpc',
    'numpy',
    'matplotlib = 2.0.1',
    'scipy',
    'repoze.vhm',       # Use repoze middleware for Virtual Host management
    'csvvalidator',
    ]

setup(name='BCCVL_Visualiser',
      version='0.0',
      description='BCCVL_Visualiser',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='bccvl_visualiser',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = bccvl_visualiser:main
      [console_scripts]
      """,
      )
