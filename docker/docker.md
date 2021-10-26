# Docker Instructions
For those entirely new to docker, the following will be helpful so you can setup JAAQL with no knowledge of docker

Please download and install docker

    curl -fsSL https://get.docker.com -o get-docker.sh
    sh ./get-docker.sh  
    
## Using pre-built image
For ease of use, you can pull our pre-built docker image to get you started quickly. If speed and simplicity is the name of the game, we recommend you do this

    mkdir JAAQL-middleware-python
    cd JAAQL-middleware-python
    docker pull jaaql-middleware-python

Please now jump to the 'Running docker image section'

## Building your own image
Please run the following commands to clone the repository and navigate to it

    git clone https://github.com/JAAQL/JAAQL-middleware-python.git
    cd JAAQL-middleware-python
    sudo docker build -t jaaql-middleware-python -f docker/Dockerfile .
    
## Setup mount directories
Make the directories you will use as bind mounts within the root JAAQL-middleware-python directory. These offer accessible volumes which persist after your container shuts down. The database is dealt with as a separate anonymous docker volume
    
    mkdir -p log/nginx
    mkdir -p www

## Running docker image
Please replace the _POSTGRES_PASSWORD_ and _JAAQL_VAULT_PASSWORD_ with different secure passwords of your choosing  
Please replace the _SERVER_ADDRESS_ build arg with your server's ip e.g. 93.184.216.34  
Alternatively if your server has a domain name, please replace it with that e.g. example.com. DO NOT USE www. in the URL. If using https, everything will be forced to www.example.com, else only example.com will be available  
If using https you must use a domain name  

    sudo docker run -d \
        --mount type=bind,source="$(pwd)"/log,target=/JAAQL-middleware-python/log \
        --mount type=bind,source="$(pwd)"/log/nginx,target=/var/log/nginx \
        --mount type=bind,source="$(pwd)"/www,target=/JAAQL-middleware-python/www \
        --name jaaql-middleware-container \
        -p 80:80 \
        -e IS_HTTPS=FALSE \
        -e POSTGRES_PASSWORD=123456 \
        -e JAAQL_VAULT_PASSWORD=pa55word \
        -e SERVER_ADDRESS=YOUR_SERVER_ADDRESS \
        jaaql-middleware-python

For those wishing that this container boots when your system boots (on startup), please add the following argument to the above

    --restart unless-stopped \
    
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

## Using HTTPS
If you wish to use https please adjust the 'docker run' command to have the following arguments. The email is used by certbot for registration and recovery contact. An email will also be sent if the certificates cannot auto renew. Please do not remove the -p 80:80 argument as we require port 80 open so those accessing the website with http are redirected to https

    -p 443:443 \
    -e IS_HTTPS=TRUE \
    -e HTTPS_EMAIL=mail@example.com \

If you take a container that has been ran using IS_HTTPS=TRUE and run it with IS_HTTPS=FALSE you will lose the certificates and need to reconfigure

# Troubleshooting
If you are seeing a 404 when trying to access http(s)://your_address/swagger/jaaql_internal_api.html, you have likely not replaced the server address in the run command
