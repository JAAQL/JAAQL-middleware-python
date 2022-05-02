# How to build
## JAAQL
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

## JEQL
JEQL is written in es6 and uses javascript modules. For someone stuck in the early-mid 2010s, it may be desirable for them to not use JEQL as a module. In order to support them, we can compile this es6 code using babel to es5. In order to do this you first must install node.js and then run

    npm -i

Which will install babel. Babel can then compile the JEQL package in the apps directory using the following commands in windows and unix respectively

    .\node_modules\.bin\babel .\jaaql\apps\JEQL --out-dir .\jaaql\apps\JEQL-es5
	./node_modules/.bin/babel ./jaaql/apps/JEQL --out-dir ./jaaql/apps/JEQL-es5
