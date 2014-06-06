from fabric.api import local

def test():
    local('env/bin/tox')
