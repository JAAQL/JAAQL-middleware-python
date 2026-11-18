# Docker Instructions
For those entirely new to docker, the following will be helpful so you can setup JAAQL with no knowledge of docker

Please download and install docker

    curl -fsSL https://get.docker.com -o get-docker.sh
    sh ./get-docker.sh

On Almalinux run the following and input y for the prompts

    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf remove podman buildah
    sudo dnf install docker-ce docker-ce-cli containerd.io
    sudo systemctl start docker.service
    sudo systemctl enable docker.service
    sudo systemctl enable docker
    sudo service docker start
    
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

    -e CANNED_QUERIES=TRUE \
    -e GUNICORN_WORKERS=5 \
    -e DO_AUDIT=FALSE \
    -e FORCE_MFA=FALSE \
    -e LOG_TO_OUTPUT=TRUE \
    -e OUTPUT_QUERY_EXCEPTIONS=TRUE \
    -e JEQL_VERSION=3.0.6 \
    -e SENTINEL_URL=jaaql.io:8443 \
    -e JAAQL_DEEP_HEALTH_APPLICATION=sentinel \
    -e SENTINEL_SLOW_QUERY_SECONDS=3 \
    -e RESEND_VERIFY_EMAIL_COOLDOWN_SECONDS=60 \
    -e RESEND_VERIFY_EMAIL_MAX_PER_HOUR=5 \
    -e WEBHOOK_MAX_RUNNING=4 \
    -e WEBHOOK_MAX_WAITING=32 \
    -e PUBLIC_PROCEDURE_MAX_RUNNING=4 \
    -e PUBLIC_PROCEDURE_MAX_WAITING=32 \
    --mount type=bind,source="$(pwd)"/install_scripts,target=/JAAQL-middleware-python/install_scripts \

JEQL_VERSION specifies the version of JEQL to use  
SENTINEL_SLOW_QUERY_SECONDS (default 3) reports a JAAQL query request whose statements and COMMIT take longer than that many seconds to Sentinel (SENTINEL_URL) as a slow query, and prints it as one line in the log either way; 0 turns it off. The time is wall clock in the gunicorn worker, so a worker busy with other requests can make a fast statement look slow. jaaql-monitor's statements (deploy scripts, migrations) are never reported  
SENTINEL_URL also receives JAAQL's own server errors: a request that fails because of JAAQL or its infrastructure (an unexpected exception, a 5xx, JAAQL's own SQL failing, the database server failing under any SQL: disk full, out of memory, corruption, an I/O error, a shutdown), never one that fails because of what the client sent (its SQL, a malformed body); each is printed as one line in the log either way. Only /submit, /execute and /call-proc show their inputs' values in a report, other routes name their inputs only  
JAAQL_DEEP_HEALTH_APPLICATION (unset by default) names one application whose view deep_health.fault (cause text) /internal/deep-health also reads, as dba, after JAAQL's own check: any row answers 503 Deep health followed by every cause, and a view that cannot be read 503 Deep health: application check unavailable, neither of which is reported as a server error. Unset, deep-health checks JAAQL alone. Sentinel's box sets it to sentinel. Both 503 bodies are public: nginx passes /api/internal/deep-health on with no login, as Pingdom polls it, so anyone can read the causes the view names. A view must therefore name causes fit for anyone to read (Sentinel's names the kind of cause only, never addresses or personal data). Why a view could not be read (the first line of the database error) is never in the body: it is printed in the log as a line of its own, "Deep health <application> answered 503: deep_health.fault could not be read (<error>); <n> more since the last line", at most once a minute per gunicorn worker and never as a SERVER ERROR line. JAAQL's own check, which comes first whether the variable is set or not, shows no one an error either: when it fails (its cached health query missing, JAAQL's database failing under it) deep-health answers the generic 503 Deep health: JAAQL check failed, and /internal/is-alive, as public, the generic 503 Keep alive failed; each is reported to Sentinel as the server error it is, by the error itself, and why is printed in the log as "Deep health answered 503: JAAQL's own check failed (<error>); <n> more since the last line" (or "Is alive answered 503: ..."), at most once a minute per worker. Both routes, as every GET route whose GET only reads, also answer HEAD, which uptime checkers send, with the status and headers the GET would have and no body, and a method a route does not take with 405 and an Allow header, never as a server error. A GET route whose GET acts answers HEAD 405, with an Allow header that leaves HEAD out as Flask's own answer to OPTIONS on it does, and does nothing, so that no link checker, mail scanner or uptime checker sending HEAD does what the GET does: the webhooks (below), /cron (starts the cron jobs due), /flush-cache (flushes every worker's cache), and the OIDC login and logout routes /fetch-user-registries-for-tenant, /oidc-redirect-url, /exchange-auth-code, /oidc/logout and /oidc/post-logout (a pushed authorization request, the login's cookies set and consumed, a code exchanged, with EasyAuth a login and its rows provisioned). /rendered_documents answers HEAD by reading the document without the download's deleting it  
RESEND_VERIFY_EMAIL_COOLDOWN_SECONDS (default 60) and RESEND_VERIFY_EMAIL_MAX_PER_HOUR (default 5) limit how often /resend-verify-email, which needs no login, has Keycloak send one account its verification mail: at most once in that many seconds and that many times an hour, the send at the account's first sign-in included; a resend inside the limits sends nothing and answers as the last send did. 0 lifts a limit. Each gunicorn worker (GUNICORN_WORKERS) counts on its own  
WEBHOOK_MAX_RUNNING (default 4) is the most webhook processes (node, one per request to /webhook/... or /secure/...) one gunicorn worker runs at once, and WEBHOOK_MAX_WAITING (default 32) the most webhooks that wait for a place in it at once, each at most 5 seconds and served in the order they came, so that a burst is served a few at a time; a webhook that finds no place is not started and is answered 503 with Retry-After: 5, never as a server error. WEBHOOK_MAX_RUNNING 0 lifts the bound, WEBHOOK_MAX_WAITING 0 refuses at once. A box runs at most GUNICORN_WORKERS times as many. A webhook's body reaches it on its stdin, so its size is bounded only by the request size limit: nginx's client_max_body_size (JAAQL's nginx config sets none, so nginx's default of 1 MiB holds) and Flask's MAX_CONTENT_LENGTH of 2 MiB behind it, each answering 413. A /webhook POST's body is JSON or form-encoded (application/x-www-form-urlencoded, as payment providers such as Mollie send it), which JAAQL hands over as it came, never parsed (webhook.rawRequestData in BATON); a /secure POST's is JSON only. A webhook URL's query reaches the webhook unchanged as its parameters, whatever its keys, and the path's application and name say which webhook runs. A HEAD to a webhook URL is answered 405 (Allow: GET, OPTIONS, POST) and starts nothing: the webhook is not told the method, so it would act on a HEAD as on the GET, run by every link or uptime checker that sends one  
PUBLIC_PROCEDURE_MAX_RUNNING (default 4) and PUBLIC_PROCEDURE_MAX_WAITING (default 32) bound public cloud procedures (/remote_procedure of a procedure of access public, which the anonymous user may call) in the same way, with places of their own, so that webhooks and public procedures never keep each other out; one that finds no place is not started and is answered 503 with Retry-After: 5. Private procedures, which need a login, are not bounded  
You can specify jaaql specific install scripts which will call the various endpoints with input data, after jaaql has been installed
    
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

Every line the master and the workers print reaches log/gunicorn.log whole and at once, in the order each process printed it (jaaql/utilities/line_output.py, installed by docker/gunicorn_config.py's on_starting): one write per line, the cache flush's lines included (on SIGUSR1, which docker/gunicorn_config.py's post_worker_init has gevent's hub run between greenlets, never in the middle of a line being printed), so the lines of workers printing at the same moment are never joined or cut, and a grep -c of SERVER ERROR counts each. PYTHONUNBUFFERED is not needed for that. The limits: a line is written once its newline is printed (or at a flush, or when the process exits); a line over 1 MiB is written as it comes, in pieces; and with LOG_TO_OUTPUT=TRUE, where the output is a pipe rather than the log file, the kernel keeps a write whole only up to 4,096 bytes (PIPE_BUF), so a longer line can still be cut by another worker's there

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

# Local DEV

    docker run -p 80:80 -e LOG_TO_OUTPUT=TRUE -e POSTGRES_PASSWORD=123456 -e JAAQL_LOCAL_INSTALL=TRUE -e JAAQL_VAULT_PASSWORD=pa55word jaaql/jaaql-middleware-python

It is also recommended to use the jaaql_docker.bat for rapid local dev rebuild and testing
