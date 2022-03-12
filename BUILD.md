# How to build
For the purpose of making the maintainer's life easier, this file has been included in case they forget how to build and push  
To build you need the following packages

    pip install wheel
    pip install twine

Build and push the project with the commands  

    python setup.py sdist bdist_wheel
    twine upload dist/*

And that is it. If you wish to push a candidate version please use version X.Y.ZaN, where N is the alpha version

For docker you can need to build with the tag (e.g. :1.1.0) and then use the following. If you supply no tag then it defaults to latest  

    docker push jaaql/jaaql-middleware-python:1.1.0  

Do not push alpha versions to latest
