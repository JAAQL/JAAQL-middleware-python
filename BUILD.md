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

## Component Tests
Please run the following component tests before pushing a final build. In order to do that please run the following docker commands, replacing the email environment variables
    
    docker build -t jaaql/jaaql-middleware-python -f docker/Dockerfile .
    docker tag jaaql/jaaql-middleware-python local-jaaql-middleware-python
    docker build -t jaaql-middleware-python-ct -f docker/Dockerfile-component .
    docker run -e POSTGRES_PASSWORD=123456 -e JAAQL_VAULT_PASSWORD=pa55word -e JAAQL_EMAIL_CREDENTIALS=eyJDVFAiOiAiVGhlIHdyb25nIHBhc3N3b3JkIn0= -e COMPONENT_EMAIL_PASSWORD=rawcomponentemailpassword jaaql-middleware-python-ct

Add the environment variable

    -e FAST_JAAQL_COMPONENT_TESTS=True

If you wish to speed up component tests