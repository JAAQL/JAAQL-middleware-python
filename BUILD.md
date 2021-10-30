# How to build
For the purpose of making the maintainer's life easier, this file has been included in case they forget how to build and push  
Build and push the project with the commands  

    python setup.py sdist bdist_wheel
    twine upload dist/*

And that is it. If you wish to push a candidate version please use version X.Y.ZaN, where N is the alpha version

For docker you can use  

    docker push jaaql/jaaql-middleware-python:1.1.0 jaaql/jaaql-middleware-python:latest  

Do not push alpha versions to latest as well
