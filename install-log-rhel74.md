
installing bccvl vis on rhel 7.4
================================

Installing as `root`:

```
yum install gcc gcc-c++ make openssl-devel
yum install git 				# already installed
yum install gdbm 				# 1.10-8 already installed
yum install libspatialite 		# installed 4.1.1
yum install mapserver 			# installed qgis-server 2.14
yum install proj 				# got 4.8 already
yum install proj-devel			# installed 4.8
yum install freetype			# got 2.4 already
yum install freetype-devel		# installed 2.4
yum install geos				# got 3.4 already
yum install libgeotiff			# got 4.0 already
yum install mpfr				# installed 3.1
yum install python				# got 2.7.5 already
yum install python-devel		# installs 2.7.5
yum install swig				# installed 2.0.10
yum install freexl				# got 1.0 already
yum install libgeotiff			# got 1.2.5 already
yum install libxml2				# got 2.9 already
yum install libxml2-devel		# installs 2.9
yum install openssl				# got 1.0 already
yum install wget				# got 1.14 already
yum install gd 					# got 2.0 already
yum install giflib				# got 4.1.6 already
yum install giflib-devel		# installed 4.1.6
yum install libjpeg-devel		# installed libjpeg-turbo-devel 1.2.90
yum install libmpc				# installed 1.0.1
yum install libyaml				# got 0.1.4 already
yum install pcre				# got 8.32 already
yum install readline			# got 6.2 already
yum install xz					# got 5.2 already
yum install gdal				# installed 1.11.4
yum install gdal-devel			# installed 1.11.4
yum install gmp					# got 6.0 already
yum install libpng				# got 1.5 already
yum install libpng-devel		# installed 1.5
yum install pip					# installed 8.1
yum install cmake				# installed 3.1
```

**`npm` didnt find**:

```
yum install cloog
yum install isl
yum install jpeg
yum install gfortran
yum install lzlib
yum install pkg-config
```

Then `git clone` as per repo (as `root`, in `/srv` dir)

    [root@wallace-maps srv]#  git clone git://github.com/jcu-eresearch/BCCVL_Visualiser.git

Update `pip` and get a `virtualenv` going with `numpy` in it:

	pip install pip --upgrade    # updates pip to 9.0.1
	pip install virtualenv
	cd /srv/BCCVL_Visualiser/BCCVL_Visualiser/
	virtualenv .
	./bin/pip install setuptools --upgrade    # already up to date
	./bin/pip install numpy --upgrade    # installed 1.13.1
	./bin/pip install scipy==0.13.3
	./bin/pip install matplotlib==1.3.1

Bootstrap the project:

	cd /srv/BCCVL_Visualiser/BCCVL_Visualiser/
	./bin/python bootstrap.py
	./bin/buildout
	./bin/test   


