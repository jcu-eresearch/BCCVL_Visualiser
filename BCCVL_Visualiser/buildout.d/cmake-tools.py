
# helpers for building mapserver by cmake
import os

def make_build_dir(options, buildout_dir, env):
	''' make the build dir that cmake insists on '''
	print('options')
	print(options)
	print('buildoutdir')
	print(buildout_dir)
	print('env')
	print(env)

	# make a build dir in the compile directory
	
	os.mkdir(os.path.join(options['compile-directory'], 'mapserver-' + options['version'], 'build'))



