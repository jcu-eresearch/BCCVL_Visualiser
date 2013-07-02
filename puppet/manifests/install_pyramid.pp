class install_pyramid {

  # setup virtualenv
  #exec { 'virtualenv --no-site-packages env':
  #  command => 'virtualenv --no-site-packages env',
  #  cwd     => '/vagrant',
  #  path    => '/usr/local/bin/:/usr/bin/:/bin/',
  #  timeout => 10 * 60,                        # Allow 10 mins to install
  #  creates => '/vagrant/env',
  #}

  # install the pyramid libraries
  #exec { 'easy_install pyramid':
  #  command => 'easy_install pyramid',
  #  cwd     => '/vagrant/env/bin',
  #  path    => '/vagrant/env/bin/',
  #  timeout => 30 * 60,                        # Allow 30 mins to install
  #  require => Exec['virtualenv --no-site-packages env'],
  #  creates => '/vagrant/env/bin/pcreate',
  #}

  exec { 'python2.7 bootstrap.py':
    cwd     => '/vagrant/WebApp',
    path    => '/usr/local/bin/:/usr/bin/:/bin/:/usr/pgsql-9.2/bin/',
    timeout => 10 * 60,                        # Allow 10 mins to install
    creates => '/vagrant/WebApp/bin',
  }
  ~>
  exec { 'buildout':
    cwd     => '/vagrant/WebApp',
    path    => '/vagrant/WebApp/bin/:/usr/local/bin/:/usr/bin/:/bin/:/usr/pgsql-9.2/bin/',
    timeout => 30 * 60,                        # Allow 30 mins to install
  }

}

include install_pyramid
