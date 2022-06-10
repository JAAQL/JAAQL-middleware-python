# Docker Instructions
For those entirely new to docker, the following will be helpful so you can setup JAAQL with no knowledge of docker

Please download and install docker

    curl -fsSL https://get.docker.com -o get-docker.sh
    sh ./get-docker.sh  
    
## Using pre-built image
For ease of use, you can pull our pre-built docker image to get you started quickly. If speed and simplicity is the name of the game, we recommend you do this

    mkdir JAAQL-middleware-python
    cd JAAQL-middleware-python
    docker pull jaaql/jaaql-middleware-python:latest

Please now jump to the 'Running docker image section'

## Building your own image
Please run the following commands to clone the repository and navigate to it

    git clone https://github.com/JAAQL/JAAQL-middleware-python.git
    cd JAAQL-middleware-python
    sudo docker build -t jaaql/jaaql-middleware-python -f docker/Dockerfile .
    
## Setup mount directories
Make the directories you will use as bind mounts within the root JAAQL-middleware-python directory. These offer accessible volumes which persist after your container shuts down. The database is dealt with as a separate anonymous docker volume
    
    mkdir -p log/nginx
    mkdir -p www
    mkdir -p letsencrypt/live

## Running docker image
Please replace the _POSTGRES_PASSWORD_ and _JAAQL_VAULT_PASSWORD_ with different secure passwords of your choosing  
Please replace the _SERVER_ADDRESS_ build arg with your server's ip e.g. 93.184.216.34  
Alternatively if your server has a domain name, please replace it with that e.g. example.com. DO NOT USE www. in the URL. If using https, everything will be forced to www.example.com, else only example.com will be available  
If using https you must use a domain name  

    sudo docker run -d \
        --mount type=bind,source="$(pwd)"/log,target=/JAAQL-middleware-python/log \
        --mount type=bind,source="$(pwd)"/www,target=/JAAQL-middleware-python/www \
        --mount type=bind,source="$(pwd)"/log/nginx,target=/var/log/nginx \
        --name jaaql-middleware-container \
        -p 80:80 \
        -e IS_HTTPS=FALSE \
        -e POSTGRES_PASSWORD=123456 \
        -e JAAQL_VAULT_PASSWORD=pa55word \
        -e SERVER_ADDRESS=YOUR_SERVER_ADDRESS \
        -e MFA_LABEL=YOUR_APP_NAME \
        jaaql/jaaql-middleware-python

For those wishing that this container boots when your system boots (on startup), please add the following argument to the above

    --restart unless-stopped \

Additional lines can be used

    -e DO_AUDIT=FALSE \
    -e FORCE_MFA=FALSE \
    -e INVITE_ONLY=FALSE \
    -e JAAQL_EMAIL_CREDENTIALS=base64encodedcredentials \
    -e JEQL_VERSION=2.1.2 \

JAAQL_EMAIL_CREDENTIALS provides SMTP/IMAP email credentials into the JAAQL server. Base64 encoded json dict of the format { \"my_account_name\": \"my_account_password\" }  
JEQL_VERSIOn specifies the version of JEQL to use
    
## Usage
Please use the command
    
    cat log/gunicorn.log
    
Which will output something like the following

    MFA label is set to default. This isn't a security issue but adds a nice name when added to authenticator apps via QR codes. You can change in the config
    INSTALL KEY: 3278649c-ec9c-41d9-bd8c-3f17fff6e5be
    [2021-10-23 13:19:03 +0000] [28] [INFO] Starting gunicorn 20.1.0
    [2021-10-23 13:19:03 +0000] [28] [INFO] Listening at: unix:jaaql.sock (28)
    [2021-10-23 13:19:03 +0000] [28] [INFO] Using worker: gevent
    [2021-10-23 13:19:03 +0000] [340] [INFO] Booting worker with pid: 340
    [2021-10-23 13:19:03 +0000] [341] [INFO] Booting worker with pid: 341
    [2021-10-23 13:19:03 +0000] [342] [INFO] Booting worker with pid: 342
    [2021-10-23 13:19:04 +0000] [343] [INFO] Booting worker with pid: 343
    [2021-10-23 13:19:04 +0000] [344] [INFO] Booting worker with pid: 344

Here you will see the installation key. You can access swagger via http(s)://your_address/swagger/jaaql_internal_api.html

## Allowing db access outside the container
If you wish to gain access to the database outside of your container then please add the argument

    -p 5432:5432 \

This will open up the database port to be accessible outside. You can use psql to hook up to the database, we recommend installing on centos as follows

    dnf install postgresql

And then accessing the database as such

    psql -U postgres -h 127.0.0.1 -p 5432 -d jaaql

You will then be prompted for a password

## Using HTTPS
If you wish to use https please adjust the 'docker run' command to have the following arguments. The email is used by certbot for registration and recovery contact. An email will also be sent if the certificates cannot auto renew. Please do not remove the -p 80:80 argument as we require port 80 open so those accessing the website with http are redirected to https

    -p 443:443 \
    -e IS_HTTPS=TRUE \
    -e HTTPS_EMAIL=mail@example.com \
    --mount type=bind,source="$(pwd)"/letsencrypt,target=/etc/letsencrypt \

If you take a container that has been ran using IS_HTTPS=TRUE and run it with IS_HTTPS=FALSE you will lose the certificates and need to reconfigure. It is recommended that you backup your certificate

## Extending JAAQL
For those who wish to use JAAQL as a package, there is an example Dockerfile (Dockerfile-extend) that when built will run your app in the same way as JAAQL is ran (gunicorn, nginx, pypy, https etc.). Please make sure there is a wsgi.py in your project base which has a build_app function that returns a flask object. For example  
  
    from jaaql.jaaql import create_app

    def build_app(*args, **kwargs):
        return create_app(is_gunicorn=True, **kwargs)
    
For a better example please see the example application at https://github.com/JAAQL/JAAQL-example-app  
Please note the use of INSTALL_PATH in the Dockerfile. Setting this correctly is essential. Please place any requirements in requirement.txt in your projects base file and they will be installed. Using pip will not work as the image is based on pypy  

# Troubleshooting
If you are seeing a 404 when trying to access http(s)://your_address/swagger/jaaql_internal_api.html, you have likely not replaced the server address in the run command
